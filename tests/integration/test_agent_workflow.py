"""Integration tests for the complete grounded analytical workflow."""

from typing import Any

import pytest

from app.adapters.cube_client import CubeClient
from app.config import Settings
from app.domain.metrics import (
    Dimension,
    Metric,
    SortDirection,
)
from app.domain.models import (
    AnalyticalRequest,
    IntentStatus,
    InterpretedQuestion,
    SortSpec,
)
from app.graph.workflow import build_workflow
from app.services.answer_composer import AnswerComposer
from app.services.query_builder import CubeQueryBuilder
from app.services.result_validator import ResultValidator


class FixedIntentParser:
    """Return a controlled interpretation without calling an external LLM."""

    def __init__(
        self,
        interpretation: InterpretedQuestion,
    ) -> None:
        self._interpretation = interpretation
        self.received_question: str | None = None

    def parse(self, question: str) -> InterpretedQuestion:
        """Record the question and return the configured interpretation."""
        self.received_question = question
        return self._interpretation


@pytest.mark.integration
def test_workflow_answers_purchase_ranking_from_live_cube() -> None:
    """The complete workflow should ground its answer in live Cube data."""
    question = "Which campaign generated the most purchases?"
    request = AnalyticalRequest(
        metrics=(Metric.PURCHASES,),
        dimensions=(Dimension.CAMPAIGN_NAME,),
        order_by=SortSpec(
            metric=Metric.PURCHASES,
            direction=SortDirection.DESCENDING,
        ),
        limit=1,
    )
    parser = FixedIntentParser(
        InterpretedQuestion(
            status=IntentStatus.READY,
            request=request,
        )
    )
    settings = Settings()

    with CubeClient(
        base_url=settings.cube_api_url,
        timeout_seconds=settings.request_timeout_seconds,
        token=settings.cube_api_token,
    ) as cube_client:
        workflow = build_workflow(
            parser=parser,  # type: ignore[arg-type]
            data_source=cube_client,
            query_builder=CubeQueryBuilder(),
            result_validator=ResultValidator(),
            answer_composer=AnswerComposer(),
        )

        result: dict[str, Any] = workflow.invoke(
            {"question": question}
        )

    assert parser.received_question == question
    assert result["cube_query"] == {
        "measures": [
            "marketing_performance.purchases",
        ],
        "dimensions": [
            "marketing_performance.campaign_name",
        ],
        "order": {
            "marketing_performance.purchases": "desc",
        },
        "limit": 1,
    }
    assert result["answer"] == (
        "Across the full available data period, "
        "Email Loyalty generated the most purchases, "
        "with 2,796 purchases."
    )