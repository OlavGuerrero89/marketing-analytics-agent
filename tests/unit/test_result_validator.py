"""Unit tests for Cube result validation and normalization."""

from decimal import Decimal

import pytest

from app.domain.exceptions import ResultValidationError
from app.domain.metrics import Dimension, Metric
from app.domain.models import AnalyticalRequest
from app.services.result_validator import ResultValidator


def test_normalizes_valid_cube_row() -> None:
    request = AnalyticalRequest(
        metrics=(Metric.SPEND, Metric.PURCHASES),
        dimensions=(Dimension.CHANNEL,),
    )
    rows = [
        {
            "marketing_performance.channel": "Search",
            "marketing_performance.spend": "123.45",
            "marketing_performance.purchases": "7",
        }
    ]

    result = ResultValidator().validate(request, rows)

    assert not result.is_empty
    assert len(result.rows) == 1
    assert result.rows[0].dimensions == {
        Dimension.CHANNEL: "Search"
    }
    assert result.rows[0].metrics == {
        Metric.SPEND: Decimal("123.45"),
        Metric.PURCHASES: Decimal("7"),
    }


def test_accepts_empty_result() -> None:
    request = AnalyticalRequest(metrics=(Metric.SPEND,))

    result = ResultValidator().validate(request, [])

    assert result.is_empty
    assert result.rows == ()


def test_rejects_missing_metric() -> None:
    request = AnalyticalRequest(metrics=(Metric.SPEND,))
    rows = [{"marketing_performance.channel": "Search"}]

    with pytest.raises(
        ResultValidationError,
        match="missing metric marketing_performance.spend",
    ):
        ResultValidator().validate(request, rows)


def test_rejects_missing_dimension() -> None:
    request = AnalyticalRequest(
        metrics=(Metric.SPEND,),
        dimensions=(Dimension.CHANNEL,),
    )
    rows = [{"marketing_performance.spend": "123.45"}]

    with pytest.raises(
        ResultValidationError,
        match="missing dimension marketing_performance.channel",
    ):
        ResultValidator().validate(request, rows)


def test_rejects_non_numeric_metric() -> None:
    request = AnalyticalRequest(metrics=(Metric.SPEND,))
    rows = [{"marketing_performance.spend": "not-a-number"}]

    with pytest.raises(
        ResultValidationError,
        match="non-numeric metric marketing_performance.spend",
    ):
        ResultValidator().validate(request, rows)


@pytest.mark.parametrize(
    "invalid_value",
    ["NaN", "Infinity", "-Infinity"],
)
def test_rejects_non_finite_metric(invalid_value: str) -> None:
    request = AnalyticalRequest(metrics=(Metric.SPEND,))
    rows = [{"marketing_performance.spend": invalid_value}]

    with pytest.raises(
        ResultValidationError,
        match="non-finite metric marketing_performance.spend",
    ):
        ResultValidator().validate(request, rows)


def test_accepts_null_derived_metric() -> None:
    request = AnalyticalRequest(
        metrics=(Metric.ROAS,),
        dimensions=(Dimension.CAMPAIGN_NAME,),
    )
    rows = [
        {
            "marketing_performance.campaign_name": "Awareness",
            "marketing_performance.roas": None,
        }
    ]

    result = ResultValidator().validate(request, rows)

    assert not result.is_empty
    assert result.rows[0].metrics[Metric.ROAS] is None
