"""Unit tests for the compiled LangGraph workflow."""

from decimal import Decimal
from unittest.mock import MagicMock

from app.domain.metrics import Dimension, Metric
from app.domain.models import (
    AnalyticalRequest,
    IntentStatus,
    InterpretedQuestion,
    ValidatedResult,
    ValidatedRow,
)
from app.graph.workflow import build_workflow


def test_workflow_executes_grounded_analytical_path() -> None:
    request = AnalyticalRequest(
        metrics=(Metric.PURCHASES,),
        dimensions=(Dimension.CAMPAIGN_NAME,),
    )
    interpretation = InterpretedQuestion(
        status=IntentStatus.READY,
        request=request,
    )
    query = {
        "measures": ["marketing_performance.purchases"],
        "dimensions": [
            "marketing_performance.campaign_name"
        ],
    }
    rows = [
        {
            "marketing_performance.campaign_name": "Search Growth",
            "marketing_performance.purchases": "125",
        }
    ]
    validated_result = ValidatedResult(
        rows=(
            ValidatedRow(
                dimensions={
                    Dimension.CAMPAIGN_NAME: "Search Growth"
                },
                metrics={Metric.PURCHASES: Decimal("125")},
            ),
        )
    )

    parser = MagicMock()
    parser.parse.return_value = interpretation
    query_builder = MagicMock()
    query_builder.build.return_value = query
    data_source = MagicMock()
    data_source.load.return_value = rows
    result_validator = MagicMock()
    result_validator.validate.return_value = validated_result
    answer_composer = MagicMock()
    answer_composer.compose.return_value = (
        "Search Growth generated the most purchases."
    )

    workflow = build_workflow(
        parser=parser,
        data_source=data_source,
        query_builder=query_builder,
        result_validator=result_validator,
        answer_composer=answer_composer,
    )

    result = workflow.invoke(
        {"question": "Which campaign had the most purchases?"}
    )

    assert result["answer"] == (
        "Search Growth generated the most purchases."
    )
    parser.parse.assert_called_once()
    query_builder.build.assert_called_once_with(request)
    data_source.load.assert_called_once_with(query)
    result_validator.validate.assert_called_once_with(
        request,
        rows,
    )
    answer_composer.compose.assert_called_once_with(
        request,
        validated_result,
    )


def test_workflow_skips_cube_for_clarification() -> None:
    message = "Which metric should define best performance?"
    parser = MagicMock()
    parser.parse.return_value = InterpretedQuestion(
        status=IntentStatus.NEEDS_CLARIFICATION,
        message=message,
    )
    data_source = MagicMock()

    workflow = build_workflow(
        parser=parser,
        data_source=data_source,
        query_builder=MagicMock(),
        result_validator=MagicMock(),
        answer_composer=MagicMock(),
    )

    result = workflow.invoke(
        {"question": "Which campaign performed best?"}
    )

    assert result["answer"] == message
    data_source.load.assert_not_called()