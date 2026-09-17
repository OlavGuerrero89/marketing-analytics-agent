"""Unit tests for validated analytical requests and Cube query building."""

from datetime import date

import pytest
from pydantic import ValidationError

from app.domain.metrics import (
    Dimension,
    Metric,
    SortDirection,
    TimeGranularity,
)
from app.domain.models import AnalyticalRequest, SortSpec
from app.services.query_builder import CubeQueryBuilder


def test_builds_total_spend_query_for_date_range() -> None:
    request = AnalyticalRequest(
        metrics=(Metric.SPEND,),
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
    )

    query = CubeQueryBuilder().build(request)

    assert query == {
        "measures": ["marketing_performance.spend"],
        "timeDimensions": [
            {
                "dimension": "marketing_performance.event_date",
                "dateRange": ["2026-01-01", "2026-01-31"],
            }
        ],
    }


def test_builds_query_grouped_by_channel() -> None:
    request = AnalyticalRequest(
        metrics=(Metric.SPEND,),
        dimensions=(Dimension.CHANNEL,),
    )

    query = CubeQueryBuilder().build(request)

    assert query == {
        "measures": ["marketing_performance.spend"],
        "dimensions": ["marketing_performance.channel"],
    }


def test_builds_campaign_ranking_by_roas() -> None:
    request = AnalyticalRequest(
        metrics=(Metric.ROAS,),
        dimensions=(Dimension.CAMPAIGN_NAME,),
        order_by=SortSpec(
            metric=Metric.ROAS,
            direction=SortDirection.DESCENDING,
        ),
        limit=3,
    )

    query = CubeQueryBuilder().build(request)

    assert query == {
        "measures": ["marketing_performance.roas"],
        "dimensions": ["marketing_performance.campaign_name"],
        "order": {"marketing_performance.roas": "desc"},
        "limit": 3,
    }


def test_builds_monthly_trend_query() -> None:
    request = AnalyticalRequest(
        metrics=(Metric.REVENUE,),
        start_date=date(2026, 1, 1),
        end_date=date(2026, 2, 28),
        time_granularity=TimeGranularity.MONTH,
    )

    query = CubeQueryBuilder().build(request)

    assert query == {
        "measures": ["marketing_performance.revenue"],
        "timeDimensions": [
            {
                "dimension": "marketing_performance.event_date",
                "dateRange": ["2026-01-01", "2026-02-28"],
                "granularity": "month",
            }
        ],
    }


def test_rejects_inverted_date_range() -> None:
    with pytest.raises(
        ValidationError,
        match="start_date cannot be later than end_date",
    ):
        AnalyticalRequest(
            metrics=(Metric.SPEND,),
            start_date=date(2026, 2, 1),
            end_date=date(2026, 1, 1),
        )


def test_rejects_ordering_by_unrequested_metric() -> None:
    with pytest.raises(
        ValidationError,
        match="order_by must reference a requested metric",
    ):
        AnalyticalRequest(
            metrics=(Metric.SPEND,),
            order_by=SortSpec(metric=Metric.ROAS),
        )