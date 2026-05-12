from pathlib import Path

from build import generate_tests, inspection_failed
from llm import LLMClient, LLMError
from nodes.page_inspection_error_handler.node import handle_page_inspection_error
from state import GenerationRequest, GraphState, PageInspection


def test_graph_writes_valid_tests_from_mocked_llm(monkeypatch, tmp_path: Path) -> None:
    def fake_inspect(state: GraphState) -> GraphState:
        return {
            **state,
            "inspection": PageInspection(
                url="https://www.google.com",
                final_url="https://www.google.com",
                title="Example",
                visible_text="Example Domain More information",
            ),
        }

    def fake_json_messages(self, messages):
        content = messages[0]["content"]
        if '"scenarios"' in content:
            return {"scenarios": ["Users can understand the page purpose."]}
        if '"test_cases"' in content:
            return {
                "test_cases": [
                    {
                        "name": f"Test case {index}",
                        "intent": "Verify the page supports a visible user goal.",
                        "steps": ["Open the target URL.", "Inspect visible content."],
                        "assertions": ["The page has visible content."],
                        "priority": "high" if index == 1 else "medium",
                    }
                    for index in range(1, 6)
                ]
            }
        return {
            "function_name": "test_page",
            "content_lines": [
                "def test_page(page: Page, target_url: str) -> None:",
                "    page.goto(target_url)",
                "    assert page.url.startswith('http')",
            ]
        }

    monkeypatch.setattr("build.inspect_page", fake_inspect)
    monkeypatch.setattr("build.probe_test_cases", lambda state: {**state, "test_case_probes": []})
    monkeypatch.setattr(LLMClient, "json_messages", fake_json_messages)

    state = generate_tests(
        GenerationRequest(
            url="https://www.google.com",
            knowledge_base="Users should understand the page purpose.",
            output_dir=str(tmp_path),
            max_tests=5,
        )
    )

    assert len(state["test_cases"]) == 5
    assert state["written_files"]
    assert Path(state["written_files"][0]).exists()


def test_graph_repairs_invalid_generated_python(monkeypatch, tmp_path: Path) -> None:
    def fake_inspect(state: GraphState) -> GraphState:
        return {
            **state,
            "inspection": PageInspection(
                url="https://www.google.com",
                final_url="https://www.google.com",
                title="Example",
                visible_text="Example Domain More information",
            ),
        }

    calls = {"scripts": 0}

    def fake_json_messages(self, messages):
        content = messages[0]["content"]
        if '"scenarios"' in content:
            return {"scenarios": ["Users can understand the page purpose."]}
        if '"test_cases"' in content:
            return {
                "test_cases": [
                    {
                        "name": f"Test case {index}",
                        "intent": "Verify the page supports a visible user goal.",
                        "steps": ["Open the target URL.", "Inspect visible content."],
                        "assertions": ["The page has visible content."],
                        "priority": "medium",
                    }
                    for index in range(1, 6)
                ]
            }
        if "SYNTAX_ERRORS" in content:
            return {
                "function_name": "test_repaired",
                "content_lines": [
                    "def test_repaired(page: Page, target_url: str) -> None:",
                    "    assert page is not None",
                ]
            }
        calls["scripts"] += 1
        return {
            "function_name": "test_broken",
            "content_lines": [
                "def test_broken(page: Page, target_url: str) -> None:",
                "    assert 'unterminated",
            ]
        }

    monkeypatch.setattr("build.inspect_page", fake_inspect)
    monkeypatch.setattr("build.probe_test_cases", lambda state: {**state, "test_case_probes": []})
    monkeypatch.setattr(LLMClient, "json_messages", fake_json_messages)

    state = generate_tests(
        GenerationRequest(
            url="https://www.google.com",
            output_dir=str(tmp_path),
            max_tests=5,
        )
    )

    assert calls["scripts"] == 5
    assert state["written_files"]
    assert Path(state["written_files"][0]).name == "test_google.py"


def test_graph_stops_when_browser_inspection_fails() -> None:
    state: GraphState = {
        "request": GenerationRequest(url="https://bad.local"),
        "inspection": PageInspection(
            url="https://bad.local",
            final_url="https://bad.local",
            title="",
            visible_text="",
            errors=["Navigation timeout"],
        ),
    }

    assert inspection_failed(state)
    failed_state = handle_page_inspection_error(state)

    assert failed_state["failure_report"].message.startswith("Page inspection failed")
    assert failed_state["written_files"] == []


def test_graph_stops_when_llm_fails(monkeypatch, tmp_path: Path) -> None:
    def fake_inspect(state: GraphState) -> GraphState:
        return {
            **state,
            "inspection": PageInspection(
                url="https://www.google.com",
                final_url="https://www.google.com",
                title="Google",
                visible_text="Google Search",
            ),
        }

    monkeypatch.setattr("build.inspect_page", fake_inspect)
    monkeypatch.setattr("build.probe_test_cases", lambda state: {**state, "test_case_probes": []})
    def fake_json_messages(self, messages):
        raise LLMError("OpenAI request failed")

    monkeypatch.setattr(LLMClient, "json_messages", fake_json_messages)
    state = generate_tests(
        GenerationRequest(
            url="https://www.google.com",
            output_dir=str(tmp_path),
            max_tests=5,
        )
    )

    assert state["failure_report"].message.startswith("Scenario finding failed")
    assert state["written_files"] == []
    assert not list(tmp_path.glob("*.py"))
