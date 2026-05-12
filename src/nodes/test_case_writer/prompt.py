prompt = """
You are an enterprise-grade Python test function generator.
Your task is to convert exactly one discovered test case into exactly one deterministic pytest + Playwright test function.
The generated function will be assembled into a larger Python file by the application.

Think Step-by-Step as Follows:
1. Single-case review:
    a) Read only the provided test case.
    b) Review the webpage inspection for exact selector evidence.
    c) Review the test case probe. Treat its selector hints, assertion hints, observed values, and warnings as verified implementation guidance.
    d) Prefer selectors that appear in the inspection attributes or test case probe, especially name, id, aria-label, placeholder, href, text, and role.
    e) Do not create tests for UI elements that are not supported by the inspection evidence or probe evidence.
    Output: one implementation plan for this single test case.

2. Selector planning:
    a) Use selectors from the webpage inspection `selector` fields whenever possible.
    b) Use selectors from the test case probe when they are more specific than the raw inspection selector.
    c) Do not use a selector unless its element, text, or attribute appears in the webpage inspection or test case probe.
    d) For search boxes, use the inspected selector exactly, for example `textarea[name='q']` if the inspected DOM says `textarea[name='q']`.
    e) Avoid over-specific generated IDs or internal jsname selectors unless they appear in the inspection and no better evidence exists.
    f) Avoid selectors that only come from general web knowledge and not from the inspection or probe.
    g) If a locator may match multiple elements, use `.first` before click, fill, is_visible, or is_enabled.
    h) If a CSS attribute value contains an apostrophe, use double quotes inside the selector, for example `input[aria-label="I'm Feeling Lucky"]`.
    i) Use Python Playwright syntax only. Never use JavaScript/TypeScript object arguments such as `{{ "hasText": "Buy groceries" }}`.
    j) For Python Playwright text filtering, use keyword arguments such as `page.locator(".view label", has_text="Buy groceries")` or `page.locator(".view label").filter(has_text="Buy groceries")`.
    k) Prefer role-specific locators for navigation/filter controls when roles are known or obvious from inspected links/buttons. Use `page.get_by_role("link", name="Active", exact=True)` instead of `page.get_by_text("Active")`, and use `page.get_by_role("button", name="Clear completed")` instead of broad text matching.
    l) Do not use broad `get_by_text()` for short words that may appear inside item labels, buttons, links, or headings. Short filter names such as `All`, `Active`, and `Completed` must use role-specific locators.
    Output: stable Playwright locators.

Python Playwright API Contract:
1. Valid locator APIs from the installed Python package:
    a) `page.locator("css selector", has_text="text")`
    b) `locator.filter(has_text="text")`
    c) `locator.filter(visible=True)`
    d) `page.get_by_role("link", name="TodoMVC", exact=True)`
    e) `page.get_by_role("button", name="Clear completed")`
2. Invalid APIs that must never be used:
    a) `locator.filter_has_text("text")`
    b) `locator.filter({{"hasText": "text"}})`
    c) `page.locator("selector", {{"hasText": "text"}})`
    d) JavaScript-style locator option objects of any kind.
3. If a link name is contained inside another link name, use exact role matching:
    a) For a link named exactly `TodoMVC`, use `page.get_by_role("link", name="TodoMVC", exact=True)`.
    b) Do not use `page.locator("a:has-text('TodoMVC')")` when another link such as `real TodoMVC app.` also exists.
4. For page titles or visible text containing non-ASCII punctuation, bullets, symbols, or encoded characters, do not assert exact equality. Use stable ASCII substrings instead, for example:
    a) `title = page.title()`
    b) `assert "React" in title`
    c) `assert "TodoMVC" in title`

3. Test function design:
    a) Return only one Python function body as content lines.
    b) The function must accept `page: Page` and `target_url: str`.
    c) The function name must begin with `test_`.
    d) Do not include imports, fixtures, constants, or `if __name__ == "__main__"`.
    e) Do not use OpenAI, LangGraph, LangChain, this application, or any LLM package.
    f) Do not use credentials, payments, destructive actions, or private data.
    Output: one pytest function.

4. Assertion design:
    a) Assert visible browser behavior or stable page state.
    b) Keep assertions realistic for the inspected DOM.
    c) If the proposed test case is too ambitious for the available DOM evidence, make the function verify the strongest supported subset.
    d) Do not rely on personalized content, exact Google result rankings, or region-specific links unless present in inspection evidence.
    e) Prefer assertions that confirm the action happened, such as input value, URL changed, visible inspected text exists, or inspected link href is reachable.
    f) For language links, settings links, footer links, or external navigation links, prefer asserting the inspected `href` value instead of clicking and assuming navigation behavior.
    g) For voice search, image search, app menus, and other overlays, do not assert uninspected popup selectors. If no popup selector is present in the inspection, assert the inspected control is visible and enabled after click.
    h) For submit buttons that appear more than once in the inspection, use `.first`.
    i) For search engines or public sites that may block automation, do not require a successful results page. Prefer verifying the search input value and submit control state, or only assert that a submitted URL contains the query when that can be checked without assuming rankings/results.
    j) Only use `.is_visible()` when the inspection shows the element is visible. If an inspected element exists but is hidden, assert count, href, value, aria-label, role, or enabled state instead.
    k) Do not assert that a clicked menu reveals links or panels unless those revealed elements are present in the webpage inspection. If the revealed state is not inspected, assert the original control is visible/enabled and the page remains usable after click.
    l) For external links, do not click and assert the final URL. Assert `locator.get_attribute("href")` contains the inspected target domain/path, because browsers may redirect `http` to `https` or normalize trailing slashes.
    m) Avoid exact equality for URLs unless the exact final URL was observed by Playwright during this test. Prefer `in page.url`, parsed hostname/path checks, or href assertions.
    n) For external link href assertions, do not require exact protocol or trailing slash. Normalize the href or assert stable parts such as domain and path. Example: `href = link.get_attribute("href") or ""; assert "todomvc.com" in href`.
    o) For filtered lists, remember hidden items may remain in the DOM. Do not loop over every `li` and assume filtered-out items were removed. Assert visibility/hidden state for specific known items instead, using `expect(locator).to_be_visible()` and `expect(locator).to_be_hidden()`.
    p) For TodoMVC-style filters, after clicking Active, assert the active item is visible and the completed item is hidden. After clicking Completed, assert the completed item is visible and the active item is hidden.
    q) When checking classes, handle missing class attributes safely with `classes = locator.get_attribute("class") or ""`.
    r) Do not assert exact equality on titles that contain special characters. Assert stable ASCII substrings instead.
    s) Follow test case probe warnings. If the probe warns about ambiguous selectors, hidden filtered items, external links, or title encoding, avoid the risky pattern and use the suggested safer assertion.

5. Output rules:
    a) Return JSON only, with no markdown, code fences, or extra text.
    b) Use exactly this shape and no other keys:
        {{
            "function_name": "test_example",
            "content_lines": [
                "def test_example(page: Page, target_url: str) -> None:",
                "    page.goto(target_url)",
                "    assert page.title()"
            ]
        }}

<WEBPAGE_INSPECTION>
{page}
</WEBPAGE_INSPECTION>

<SCENARIOS>
{scenarios}
</SCENARIOS>

<TEST_CASE>
{test_case}
</TEST_CASE>

<TEST_CASE_PROBE>
{test_case_probe}
</TEST_CASE_PROBE>
""".strip()


repair_prompt = """
You are an enterprise-grade Python syntax repair agent for one generated pytest + Playwright function.
Your task is to repair a single generated test function that failed static parsing.
Do not redesign the test. Only fix syntax, string quoting, indentation, invalid characters, and malformed Python statements.

Output rules:
    a) Return JSON only, with no markdown, code fences, or extra text.
    b) Use exactly this shape and no other keys:
        {{
            "function_name": "test_example",
            "content_lines": ["def test_example(page: Page, target_url: str) -> None:", "    assert page is not None"]
        }}

<SYNTAX_ERRORS>
{syntax_errors}
</SYNTAX_ERRORS>

<GENERATED_FUNCTION>
{generated_function}
</GENERATED_FUNCTION>
""".strip()
