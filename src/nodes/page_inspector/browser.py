from __future__ import annotations

import json
import re
from contextlib import suppress

from state import PageElement, PageInspection


def _text(value: str | None, limit: int = 240) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", value).strip()[:limit]


def _selector_for(tag: str, attrs: dict[str, str], text: str = "") -> str:
    if attrs.get("data-testid"):
        return f"[data-testid={json.dumps(attrs['data-testid'])}]"
    if attrs.get("aria-label"):
        return f"{tag}[aria-label={json.dumps(attrs['aria-label'])}]"
    if attrs.get("name"):
        return f"{tag}[name={json.dumps(attrs['name'])}]"
    if attrs.get("id"):
        return f"[id={json.dumps(attrs['id'])}]"
    if text and tag in {"button", "a"}:
        return f"{tag}:has-text({json.dumps(text[:50])})"
    return tag


def _attrs(locator) -> dict[str, str]:
    names = ["id", "name", "type", "placeholder", "aria-label", "data-testid", "href", "role"]
    found: dict[str, str] = {}
    for name in names:
        with suppress(Exception):
            value = locator.get_attribute(name)
            if value:
                found[name] = value[:300]
    return found


def _tag_name(locator, fallback: str) -> str:
    with suppress(Exception):
        tag = locator.evaluate("element => element.tagName.toLowerCase()")
        if tag:
            return str(tag)
    return fallback


def _collect(locator, kind: str, fallback_tag: str, limit: int = 30) -> list[PageElement]:
    items: list[PageElement] = []
    with suppress(Exception):
        count = min(locator.count(), limit)
        for index in range(count):
            item = locator.nth(index)
            tag = _tag_name(item, fallback_tag)
            attrs = _attrs(item)
            label = _text(item.inner_text() if kind != "input" else attrs.get("placeholder") or attrs.get("aria-label") or attrs.get("name"))
            items.append(PageElement(kind=kind, text=label, selector=_selector_for(tag, attrs, label), attributes=attrs))
    return items


class BrowserInspector:
    def __init__(self, timeout_ms: int = 15000) -> None:
        self.timeout_ms = timeout_ms

    def inspect(self, url: str, headed: bool = False) -> PageInspection:
        try:
            from playwright.sync_api import sync_playwright
        except Exception as exc:  # pragma: no cover - depends on optional install
            return PageInspection(
                url=url,
                final_url=url,
                title="",
                visible_text="",
                errors=[f"Playwright is not available: {exc}"],
            )

        errors: list[str] = []
        with sync_playwright() as playwright:
            browser = None
            page = None
            try:
                browser = playwright.chromium.launch(headless=not headed)
                page = browser.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=self.timeout_ms)
                with suppress(Exception):
                    page.wait_for_load_state("networkidle", timeout=5000)
                title = _text(page.title(), 500)
                visible_text = _text(page.locator("body").inner_text(timeout=5000), 5000)
                inspection = PageInspection(
                    url=url,
                    final_url=page.url,
                    title=title,
                    visible_text=visible_text,
                    buttons=_collect(page.locator("button, [role=button], input[type=button], input[type=submit]"), "button", "button"),
                    links=_collect(page.locator("a[href]"), "link", "a"),
                    inputs=_collect(page.locator("input, textarea, select"), "input", "input"),
                    forms=_collect(page.locator("form"), "form", "form", 10),
                    errors=errors,
                )
            except Exception as exc:
                final_url = url
                if page is not None:
                    with suppress(Exception):
                        final_url = page.url
                inspection = PageInspection(url=url, final_url=final_url, title="", visible_text="", errors=[str(exc)])
            finally:
                if browser is not None:
                    browser.close()
        return inspection
