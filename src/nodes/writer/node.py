from __future__ import annotations

from state import GraphState

from .writer import write_generated_files


def write_output(state: GraphState) -> GraphState:
    written = write_generated_files(state.get("generated_files", []), state["request"].output_dir)
    return {**state, "written_files": written}
