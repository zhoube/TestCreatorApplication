from __future__ import annotations

from state import FailureReport, GraphState, PageInspection


def handle_page_inspection_error(state: GraphState) -> GraphState:
    inspection = state.get("inspection")
    if isinstance(inspection, PageInspection):
        details = inspection.errors or ["No usable title, visible text, forms, links, buttons, or inputs were captured."]
    else:
        details = ["Browser inspection did not produce a page inspection result."]
    return {
        **state,
        "failure_report": FailureReport(
            message="Page inspection failed. Test generation stopped before calling the LLM.",
            details=details,
        ),
        "written_files": [],
    }
