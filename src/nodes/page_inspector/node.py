from __future__ import annotations

from state import GraphState

from .browser import BrowserInspector


def inspect_page(state: GraphState) -> GraphState:
    request = state["request"]
    inspection = BrowserInspector().inspect(request.url, headed=request.headed)
    return {**state, "inspection": inspection}
