"""Validation and normalization of Cube analytical results."""

from collections.abc import Mapping, Sequence
from decimal import Decimal, InvalidOperation
from typing import Any

from app.domain.exceptions import ResultValidationError
from app.domain.metrics import Dimension, Metric
from app.domain.models import (
    AnalyticalRequest,
    ValidatedResult,
    ValidatedRow,
)


class ResultValidator:
    """Validate Cube rows against the original analytical request."""

    VIEW_NAME = "marketing_performance"
    NULLABLE_METRICS = frozenset(
        {
            Metric.CTR,
            Metric.CPC,
            Metric.CPA,
            Metric.ROAS,
        }
    )

    def validate(
        self,
        request: AnalyticalRequest,
        rows: Sequence[Mapping[str, Any]],
    ) -> ValidatedResult:
        validated_rows = tuple(
            self._validate_row(request, row, index)
            for index, row in enumerate(rows)
        )
        return ValidatedResult(rows=validated_rows)

    def _validate_row(
        self,
        request: AnalyticalRequest,
        row: Mapping[str, Any],
        index: int,
    ) -> ValidatedRow:
        dimensions = {
            dimension: self._dimension_value(row, dimension, index)
            for dimension in request.dimensions
        }
        metrics = {
            metric: self._metric_value(row, metric, index)
            for metric in request.metrics
        }

        return ValidatedRow(
            dimensions=dimensions,
            metrics=metrics,
        )

    def _dimension_value(
        self,
        row: Mapping[str, Any],
        dimension: Dimension,
        index: int,
    ) -> str:
        member = self._member(dimension.value)

        if member not in row:
            raise ResultValidationError(
                f"Row {index} is missing dimension {member}."
            )

        value = row[member]

        if not isinstance(value, str) or not value.strip():
            raise ResultValidationError(
                f"Row {index} has an invalid dimension {member}."
            )

        return value

    def _metric_value(
        self,
        row: Mapping[str, Any],
        metric: Metric,
        index: int,
    ) -> Decimal | None:
        member = self._member(metric.value)

        if member not in row:
            raise ResultValidationError(
                f"Row {index} is missing metric {member}."
            )

        raw_value = row[member]

        if raw_value is None:
            if metric in self.NULLABLE_METRICS:
                return None

            raise ResultValidationError(
                f"Row {index} has a null metric {member}."
            )

        try:
            value = Decimal(str(raw_value))
        except (InvalidOperation, ValueError) as error:
            raise ResultValidationError(
                f"Row {index} has a non-numeric metric {member}."
            ) from error

        if not value.is_finite():
            raise ResultValidationError(
                f"Row {index} has a non-finite metric {member}."
            )

        return value

    def _member(self, name: str) -> str:
        return f"{self.VIEW_NAME}.{name}"