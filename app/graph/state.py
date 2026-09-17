"""Shared state passed between LangGraph nodes."""

from typing import Any, TypedDict

from app.domain.models import (
    InterpretedQuestion,
    ValidatedResult,
)


class AgentState(TypedDict, total=False):
    """State accumulated during one agent execution."""

    question: str
    interpretation: InterpretedQuestion
    cube_query: dict[str, Any]
    raw_rows: list[dict[str, Any]]
    validated_result: ValidatedResult
    answer: str
    error: str