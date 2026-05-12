from __future__ import annotations

import json

from langchain_core.prompts import ChatPromptTemplate

from llm import LLMClient, LLMError
from state import FailureReport, GraphState

from .prompt import prompt


def find_scenarios(state: GraphState) -> GraphState:
    request = state["request"]
    inspection = state["inspection"]
    prompt_value = ChatPromptTemplate.from_messages([("system", prompt)]).format_prompt(
        page=json.dumps(inspection.summary(), indent=2),
        knowledge_base=request.knowledge_base or "No knowledge base supplied.",
    )
    prompt_messages = prompt_value.to_messages()
    try:
        result = LLMClient().json_messages([{"role": "system", "content": str(prompt_messages[0].content)}])
    except LLMError as exc:
        return {
            **state,
            "failure_report": FailureReport(
                message="Scenario finding failed. Test generation stopped.",
                details=[str(exc)],
            ),
            "written_files": [],
        }
    print("\n[LLM NODE OUTPUT] scenario_finder")
    print(json.dumps(result, indent=2))
    scenarios = [str(item) for item in result.get("scenarios", [])][:8]
    if not scenarios:
        return {
            **state,
            "failure_report": FailureReport(
                message="Scenario finding failed. Test generation stopped.",
                details=["The LLM response did not contain any scenarios."],
            ),
            "written_files": [],
        }
    return {**state, "scenarios": scenarios}
