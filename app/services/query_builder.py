"""Deterministic construction of governed Cube queries."""
from __future__ import annotations

from typing import Any

from app.domain.models import AnalyticalRequest


class CubeQueryBuilder:
    """Translate a validated domain request into the Cube query format."""

    VIEW_NAME = "marketing_performance"
    TIME_DIMENSION = f"{VIEW_NAME}.event_date"

    def build(self, request: AnalyticalRequest) -> dict[str, Any]:
        query: dict[str, Any] = {
            "measures": [
                self._member(metric.value)
                for metric in request.metrics
            ]
        }

        if request.dimensions:
            query["dimensions"] = [
                self._member(dimension.value)
                for dimension in request.dimensions
            ]

        if request.start_date is not None and request.end_date is not None:
            time_dimension: dict[str, Any] = {
                "dimension": self.TIME_DIMENSION,
                "dateRange": [
                    request.start_date.isoformat(),
                    request.end_date.isoformat(),
                ],
            }

            if request.time_granularity is not None:
                time_dimension["granularity"] = (
                    request.time_granularity.value
                )

            query["timeDimensions"] = [time_dimension]

        if request.order_by is not None:
            query["order"] = {
                self._member(request.order_by.metric.value):
                    request.order_by.direction.value
            }

        if request.limit is not None:
            query["limit"] = request.limit

        return query

    def _member(self, name: str) -> str:
        return f"{self.VIEW_NAME}.{name}"