from __future__ import annotations

from langgraph.graph import StateGraph, START, END

from core.orchestrator.state import AutoLoopState
from core.orchestrator.nodes import (
    parse_node,
    route_node,
    execute_node,
    evaluate_node,
    finalize_node,
    exhaust_node,
    increment_round_node,
    should_retry,
)


def build_graph():
    builder = StateGraph(AutoLoopState)

    builder.add_node("parse", parse_node)
    builder.add_node("route", route_node)
    builder.add_node("execute", execute_node)
    builder.add_node("evaluate", evaluate_node)
    builder.add_node("finalize", finalize_node)
    builder.add_node("exhaust", exhaust_node)
    builder.add_node("increment_round", increment_round_node)

    builder.add_edge(START, "parse")
    builder.add_edge("parse", "route")
    builder.add_edge("route", "execute")
    builder.add_edge("execute", "evaluate")
    builder.add_conditional_edges(
        "evaluate",
        should_retry,
        {
            "finalize": "finalize",
            "exhaust": "exhaust",
            "retry": "increment_round",
        },
    )
    builder.add_edge("increment_round", "execute")
    builder.add_edge("finalize", END)
    builder.add_edge("exhaust", END)

    return builder.compile()


graph = build_graph()
