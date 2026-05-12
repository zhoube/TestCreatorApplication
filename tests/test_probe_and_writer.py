from state import GenerationRequest, GraphState, PageElement, PageInspection, TestCase as AppTestCase
from nodes.test_case_probe.node import _static_hints, probe_test_cases
from nodes.test_case_writer.node import _normalize_python_playwright


def test_probe_recommends_exact_role_link_for_ambiguous_text() -> None:
    state: GraphState = {
        "request": GenerationRequest(url="https://demo.playwright.dev/todomvc"),
        "inspection": PageInspection(
            url="https://demo.playwright.dev/todomvc",
            final_url="https://demo.playwright.dev/todomvc/#/",
            title="React • TodoMVC",
            visible_text="real TodoMVC app. Part of TodoMVC",
            links=[
                PageElement(kind="link", text="real TodoMVC app.", attributes={"href": "https://todomvc.com/"}),
                PageElement(kind="link", text="TodoMVC", attributes={"href": "http://todomvc.com"}),
            ],
        ),
    }
    test_case = AppTestCase(
        name="Verify TodoMVC link href",
        intent="Verify that the TodoMVC link href points to TodoMVC",
        steps=["Locate the link with visible text TodoMVC"],
        assertions=["The href contains todomvc.com"],
    )

    probe = _static_hints(test_case, state)

    assert 'page.get_by_role("link", name="TodoMVC", exact=True)' in probe.selector_hints
    assert any("todomvc.com" in hint for hint in probe.assertion_hints)


def test_writer_normalizes_filter_has_text() -> None:
    content = 'todo_item = page.locator(".todo-list li").filter_has_text(new_todo_text).first\n'

    normalized = _normalize_python_playwright(content)

    assert ".filter(has_text=new_todo_text)" in normalized
    assert "filter_has_text" not in normalized


def test_probe_node_serializes_slotted_probe_for_logging(monkeypatch) -> None:
    state: GraphState = {
        "request": GenerationRequest(url="https://demo.playwright.dev/todomvc"),
        "inspection": PageInspection(
            url="https://demo.playwright.dev/todomvc",
            final_url="https://demo.playwright.dev/todomvc/#/",
            title="React • TodoMVC",
            visible_text="todos",
            inputs=[PageElement(kind="input", attributes={"placeholder": "What needs to be done?"})],
        ),
        "test_cases": [
            AppTestCase(
                name="Add a new todo item",
                intent="Verify todo creation",
                steps=["Add a todo"],
                assertions=["Todo is visible"],
            )
        ],
    }
    monkeypatch.setattr("nodes.test_case_probe.node._playwright_observations", lambda state: {"actual_title": "React • TodoMVC"})

    result = probe_test_cases(state)

    assert result["test_case_probes"][0].case_name == "Add a new todo item"
