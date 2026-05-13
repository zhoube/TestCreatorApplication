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
            probe.selector_hints.append(f'page.get_by_role("link", name={_quote(text)}, exact=True)')
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
