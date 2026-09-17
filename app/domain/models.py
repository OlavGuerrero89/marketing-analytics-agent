"""Validated domain models for analytical requests."""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.metrics import (
    Dimension,
    Metric,
    SortDirection,
    TimeGranularity,
)


class SortSpec(BaseModel):
    """Metric and direction used to order a Cube result."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    metric: Metric
    direction: SortDirection = SortDirection.DESCENDING


class AnalyticalRequest(BaseModel):
    """Technology-independent representation of an analytical request."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    metrics: tuple[Metric, ...] = Field(min_length=1)
    dimensions: tuple[Dimension, ...] = ()
    start_date: date | None = None
    end_date: date | None = None
    time_granularity: TimeGranularity | None = None
    order_by: SortSpec | None = None
    limit: int | None = Field(default=None, ge=1, le=100)

    @model_validator(mode="after")
    def validate_request(self) -> Self:
        if (self.start_date is None) != (self.end_date is None):
            raise ValueError(
                "start_date and end_date must be provided together."
            )

        if (
            self.start_date is not None
            and self.end_date is not None
            and self.start_date > self.end_date
        ):
            raise ValueError(
                "start_date cannot be later than end_date."
            )

        if self.time_granularity is not None and self.start_date is None:
            raise ValueError(
                "time_granularity requires a date range."
            )

        if self.order_by is not None and self.order_by.metric not in self.metrics:
            raise ValueError(
                "order_by must reference a requested metric."
            )

        if len(set(self.metrics)) != len(self.metrics):
            raise ValueError("metrics cannot contain duplicates.")

        if len(set(self.dimensions)) != len(self.dimensions):
            raise ValueError("dimensions cannot contain duplicates.")

        return self


class IntentStatus(StrEnum):
    """Possible outcomes of natural-language interpretation."""

    READY = "ready"
    NEEDS_CLARIFICATION = "needs_clarification"
    UNSUPPORTED = "unsupported"


class InterpretedQuestion(BaseModel):
    """Structured and validated result produced by the language model."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: IntentStatus
    request: AnalyticalRequest | None = None
    message: str | None = Field(default=None, max_length=300)

    @model_validator(mode="after")
    def validate_status_payload(self) -> Self:
        if self.status is IntentStatus.READY:
            if self.request is None:
                raise ValueError(
                    "A ready interpretation requires an analytical request."
                )

            if self.message is not None:
                raise ValueError(
                    "A ready interpretation cannot contain a message."
                )

            return self

        if self.request is not None:
            raise ValueError(
                "A non-ready interpretation cannot contain a request."
            )

        if self.message is None or not self.message.strip():
            raise ValueError(
                "A non-ready interpretation requires a message."
            )

        return self