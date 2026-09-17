"""Deterministic composition of grounded analytical answers."""

from decimal import Decimal

from app.domain.metrics import Dimension, Metric
from app.domain.models import (
    AnalyticalRequest,
    ValidatedResult,
)


class AnswerComposer:
    """Render validated Cube results without changing their meaning."""

    def compose(
        self,
        request: AnalyticalRequest,
        result: ValidatedResult,
    ) -> str:
        if result.is_empty:
            return (
                "No data was available for the requested analysis."
            )

        if self._is_spend_by_channel(request):
            return self._compose_spend_by_channel(request, result)

        if self._is_campaign_ranking(request, Metric.PURCHASES):
            return self._compose_purchase_ranking(request, result)

        if self._is_campaign_ranking(request, Metric.ROAS):
            return self._compose_roas_ranking(request, result)

        return (
            "The analysis returned validated data, but this response "
            "format is not supported."
        )

    def _compose_spend_by_channel(
        self,
        request: AnalyticalRequest,
        result: ValidatedResult,
    ) -> str:
        period = self._period_text(request)
        lines = [f"Marketing spend {period}:"]

        ordered_rows = sorted(
            result.rows,
            key=lambda row: row.dimensions[Dimension.CHANNEL],
        )

        for row in ordered_rows:
            channel = row.dimensions[Dimension.CHANNEL]
            spend = row.metrics[Metric.SPEND]

            if spend is None:
                formatted_spend = "not available"
            else:
                formatted_spend = f"${spend:,.2f}"

            lines.append(f"- {channel}: {formatted_spend}")

        return "\n".join(lines)

    def _compose_purchase_ranking(
        self,
        request: AnalyticalRequest,
        result: ValidatedResult,
    ) -> str:
        winner = result.rows[0]
        campaign = winner.dimensions[Dimension.CAMPAIGN_NAME]
        purchases = winner.metrics[Metric.PURCHASES]
        period = self._period_sentence(request)

        if purchases is None:
            return (
                f"{period}, purchase data for {campaign} was "
                "not available."
            )

        return (
            f"{period}, {campaign} generated the most purchases, "
            f"with {self._format_count(purchases)} purchases."
        )

    def _compose_roas_ranking(
        self,
        request: AnalyticalRequest,
        result: ValidatedResult,
    ) -> str:
        winner = result.rows[0]
        campaign = winner.dimensions[Dimension.CAMPAIGN_NAME]
        roas = winner.metrics[Metric.ROAS]
        period = self._period_sentence(request)

        if roas is None:
            return (
                f"{period}, ROAS for {campaign} was not available."
            )

        return (
            f"{period}, {campaign} had the highest ROAS "
            f"at {roas:,.2f}x."
        )

    def _period_text(self, request: AnalyticalRequest) -> str:
        if request.start_date is None or request.end_date is None:
            return "across the full available data period"

        return (
            f"from {request.start_date.isoformat()} "
            f"to {request.end_date.isoformat()}"
        )

    def _period_sentence(self, request: AnalyticalRequest) -> str:
        if request.start_date is None or request.end_date is None:
            return "Across the full available data period"

        return (
            f"From {request.start_date.isoformat()} "
            f"to {request.end_date.isoformat()}"
        )

    def _is_spend_by_channel(
        self,
        request: AnalyticalRequest,
    ) -> bool:
        return (
            request.metrics == (Metric.SPEND,)
            and request.dimensions == (Dimension.CHANNEL,)
        )

    def _is_campaign_ranking(
        self,
        request: AnalyticalRequest,
        metric: Metric,
    ) -> bool:
        return (
            request.metrics == (metric,)
            and request.dimensions
            == (Dimension.CAMPAIGN_NAME,)
        )

    def _format_count(self, value: Decimal) -> str:
        if value == value.to_integral_value():
            return f"{value:,.0f}"

        return f"{value:,.2f}"