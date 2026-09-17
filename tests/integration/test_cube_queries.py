"""Integration tests for governed analytical queries through Cube."""

from datetime import date
from decimal import Decimal

import pytest

from app.adapters.cube_client import CubeClient
from app.config import Settings
from app.domain.metrics import Dimension, Metric
from app.domain.models import AnalyticalRequest
from app.services.query_builder import CubeQueryBuilder


@pytest.mark.integration
def test_returns_january_spend_grouped_by_channel() -> None:
    settings = Settings()
    request = AnalyticalRequest(
        metrics=(Metric.SPEND,),
        dimensions=(Dimension.CHANNEL,),
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
    )
    query = CubeQueryBuilder().build(request)

    with CubeClient(
        base_url=settings.cube_api_url,
        timeout_seconds=settings.request_timeout_seconds,
        token=settings.cube_api_token,
    ) as client:
        rows = client.load(query)

    spend_by_channel = {
        row["marketing_performance.channel"]: Decimal(
            row["marketing_performance.spend"]
        )
        for row in rows
    }

    assert set(spend_by_channel) == {
        "Display",
        "Email",
        "Search",
        "Social",
    }
    assert all(spend > 0 for spend in spend_by_channel.values())
    assert sum(
        spend_by_channel.values(),
        start=Decimal("0"),
    ) == Decimal("60834.49")