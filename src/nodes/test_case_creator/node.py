from __future__ import annotations

import json

from langchain_core.prompts import ChatPromptTemplate

from llm import LLMClient, LLMError
from state import FailureReport, GraphState, TestCase

from .prompt import prompt


def _normalize_priority(priority: str) -> str:
    normalized = priority.strip().lower()
    if normalized in {"high", "medium", "low"}:
        return normalized
    return "medium"


def _select_priority_cases(test_cases: list[TestCase], max_tests: int, min_tests: int = 5) -> list[TestCase]:
    high = [test_case for test_case in test_cases if test_case.priority == "high"]
    medium = [test_case for test_case in test_cases if test_case.priority == "medium"]
    low = [test_case for test_case in test_cases if test_case.priority == "low"]

    selected = high[:max_tests]
    if len(selected) < min_tests:
        selected.extend(medium[: min_tests - len(selected)])
    if len(selected) < min_tests:
        selected.extend(low[: min_tests - len(selected)])
    return selected[:max_tests]


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
                priority=_normalize_priority(str(item.get("priority", "medium"))),
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
    selected_test_cases = _select_priority_cases(test_cases, target_count)
    if len(selected_test_cases) < 5:
        return {
            **state,
            "failure_report": FailureReport(
                message="Test case creation failed. Test generation stopped.",
                details=[f"Only {len(selected_test_cases)} priority-selected test cases were available; at least 5 are required."],
            ),
            "written_files": [],
        }
    return {**state, "test_cases": selected_test_cases}
