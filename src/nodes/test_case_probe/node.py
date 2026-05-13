from __future__ import annotations

import json
import re
from contextlib import suppress
from dataclasses import asdict
from urllib.parse import urlparse

from state import GraphState, PageElement, TestCase, TestCaseProbe


def _quote(value: str) -> str:
    return json.dumps(value)


def _ascii_words(value: str) -> list[str]:
    return [word for word in re.findall(r"[A-Za-z0-9]{3,}", value) if word.lower() not in {"https", "http", "www"}]


def _link_domain(href: str) -> str:
    host = urlparse(href).hostname or ""
    return host.removeprefix("www.")


def _matching_links(case: TestCase, links: list[PageElement]) -> list[PageElement]:
    haystack = f"{case.name} {case.intent} {' '.join(case.steps)} {' '.join(case.assertions)}".lower()
    if not any(word in haystack for word in ["href", "link", "logo", "navigate", "navigation", "url"]):
        return []
    matches: list[PageElement] = []
    for link in links:
        text = link.text.strip()
        href = link.attributes.get("href", "")
        if text and text.lower() in haystack:
            matches.append(link)
            continue
        domain = _link_domain(href)
        if domain and domain.lower() in haystack:
            matches.append(link)
    return matches


def _select_options(element: PageElement) -> list[dict[str, str]]:
    try:
        options = json.loads(element.attributes.get("options", "[]"))
    except json.JSONDecodeError:
        return []
    if not isinstance(options, list):
        return []
    return [
        {"text": str(option.get("text", "")), "value": str(option.get("value", ""))}
        for option in options
        if isinstance(option, dict)
    ]


def _input_hint(inputs: list[PageElement]) -> str | None:
    for element in inputs:
        placeholder = element.attributes.get("placeholder", "")
        if placeholder:
            selector = f"input[placeholder={_quote(placeholder)}]"
            return f"page.locator({_quote(selector)})"
    for element in inputs:
        if element.selector:
            return f'page.locator({_quote(element.selector)})'
    return None


def _role_locator_hint(element: PageElement, default_role: str = "link") -> str | None:
    text = element.text.strip()
    if not text:
        return None
    role = element.attributes.get("role") or default_role
    return f'page.get_by_role({_quote(role)}, name={_quote(text)}, exact=True)'


def _radio_inputs(inputs: list[PageElement]) -> list[PageElement]:
    return [element for element in inputs if element.attributes.get("type") == "radio"]


def _static_hints(case: TestCase, state: GraphState) -> TestCaseProbe:
    inspection = state["inspection"]
    lower_name = case.name.lower()
    lower_text = f"{case.name} {case.intent}".lower()
    probe = TestCaseProbe(case_name=case.name)

    title_words = _ascii_words(inspection.title)
    if "title" in lower_text and title_words:
        probe.observed_values["title"] = inspection.title
        probe.assertion_hints.extend([f'assert "{word}" in page.title()' for word in title_words[:3]])
        probe.warnings.append("Avoid exact title equality when the title contains punctuation or non-ASCII characters.")

    for link in _matching_links(case, inspection.links):
        text = link.text.strip()
        href = link.attributes.get("href", "")
        if text:
            if link.attributes.get("visible") == "false" and link.selector:
                probe.selector_hints.append(f"page.locator({_quote(link.selector)}).first")
                probe.warnings.append("This matched link is hidden at the inspected viewport; do not use get_by_role() or assert is_visible() for it.")
            else:
                role_hint = _role_locator_hint(link)
                if role_hint:
                    probe.selector_hints.append(role_hint)
                if link.attributes.get("role") and link.attributes["role"] != "link":
                    probe.warnings.append(f"This matched anchor has inspected role {_quote(link.attributes['role'])}; use that role instead of role 'link'.")
        if href:
            probe.observed_values[f"href:{text or href}"] = href
            domain = _link_domain(href)
            if domain:
                probe.assertion_hints.append(f'assert "{domain}" in href')
            else:
                probe.assertion_hints.append(f'assert { _quote(href) } in href')
            probe.warnings.append("Assert href domain/path parts instead of clicking external links or requiring exact protocol/trailing slash.")

    input_selector = _input_hint(inspection.inputs)
    if input_selector and any(word in lower_text for word in ["add", "todo", "input", "edit", "filter", "count", "clear", "complete"]):
        probe.selector_hints.append(input_selector)

    if any(word in lower_text for word in ["select", "option", "dropdown", "years"]):
        for element in inspection.inputs:
            options = _select_options(element)
            if not options:
                continue
            if element.selector:
                probe.selector_hints.append(f"page.locator({_quote(element.selector)})")
            probe.observed_values[f"select_options:{element.selector or 'select'}"] = json.dumps(options)
            selectable = [option for option in options if option["value"] and option["text"].lower() != "select an option"]
            if selectable:
                chosen = next((option for option in selectable if option["text"] in lower_text), selectable[min(1, len(selectable) - 1)])
                probe.assertion_hints.append(
                    f'select_menu.select_option({_quote(chosen["value"])}); assert select_menu.input_value() == {_quote(chosen["value"])}'
                )
                probe.warnings.append(
                    f'Select option label {_quote(chosen["text"])} has value {_quote(chosen["value"])}; assert input_value() against the value, not the label.'
                )
            break

    if "radio" in lower_text:
        radios = _radio_inputs(inspection.inputs)
        if radios:
            for radio in radios[:5]:
                selector = radio.selector or (f'[id="{radio.attributes["id"]}"]' if radio.attributes.get("id") else "")
                if selector:
                    probe.selector_hints.append(f"page.locator({_quote(selector)})")
            radio_details = [
                {
                    "id": radio.attributes.get("id", ""),
                    "name": radio.attributes.get("name", ""),
                    "value": radio.attributes.get("value", ""),
                    "selector": radio.selector,
                }
                for radio in radios
            ]
            probe.observed_values["radio_inputs"] = json.dumps(radio_details)
            names = {radio.attributes.get("name", "") for radio in radios}
            if "" in names or len(names) != 1:
                probe.warnings.append(
                    "Do not assert radio mutual exclusion unless inspected radio inputs share the same non-empty name attribute. For ungrouped radios, assert only that the clicked radio becomes checked."
                )

    for element in [*inspection.buttons, *inspection.links]:
        label = element.text or element.attributes.get("aria-label", "")
        if label and label.lower() in lower_text and element.attributes.get("visible") == "false" and element.selector:
            probe.selector_hints.append(f"page.locator({_quote(element.selector)}).first")
            probe.warnings.append(f"{label!r} is hidden at the inspected viewport; assert existence or attributes instead of visibility.")

    if "add" in lower_name and "todo" in lower_name:
        probe.selector_hints.append('page.locator(".todo-list li", has_text=new_todo_text).first')
        probe.assertion_hints.append("expect(todo_item).to_be_visible()")
    if "active" in lower_name and "filter" in lower_name:
        probe.selector_hints.append('page.get_by_role("link", name="Active", exact=True)')
        probe.assertion_hints.append("expect(active_item).to_be_visible(); expect(completed_item).to_be_hidden()")
        probe.warnings.append("Filtered-out TodoMVC items can remain in the DOM while hidden; assert specific visibility/hidden states.")
    if "completed" in lower_name and "filter" in lower_name:
        probe.selector_hints.append('page.get_by_role("link", name="Completed", exact=True)')
        probe.assertion_hints.append("expect(completed_item).to_be_visible(); expect(active_item).to_be_hidden()")
        probe.warnings.append("Use role-specific filter links because text like Completed can also appear in todo labels/buttons.")
    if "clear" in lower_name and "completed" in lower_name:
        probe.selector_hints.append('page.get_by_role("button", name="Clear completed")')
    if "count" in lower_name:
        probe.selector_hints.append('page.locator(".todo-count")')
    if "edit" in lower_name:
        probe.selector_hints.extend(['page.locator(".todo-list li label").first', 'page.locator(".todo-list li.editing .edit").first'])

    if not probe.selector_hints and not probe.assertion_hints:
        probe.warnings.append("No strong selector or assertion hints were found; writer should use only inspected DOM evidence.")
    return probe


def _playwright_observations(state: GraphState) -> dict[str, str]:
    observations: dict[str, str] = {}
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # pragma: no cover - optional dependency
        return {"playwright_error": f"Playwright unavailable: {exc}"}

    request = state["request"]
    with sync_playwright() as playwright:
        browser = None
        try:
            browser = playwright.chromium.launch(headless=not request.headed)
            page = browser.new_page()
            page.goto(request.url, wait_until="domcontentloaded", timeout=15000)
            observations["actual_title"] = page.title()
            with suppress(Exception):
                observations["input_count"] = str(page.locator("input, textarea, select").count())
            with suppress(Exception):
                observations["link_count"] = str(page.locator("a[href]").count())
        except Exception as exc:
            observations["playwright_error"] = str(exc)
        finally:
            if browser is not None:
                browser.close()
    return observations


def probe_test_cases(state: GraphState) -> GraphState:
    observations = _playwright_observations(state)
    probes = [_static_hints(test_case, state) for test_case in state.get("test_cases", [])]
    if observations:
        for probe in probes:
            probe.observed_values.update({f"page:{key}": value for key, value in observations.items()})
    print("\n[NODE OUTPUT] test_case_probe")
    print(json.dumps([asdict(probe) for probe in probes], indent=2))
    return {**state, "test_case_probes": probes}
