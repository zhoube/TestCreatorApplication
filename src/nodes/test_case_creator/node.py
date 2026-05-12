from __future__ import annotations

import json

from langchain_core.prompts import ChatPromptTemplate

from llm import LLMClient, LLMError
from state import FailureReport, GraphState, TestCase

from .prompt import prompt


def create_test_cases(state: GraphState) -> GraphState:
    prompt_value = ChatPromptTemplate.from_messages([("system", prompt)]).format_prompt(
        page=json.dumps(state["inspection"].summary(), indent=2),
        scenarios=json.dumps(state.get("scenarios", []), indent=2),
        max_tests=max(5, min(state["request"].max_tests, 10)),
    )
    prompt_messages = prompt_value.to_messages()
    try:
        result = LLMClient().json_messages([{"role": "system", "content": str(prompt_messages[0].content)}])
    except LLMError as exc:
        return {
            **state,
            "failure_report": FailureReport(
                message="Test case creation failed. Test generation stopped.",
                details=[str(exc)],
            ),
            "written_files": [],
        }
    print("\n[LLM NODE OUTPUT] test_case_creator")
    print(json.dumps(result, indent=2))
    test_cases: list[TestCase] = []
    for item in result.get("test_cases", [])[:10]:
        test_cases.append(
            TestCase(
                name=str(item.get("name", "Generated test case")),
                intent=str(item.get("intent", "")),
                steps=[str(step) for step in item.get("steps", [])],
                assertions=[str(assertion) for assertion in item.get("assertions", [])],
                priority=str(item.get("priority", "medium")),
            )
        )
    target_count = max(5, min(state["request"].max_tests, 10))
    if len(test_cases) < 5:
        return {
            **state,
            "failure_report": FailureReport(
                message="Test case creation failed. Test generation stopped.",
                details=[f"The LLM returned {len(test_cases)} test cases; at least 5 are required."],
            ),
            "written_files": [],
        }
    return {**state, "test_cases": test_cases[:target_count]}
