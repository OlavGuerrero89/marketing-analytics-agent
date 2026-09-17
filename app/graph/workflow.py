"""Assembly of the explicit LangGraph agent workflow."""

from langgraph.graph import END, START, StateGraph

from app.graph.nodes import (
    CubeDataSource,
    create_answer_node,
    create_interpret_node,
    create_query_node,
    create_validate_node,
    direct_response_node,
    error_response_node,
    route_after_interpret,
    route_after_operation,
)
from app.graph.state import AgentState
from app.services.answer_composer import AnswerComposer
from app.services.intent_parser import IntentParser
from app.services.query_builder import CubeQueryBuilder
from app.services.result_validator import ResultValidator


def build_workflow(
    parser: IntentParser,
    data_source: CubeDataSource,
    query_builder: CubeQueryBuilder,
    result_validator: ResultValidator,
    answer_composer: AnswerComposer,
):
    """Build and compile the marketing analytics workflow."""
    graph = StateGraph(AgentState)

    graph.add_node("interpret", create_interpret_node(parser))
    graph.add_node(
        "query",
        create_query_node(query_builder, data_source),
    )
    graph.add_node(
        "validate",
        create_validate_node(result_validator),
    )
    graph.add_node(
        "answer",
        create_answer_node(answer_composer),
    )
    graph.add_node("direct_response", direct_response_node)
    graph.add_node("error_response", error_response_node)

    graph.add_edge(START, "interpret")

    graph.add_conditional_edges(
        "interpret",
        route_after_interpret,
        {
            "query": "query",
            "direct_response": "direct_response",
            "error_response": "error_response",
        },
    )
    graph.add_conditional_edges(
        "query",
        route_after_operation,
        {
            "continue": "validate",
            "error_response": "error_response",
        },
    )
    graph.add_conditional_edges(
        "validate",
        route_after_operation,
        {
            "continue": "answer",
            "error_response": "error_response",
        },
    )
    graph.add_conditional_edges(
        "answer",
        route_after_operation,
        {
            "continue": END,
            "error_response": "error_response",
        },
    )

    graph.add_edge("direct_response", END)
    graph.add_edge("error_response", END)

    return graph.compile()