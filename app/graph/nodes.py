"""LangGraph nodes and routing decisions."""

from collections.abc import Callable, Mapping
from typing import Any, Literal, Protocol

from app.domain.exceptions import (
    CubeClientError,
    LanguageModelResponseError,
    ResultValidationError,
)
from app.domain.models import IntentStatus
from app.graph.state import AgentState
from app.services.answer_composer import AnswerComposer
from app.services.intent_parser import IntentParser
from app.services.query_builder import CubeQueryBuilder
from app.services.result_validator import ResultValidator


class CubeDataSource(Protocol):
    """Port required by the query node."""

    def load(
        self,
        query: Mapping[str, Any],
    ) -> list[dict[str, Any]]:
        """Execute a governed analytical query."""
        ...


Node = Callable[[AgentState], dict[str, Any]]


def create_interpret_node(parser: IntentParser) -> Node:
    """Create a node that interprets the user's question."""

    def interpret_node(state: AgentState) -> dict[str, Any]:
        question = state.get("question", "")

        try:
            interpretation = parser.parse(question)
        except LanguageModelResponseError:
            return {
                "error": (
                    "I could not interpret the question safely. "
                    "Please rephrase it and try again."
                )
            }

        return {"interpretation": interpretation}

    return interpret_node


def create_query_node(
    query_builder: CubeQueryBuilder,
    data_source: CubeDataSource,
) -> Node:
    """Create a node that builds and executes a Cube query."""

    def query_node(state: AgentState) -> dict[str, Any]:
        interpretation = state.get("interpretation")

        if interpretation is None or interpretation.request is None:
            return {
                "error": (
                    "A validated analytical request was not available."
                )
            }

        query = query_builder.build(interpretation.request)

        try:
            rows = data_source.load(query)
        except CubeClientError:
            return {
                "cube_query": query,
                "error": (
                    "I could not retrieve marketing data from Cube. "
                    "Please try again."
                ),
            }

        return {
            "cube_query": query,
            "raw_rows": rows,
        }

    return query_node


def create_validate_node(
    result_validator: ResultValidator,
) -> Node:
    """Create a node that validates Cube response rows."""

    def validate_node(state: AgentState) -> dict[str, Any]:
        interpretation = state.get("interpretation")
        raw_rows = state.get("raw_rows")

        if interpretation is None or interpretation.request is None:
            return {
                "error": (
                    "A validated analytical request was not available."
                )
            }

        if raw_rows is None:
            return {
                "error": "Cube did not return an analytical result."
            }

        try:
            validated_result = result_validator.validate(
                interpretation.request,
                raw_rows,
            )
        except ResultValidationError:
            return {
                "error": (
                    "Cube returned data that could not be "
                    "validated safely."
                )
            }

        return {"validated_result": validated_result}

    return validate_node


def create_answer_node(
    answer_composer: AnswerComposer,
) -> Node:
    """Create a node that renders validated analytical facts."""

    def answer_node(state: AgentState) -> dict[str, Any]:
        interpretation = state.get("interpretation")
        validated_result = state.get("validated_result")

        if interpretation is None or interpretation.request is None:
            return {
                "error": (
                    "A validated analytical request was not available."
                )
            }

        if validated_result is None:
            return {
                "error": (
                    "A validated analytical result was not available."
                )
            }

        answer = answer_composer.compose(
            interpretation.request,
            validated_result,
        )
        return {"answer": answer}

    return answer_node


def route_after_interpret(
    state: AgentState,
) -> Literal["query", "direct_response", "error_response"]:
    """Choose whether to query data or return a direct message."""
    if state.get("error"):
        return "error_response"

    interpretation = state.get("interpretation")

    if interpretation is None:
        return "error_response"

    if interpretation.status is IntentStatus.READY:
        return "query"

    return "direct_response"


def route_after_operation(
    state: AgentState,
) -> Literal["continue", "error_response"]:
    """Stop the analytical path when a prior node reported an error."""
    if state.get("error"):
        return "error_response"

    return "continue"


def direct_response_node(state: AgentState) -> dict[str, str]:
    """Return a clarification or unsupported-scope message."""
    interpretation = state.get("interpretation")

    if interpretation is None or not interpretation.message:
        return {
            "answer": (
                "I need more information before I can answer "
                "that question."
            )
        }

    return {"answer": interpretation.message}


def error_response_node(state: AgentState) -> dict[str, str]:
    """Return a controlled message for a known workflow failure."""
    message = state.get("error")

    if not message:
        message = (
            "I could not complete the analysis because an "
            "unexpected error occurred."
        )

    return {"answer": message}