from __future__ import annotations

from nodes.page_inspection_error_handler.node import handle_page_inspection_error
from nodes.page_inspector.node import inspect_page
from nodes.scenario_finder.node import find_scenarios
from nodes.test_case_creator.node import create_test_cases
from nodes.test_case_probe.node import probe_test_cases
from nodes.test_case_writer.node import write_test_cases
from nodes.writer.node import write_output
from state import GenerationRequest, GraphState


def inspection_failed(state: GraphState) -> bool:
    inspection = state.get("inspection")
    if inspection is None:
        return True
    has_page_evidence = bool(inspection.title or inspection.visible_text or inspection.links or inspection.buttons or inspection.inputs or inspection.forms)
    return bool(inspection.errors) or not has_page_evidence


def route_after_inspection(state: GraphState) -> str:
    if inspection_failed(state):
        return "page_inspection_error_handler"
    return "scenario_finder"


def route_failure_or(next_node: str):
    def _route(state: GraphState) -> str:
        if state.get("failure_report"):
            return "stop"
        return next_node

    return _route


def build_graph():
    from langgraph.graph import END, START, StateGraph

    graph = StateGraph(GraphState)
    graph.add_node("page_inspector", inspect_page)
    graph.add_node("scenario_finder", find_scenarios)
    graph.add_node("test_case_creator", create_test_cases)
    graph.add_node("test_case_probe", probe_test_cases)
    graph.add_node("test_case_writer", write_test_cases)
    graph.add_node("writer", write_output)
    graph.add_node("page_inspection_error_handler", handle_page_inspection_error)

    graph.add_edge(START, "page_inspector")
    graph.add_conditional_edges(
        "page_inspector",
        route_after_inspection,
        {
            "scenario_finder": "scenario_finder",
            "page_inspection_error_handler": "page_inspection_error_handler",
        },
    )
    graph.add_conditional_edges("scenario_finder", route_failure_or("test_case_creator"), {"test_case_creator": "test_case_creator", "stop": END})
    graph.add_conditional_edges("test_case_creator", route_failure_or("test_case_probe"), {"test_case_probe": "test_case_probe", "stop": END})
    graph.add_conditional_edges("test_case_probe", route_failure_or("test_case_writer"), {"test_case_writer": "test_case_writer", "stop": END})
    graph.add_conditional_edges("test_case_writer", route_failure_or("writer"), {"writer": "writer", "stop": END})
    graph.add_edge("writer", END)
    graph.add_edge("page_inspection_error_handler", END)
    return graph.compile()


def generate_tests(request: GenerationRequest) -> GraphState:
    graph = build_graph()
    return graph.invoke({"request": request})
