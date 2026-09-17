"""Unit tests for structured natural-language interpretation."""

from unittest.mock import MagicMock

import pytest
from langchain_core.runnables import RunnableLambda

from app.domain.exceptions import LanguageModelResponseError
from app.domain.metrics import Dimension, Metric, SortDirection
from app.domain.models import (
    AnalyticalRequest,
    IntentStatus,
    InterpretedQuestion,
    SortSpec,
)
from app.services.intent_parser import IntentParser


def build_parser_with_result(result):
    invocation = MagicMock(return_value=result)
    structured_model = RunnableLambda(invocation)
    model = MagicMock()
    model.with_structured_output.return_value = structured_model

    parser = IntentParser(model)

    model.with_structured_output.assert_called_once_with(
        InterpretedQuestion,
        method="json_schema",
    )

    return parser, invocation


def test_returns_model_structured_interpretation() -> None:
    expected = InterpretedQuestion(
        status=IntentStatus.READY,
        request=AnalyticalRequest(
            metrics=(Metric.SPEND,),
            dimensions=(Dimension.CHANNEL,),
        ),
    )
    parser, invocation = build_parser_with_result(expected)

    result = parser.parse(
        "How much did we spend by channel?"
    )

    assert result == expected
    invocation.assert_called_once()


def test_empty_question_requests_clarification_without_model_call() -> None:
    expected = InterpretedQuestion(
        status=IntentStatus.READY,
        request=AnalyticalRequest(metrics=(Metric.SPEND,)),
    )
    parser, invocation = build_parser_with_result(expected)

    result = parser.parse("   ")

    assert result.status is IntentStatus.NEEDS_CLARIFICATION
    assert result.request is None
    assert result.message == (
        "Please provide a marketing analytics question."
    )
    invocation.assert_not_called()


def test_preserves_unsupported_interpretation() -> None:
    expected = InterpretedQuestion(
        status=IntentStatus.UNSUPPORTED,
        message="Period comparison is not supported.",
    )
    parser, invocation = build_parser_with_result(expected)

    result = parser.parse(
        "What changed between January and February?"
    )

    assert result == expected
    invocation.assert_called_once()


def test_rejects_non_structured_model_response() -> None:
    parser, invocation = build_parser_with_result(
        {"status": "ready"}
    )

    with pytest.raises(
        LanguageModelResponseError,
        match="invalid interpretation",
    ):
        parser.parse("How much did we spend?")

    invocation.assert_called_once()


def test_ambiguous_best_requests_clarification_without_model_call() -> None:
    expected = InterpretedQuestion(
        status=IntentStatus.READY,
        request=AnalyticalRequest(metrics=(Metric.SPEND,)),
    )
    parser, invocation = build_parser_with_result(expected)

    result = parser.parse("Which campaign performed best?")

    assert result.status is IntentStatus.NEEDS_CLARIFICATION
    assert result.request is None
    assert result.message == (
        "Which metric should define best performance: "
        "purchases or ROAS?"
    )
    invocation.assert_not_called()


def test_purchase_ranking_is_deterministic() -> None:
    model_result = InterpretedQuestion(
        status=IntentStatus.NEEDS_CLARIFICATION,
        message="Incorrect model response.",
    )
    parser, invocation = build_parser_with_result(model_result)

    result = parser.parse(
        "Which campaign generated the most purchases?"
    )

    assert result == InterpretedQuestion(
        status=IntentStatus.READY,
        request=AnalyticalRequest(
            metrics=(Metric.PURCHASES,),
            dimensions=(Dimension.CAMPAIGN_NAME,),
            order_by=SortSpec(
                metric=Metric.PURCHASES,
                direction=SortDirection.DESCENDING,
            ),
            limit=1,
        ),
    )
    invocation.assert_not_called()