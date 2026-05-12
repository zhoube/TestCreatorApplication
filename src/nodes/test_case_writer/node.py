from __future__ import annotations

import ast
import json
import re
from dataclasses import asdict
from urllib.parse import urlparse

from langchain_core.prompts import ChatPromptTemplate

from config import DEFAULT_URL
from llm import LLMClient, LLMError
from state import FailureReport, GeneratedFile, GraphState, TestCase

from .prompt import prompt, repair_prompt


def _clean_generated_content(content: str) -> str:
    cleaned = content.replace("\x00", "")
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")
    return cleaned.rstrip() + "\n"


def _normalize_python_playwright(content: str) -> str:
    content = re.sub(
        r'(\.locator\([^)\n]+\))\.filter_has_text\(([^)\n]+)\)',
        r"\1.filter(has_text=\2)",
        content,
    )
    content = re.sub(
        r'(\.locator\([^,\n]+),\s*\{\s*["\']hasText["\']\s*:\s*(["\'][^"\']*["\'])\s*\}\s*\)',
        r"\1, has_text=\2)",
        content,
    )
    content = re.sub(
        r'(\.locator\([^,\n]+),\s*\{\s*["\']has_text["\']\s*:\s*(["\'][^"\']*["\'])\s*\}\s*\)',
        r"\1, has_text=\2)",
        content,
    )
    return content


def _safe_function_name(value: str, index: int) -> str:
    name = re.sub(r"[^a-zA-Z0-9_]+", "_", value).strip("_").lower()
    if not name:
        name = f"generated_{index}"
    if not name.startswith("test_"):
        name = f"test_{name}"
    return name


def _function_from_result(result: dict, index: int) -> str:
    lines = result.get("content_lines")
    if not isinstance(lines, list):
        raise LLMError("The LLM response did not contain content_lines for the test function.")
    content = _normalize_python_playwright(_clean_generated_content("\n".join(str(line) for line in lines)))
    function_name = _safe_function_name(str(result.get("function_name", "")), index)
    if not re.search(rf"def\s+{re.escape(function_name)}\s*\(", content):
        content = re.sub(r"def\s+test_[a-zA-Z0-9_]*\s*\(", f"def {function_name}(", content, count=1)
    return content


def _syntax_errors(label: str, content: str) -> list[str]:
    try:
        ast.parse(content)
    except SyntaxError as exc:
        return [f"{label}: line {exc.lineno}: {exc.msg}"]
    except ValueError as exc:
        return [f"{label}: {exc}"]
    return []


def _generate_one_function(state: GraphState, test_case: TestCase, index: int) -> str:
    matching_probes = [asdict(probe) for probe in state.get("test_case_probes", []) if probe.case_name == test_case.name]
    prompt_value = ChatPromptTemplate.from_messages([("system", prompt)]).format_prompt(
        page=json.dumps(state["inspection"].summary(), indent=2),
        scenarios=json.dumps(state.get("scenarios", []), indent=2),
        test_case=json.dumps(asdict(test_case), indent=2),
        test_case_probe=json.dumps(matching_probes[0] if matching_probes else {}, indent=2),
    )
    prompt_messages = prompt_value.to_messages()
    result = LLMClient().json_messages([{"role": "system", "content": str(prompt_messages[0].content)}])
    print(f"\n[LLM NODE OUTPUT] test_case_writer case {index}: {test_case.name}")
    print(json.dumps(result, indent=2))
    content = _function_from_result(result, index)
    errors = _syntax_errors(test_case.name, content)
    if not errors:
        return content

    repair_prompt_value = ChatPromptTemplate.from_messages([("system", repair_prompt)]).format_prompt(
        syntax_errors=json.dumps(errors, indent=2),
        generated_function=content,
    )
    repair_prompt_messages = repair_prompt_value.to_messages()
    repaired = LLMClient().json_messages([{"role": "system", "content": str(repair_prompt_messages[0].content)}])
    print(f"\n[LLM NODE OUTPUT] test_script_repair_agent case {index}: {test_case.name}")
    print(json.dumps(repaired, indent=2))
    repaired_content = _function_from_result(repaired, index)
    repaired_errors = _syntax_errors(test_case.name, repaired_content)
    if repaired_errors:
        raise LLMError("; ".join(repaired_errors))
    return repaired_content


def _site_test_filename(url: str) -> str:
    host = urlparse(url).hostname or "site"
    parts = [part for part in host.lower().split(".") if part and part not in {"www", "com", "org", "net", "co"}]
    name = parts[0] if parts else "site"
    name = re.sub(r"[^a-z0-9_]+", "_", name).strip("_") or "site"
    return f"test_{name}.py"


def _assemble_file(functions: list[str], default_target_url: str) -> GeneratedFile:
    header = f'''import os

import pytest
from playwright.sync_api import Page, expect


DEFAULT_TARGET_URL = "{default_target_url}"


@pytest.fixture(scope="session")
def target_url() -> str:
    return os.getenv("TARGET_URL", DEFAULT_TARGET_URL)
'''
    footer = '''

if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
'''
    content = _clean_generated_content("\n\n".join([header, *functions, footer]))
    return GeneratedFile(path=_site_test_filename(default_target_url), content=content)


def write_test_cases(state: GraphState) -> GraphState:
    test_cases = state.get("test_cases", [])
    functions: list[str] = []
    try:
        for index, test_case in enumerate(test_cases, start=1):
            functions.append(_generate_one_function(state, test_case, index))
    except LLMError as exc:
        return {
            **state,
            "failure_report": FailureReport(
                message="Test case writing failed. Test generation stopped.",
                details=[str(exc)],
            ),
            "written_files": [],
        }
    if not functions:
        return {
            **state,
            "failure_report": FailureReport(
                message="Test case writing failed. Test generation stopped.",
                details=["No test functions were generated."],
            ),
            "written_files": [],
        }
    generated_file = _assemble_file(functions, state["request"].url or DEFAULT_URL)
    return {**state, "generated_files": [generated_file]}
