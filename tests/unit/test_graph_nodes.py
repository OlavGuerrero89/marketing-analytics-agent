"""Unit tests for LangGraph routing and terminal response nodes."""

from unittest.mock import MagicMock

from app.domain.exceptions import (
    CubeConnectionError,
    LanguageModelResponseError,
    ResultValidationError,
)
from app.domain.metrics import Metric
from app.domain.models import (
    AnalyticalRequest,
    IntentStatus,
    InterpretedQuestion,
    ValidatedResult,
)
from app.graph.nodes import (
    create_answer_node,
    create_interpret_node,
    create_query_node,
    create_validate_node,
    direct_response_node,
    error_response_node,
    route_after_interpret,
    route_after_operation,
)


def test_ready_interpretation_routes_to_query() -> None:
    state = {
        "interpretation": InterpretedQuestion(
            status=IntentStatus.READY,
            request=AnalyticalRequest(metrics=(Metric.SPEND,)),
        )
    }

    assert route_after_interpret(state) == "query"


def test_clarification_routes_to_direct_response() -> None:
    message = "Which metric should define best performance?"
    state = {
        "interpretation": InterpretedQuestion(
            status=IntentStatus.NEEDS_CLARIFICATION,
            message=message,
        )
    }

    assert route_after_interpret(state) == "direct_response"
    assert direct_response_node(state) == {"answer": message}


def test_unsupported_question_routes_to_direct_response() -> None:
    message = "Period comparison is not supported."
    state = {
        "interpretation": InterpretedQuestion(
            status=IntentStatus.UNSUPPORTED,
            message=message,
        )
    }

    assert route_after_interpret(state) == "direct_response"
    assert direct_response_node(state) == {"answer": message}


def test_interpretation_error_routes_to_controlled_response() -> None:
    message = "I could not interpret the question."
    state = {"error": message}

    assert route_after_interpret(state) == "error_response"
    assert error_response_node(state) == {"answer": message}


def test_successful_operation_continues() -> None:
    state = {}

    assert route_after_operation(state) == "continue"


def test_failed_operation_routes_to_error_response() -> None:
    state = {"error": "Cube could not be reached."}

    assert route_after_operation(state) == "error_response"

def test_interpret_node_returns_structured_interpretation() -> None:
    interpretation = InterpretedQuestion(
        status=IntentStatus.READY,
        request=AnalyticalRequest(metrics=(Metric.SPEND,)),
    )
    parser = MagicMock()
    parser.parse.return_value = interpretation
    node = create_interpret_node(parser)

    result = node({"question": "How much did we spend?"})

    assert result == {"interpretation": interpretation}
    parser.parse.assert_called_once_with("How much did we spend?")


def test_interpret_node_returns_safe_model_error() -> None:
    parser = MagicMock()
    parser.parse.side_effect = LanguageModelResponseError(
        "Invalid model response."
    )
    node = create_interpret_node(parser)

    result = node({"question": "How much did we spend?"})

    assert result == {
        "error": (
            "I could not interpret the question safely. "
            "Please rephrase it and try again."
        )
    }


def test_query_node_builds_and_executes_cube_query() -> None:
    interpretation = InterpretedQuestion(
        status=IntentStatus.READY,
        request=AnalyticalRequest(metrics=(Metric.SPEND,)),
    )
    query = {"measures": ["marketing_performance.spend"]}
    rows = [{"marketing_performance.spend": "100.00"}]
    query_builder = MagicMock()
    query_builder.build.return_value = query
    data_source = MagicMock()
    data_source.load.return_value = rows
    node = create_query_node(query_builder, data_source)

    result = node({"interpretation": interpretation})

    assert result == {
        "cube_query": query,
        "raw_rows": rows,
    }
    query_builder.build.assert_called_once_with(
        interpretation.request
    )
    data_source.load.assert_called_once_with(query)


def test_query_node_returns_safe_cube_error() -> None:
    interpretation = InterpretedQuestion(
        status=IntentStatus.READY,
        request=AnalyticalRequest(metrics=(Metric.SPEND,)),
    )
    query = {"measures": ["marketing_performance.spend"]}
    query_builder = MagicMock()
    query_builder.build.return_value = query
    data_source = MagicMock()
    data_source.load.side_effect = CubeConnectionError(
        "Cube is offline."
    )
    node = create_query_node(query_builder, data_source)

    result = node({"interpretation": interpretation})

    assert result["cube_query"] == query
    assert result["error"] == (
        "I could not retrieve marketing data from Cube. "
        "Please try again."
    )


def test_validate_node_returns_validated_result() -> None:
    interpretation = InterpretedQuestion(
        status=IntentStatus.READY,
        request=AnalyticalRequest(metrics=(Metric.SPEND,)),
    )
    rows = [{"marketing_performance.spend": "100.00"}]
    validated_result = ValidatedResult(rows=())
    validator = MagicMock()
    validator.validate.return_value = validated_result
    node = create_validate_node(validator)

    result = node(
        {
            "interpretation": interpretation,
            "raw_rows": rows,
        }
    )

    assert result == {"validated_result": validated_result}
    validator.validate.assert_called_once_with(
        interpretation.request,
        rows,
    )


def test_validate_node_returns_safe_validation_error() -> None:
    interpretation = InterpretedQuestion(
        status=IntentStatus.READY,
        request=AnalyticalRequest(metrics=(Metric.SPEND,)),
    )
    rows = [{"marketing_performance.spend": "invalid"}]
    validator = MagicMock()
    validator.validate.side_effect = ResultValidationError(
        "Invalid metric."
    )
    node = create_validate_node(validator)

    result = node(
        {
            "interpretation": interpretation,
            "raw_rows": rows,
        }
    )

    assert result == {
        "error": (
            "Cube returned data that could not be "
            "validated safely."
        )
    }

def test_answer_node_composes_validated_result() -> None:
    interpretation = InterpretedQuestion(
        status=IntentStatus.READY,
        request=AnalyticalRequest(metrics=(Metric.SPEND,)),
    )
    validated_result = ValidatedResult(rows=())
    composer = MagicMock()
    composer.compose.return_value = (
        "No data was available for the requested analysis."
    )
    node = create_answer_node(composer)

    result = node(
        {
            "interpretation": interpretation,
            "validated_result": validated_result,
        }
    )

    assert result == {
        "answer": (
            "No data was available for the requested analysis."
        )
    }
    composer.compose.assert_called_once_with(
        interpretation.request,
        validated_result,
    )


def test_answer_node_rejects_missing_validated_result() -> None:
    interpretation = InterpretedQuestion(
        status=IntentStatus.READY,
        request=AnalyticalRequest(metrics=(Metric.SPEND,)),
    )
    composer = MagicMock()
    node = create_answer_node(composer)

    result = node({"interpretation": interpretation})

    assert result == {
        "error": (
            "A validated analytical result was not available."
        )
    }
    composer.compose.assert_not_called()