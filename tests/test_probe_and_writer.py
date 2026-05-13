import ast
import json

from state import GenerationRequest, GraphState, PageElement, PageInspection, TestCase as AppTestCase
from nodes.page_inspector.browser import _selector_for
from nodes.test_case_probe.node import _static_hints, probe_test_cases
from nodes.test_case_writer.node import _assemble_file, _normalize_python_playwright


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


def test_probe_quotes_placeholder_selector_hint_as_valid_python() -> None:
    state: GraphState = {
        "request": GenerationRequest(url="https://demo.playwright.dev/todomvc"),
        "inspection": PageInspection(
            url="https://demo.playwright.dev/todomvc",
            final_url="https://demo.playwright.dev/todomvc/#/",
            title="TodoMVC",
            visible_text="todos",
            inputs=[PageElement(kind="input", attributes={"placeholder": "What needs to be done?"})],
        ),
    }
    test_case = AppTestCase(
        name="Add a new todo item",
        intent="Verify todo creation",
        steps=["Add a todo"],
        assertions=["Todo is visible"],
    )

    probe = _static_hints(test_case, state)
    selector_hint = probe.selector_hints[0]

    assert selector_hint == 'page.locator("input[placeholder=\\"What needs to be done?\\"]")'
    ast.parse(f"def generated_test(page):\n    {selector_hint}\n")


def test_page_inspector_quotes_selector_attribute_values() -> None:
    selector = _selector_for("input", {"aria-label": 'I"m Feeling Lucky'})

    assert selector == 'input[aria-label="I\\"m Feeling Lucky"]'


def test_page_inspector_prefers_id_over_repeated_aria_label() -> None:
    selector = _selector_for("input", {"id": "radio-button-1", "aria-label": "Radio button"})

    assert selector == '[id="radio-button-1"]'


def test_assembled_generated_file_escapes_default_target_url() -> None:
    generated = _assemble_file(
        ["def test_ok(page: Page, target_url: str) -> None:\n    assert target_url\n"],
        'https://example.com/?q="quoted"',
    )

    ast.parse(generated.content)
    assert 'DEFAULT_TARGET_URL = "https://example.com/?q=\\"quoted\\""' in generated.content


def test_probe_warns_for_hidden_link_and_uses_css_locator() -> None:
    state: GraphState = {
        "request": GenerationRequest(url="https://formy-project.herokuapp.com/form"),
        "inspection": PageInspection(
            url="https://formy-project.herokuapp.com/form",
            final_url="https://formy-project.herokuapp.com/form",
            title="Formy",
            visible_text="Form Components",
            links=[
                PageElement(
                    kind="link",
                    text="Autocomplete",
                    selector='a:has-text("Autocomplete")',
                    attributes={"href": "/autocomplete", "visible": "false"},
                )
            ],
        ),
    }
    test_case = AppTestCase(
        name="Verify top navigation link Autocomplete href",
        intent="Verify the Autocomplete link href",
        steps=["Find the Autocomplete link"],
        assertions=["The href contains /autocomplete"],
    )

    probe = _static_hints(test_case, state)

    assert 'page.locator("a:has-text(\\"Autocomplete\\")").first' in probe.selector_hints
    assert any("hidden" in warning for warning in probe.warnings)


def test_probe_uses_explicit_role_for_anchor_with_button_role() -> None:
    state: GraphState = {
        "request": GenerationRequest(url="https://formy-project.herokuapp.com/form"),
        "inspection": PageInspection(
            url="https://formy-project.herokuapp.com/form",
            final_url="https://formy-project.herokuapp.com/form",
            title="Formy",
            visible_text="Submit",
            links=[
                PageElement(
                    kind="link",
                    text="Submit",
                    selector='a:has-text("Submit")',
                    attributes={"href": "/thanks", "role": "button", "visible": "true"},
                )
            ],
        ),
    }
    test_case = AppTestCase(
        name="Submit form navigation",
        intent="Click Submit and verify navigation",
        steps=["Click Submit"],
        assertions=["URL contains /thanks"],
    )

    probe = _static_hints(test_case, state)

    assert 'page.get_by_role("button", name="Submit", exact=True)' in probe.selector_hints
    assert 'page.get_by_role("link", name="Submit", exact=True)' not in probe.selector_hints
    assert any("role" in warning and "button" in warning for warning in probe.warnings)


def test_probe_does_not_add_link_hints_to_unrelated_input_case() -> None:
    state: GraphState = {
        "request": GenerationRequest(url="https://formy-project.herokuapp.com/form"),
        "inspection": PageInspection(
            url="https://formy-project.herokuapp.com/form",
            final_url="https://formy-project.herokuapp.com/form",
            title="Formy",
            visible_text="First name Last name",
            links=[PageElement(kind="link", text="Form", selector='a:has-text("Form")', attributes={"href": "/form", "visible": "true"})],
            inputs=[PageElement(kind="input", attributes={"placeholder": "Enter first name"})],
        ),
    }
    test_case = AppTestCase(
        name="Fill required text inputs",
        intent="Verify users can enter first name, last name, and job title",
        steps=["Fill text inputs"],
        assertions=["Input values are retained"],
    )

    probe = _static_hints(test_case, state)

    assert 'page.get_by_role("link", name="Form", exact=True)' not in probe.selector_hints
    assert "href:Form" not in probe.observed_values


def test_probe_records_select_option_values() -> None:
    options = [
        {"text": "Select an option", "value": "0"},
        {"text": "0-1", "value": "1"},
        {"text": "2-4", "value": "2"},
    ]
    state: GraphState = {
        "request": GenerationRequest(url="https://formy-project.herokuapp.com/form"),
        "inspection": PageInspection(
            url="https://formy-project.herokuapp.com/form",
            final_url="https://formy-project.herokuapp.com/form",
            title="Formy",
            visible_text="Years of experience: Select an option 0-1 2-4",
            inputs=[
                PageElement(
                    kind="input",
                    selector='[id="select-menu"]',
                    attributes={"tag": "select", "visible": "true", "options": json.dumps(options)},
                )
            ],
        ),
    }
    test_case = AppTestCase(
        name="Select years of experience option",
        intent="Verify users can select years of experience",
        steps=["Select 2-4 years"],
        assertions=["The selected value is recorded"],
    )

    probe = _static_hints(test_case, state)

    assert 'page.locator("[id=\\"select-menu\\"]")' in probe.selector_hints
    assert 'select_menu.select_option("2"); assert select_menu.input_value() == "2"' in probe.assertion_hints
    assert any("not the label" in warning for warning in probe.warnings)


def test_probe_warns_when_radio_inputs_are_not_grouped_by_name() -> None:
    state: GraphState = {
        "request": GenerationRequest(url="https://formy-project.herokuapp.com/form"),
        "inspection": PageInspection(
            url="https://formy-project.herokuapp.com/form",
            final_url="https://formy-project.herokuapp.com/form",
            title="Formy",
            visible_text="High School College Grad School",
            inputs=[
                PageElement(kind="input", selector='[id="radio-button-1"]', attributes={"id": "radio-button-1", "type": "radio"}),
                PageElement(kind="input", selector='[id="radio-button-2"]', attributes={"id": "radio-button-2", "type": "radio"}),
                PageElement(kind="input", selector='[id="radio-button-3"]', attributes={"id": "radio-button-3", "type": "radio"}),
            ],
        ),
    }
    test_case = AppTestCase(
        name="Select highest level of education radio buttons",
        intent="Verify radio inputs can be selected",
        steps=["Check each radio input"],
        assertions=["Clicked radio input is checked"],
    )

    probe = _static_hints(test_case, state)

    assert 'page.locator("[id=\\"radio-button-1\\"]")' in probe.selector_hints
    assert any("mutual exclusion" in warning for warning in probe.warnings)


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
