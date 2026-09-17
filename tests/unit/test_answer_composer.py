"""Unit tests for deterministic grounded answer composition."""

from datetime import date
from decimal import Decimal

from app.domain.metrics import Dimension, Metric
from app.domain.models import (
    AnalyticalRequest,
    ValidatedResult,
    ValidatedRow,
)
from app.services.answer_composer import AnswerComposer


def test_composes_spend_by_channel_with_period() -> None:
    request = AnalyticalRequest(
        metrics=(Metric.SPEND,),
        dimensions=(Dimension.CHANNEL,),
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
    )
    result = ValidatedResult(
        rows=(
            ValidatedRow(
                dimensions={Dimension.CHANNEL: "Search"},
                metrics={Metric.SPEND: Decimal("31980.20")},
            ),
            ValidatedRow(
                dimensions={Dimension.CHANNEL: "Email"},
                metrics={Metric.SPEND: Decimal("3621.52")},
            ),
        )
    )

    answer = AnswerComposer().compose(request, result)

    assert answer == (
        "Marketing spend from 2026-01-01 to 2026-01-31:\n"
        "- Email: $3,621.52\n"
        "- Search: $31,980.20"
    )


def test_composes_purchase_winner() -> None:
    request = AnalyticalRequest(
        metrics=(Metric.PURCHASES,),
        dimensions=(Dimension.CAMPAIGN_NAME,),
    )
    result = ValidatedResult(
        rows=(
            ValidatedRow(
                dimensions={
                    Dimension.CAMPAIGN_NAME: "Search Growth"
                },
                metrics={Metric.PURCHASES: Decimal("125")},
            ),
        )
    )

    answer = AnswerComposer().compose(request, result)

    assert answer == (
        "Across the full available data period, Search Growth "
        "generated the most purchases, with 125 purchases."
    )


def test_composes_roas_winner() -> None:
    request = AnalyticalRequest(
        metrics=(Metric.ROAS,),
        dimensions=(Dimension.CAMPAIGN_NAME,),
    )
    result = ValidatedResult(
        rows=(
            ValidatedRow(
                dimensions={
                    Dimension.CAMPAIGN_NAME: "Retargeting"
                },
                metrics={Metric.ROAS: Decimal("4.253")},
            ),
        )
    )

    answer = AnswerComposer().compose(request, result)

    assert answer == (
        "Across the full available data period, Retargeting "
        "had the highest ROAS at 4.25x."
    )


def test_reports_empty_result() -> None:
    request = AnalyticalRequest(metrics=(Metric.SPEND,))
    result = ValidatedResult(rows=())

    answer = AnswerComposer().compose(request, result)

    assert answer == (
        "No data was available for the requested analysis."
    )


def test_reports_unavailable_roas() -> None:
    request = AnalyticalRequest(
        metrics=(Metric.ROAS,),
        dimensions=(Dimension.CAMPAIGN_NAME,),
    )
    result = ValidatedResult(
        rows=(
            ValidatedRow(
                dimensions={
                    Dimension.CAMPAIGN_NAME: "Awareness"
                },
                metrics={Metric.ROAS: None},
            ),
        )
    )

    answer = AnswerComposer().compose(request, result)

    assert answer == (
        "Across the full available data period, ROAS for "
        "Awareness was not available."
    )