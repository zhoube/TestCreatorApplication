from __future__ import annotations

from html import escape

from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse

from build import generate_tests
from config import DEFAULT_URL
from state import GenerationRequest

app = FastAPI(title="TestCreatorApplication")


def _page(body: str) -> HTMLResponse:
    return HTMLResponse(
        f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>TestCreatorApplication</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 0; background: #f6f7f9; color: #17202a; }}
    main {{ max-width: 980px; margin: 0 auto; padding: 32px 20px; }}
    h1 {{ font-size: 28px; margin: 0 0 18px; }}
    form, section {{ background: white; border: 1px solid #d9dee7; border-radius: 8px; padding: 18px; margin-bottom: 18px; }}
    label {{ display: block; font-weight: 700; margin: 12px 0 6px; }}
    input, textarea {{ box-sizing: border-box; width: 100%; padding: 10px; border: 1px solid #bbc4d1; border-radius: 6px; font: inherit; }}
    textarea {{ min-height: 130px; }}
    button {{ margin-top: 14px; padding: 10px 14px; background: #0f6cbd; color: white; border: 0; border-radius: 6px; cursor: pointer; }}
    pre {{ overflow: auto; background: #111827; color: #f9fafb; padding: 14px; border-radius: 6px; }}
    .meta {{ color: #526070; }}
  </style>
</head>
<body><main>{body}</main></body>
</html>"""
    )


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    return _page(
        f"""<h1>TestCreatorApplication</h1>
<form method="post" action="/generate">
  <label for="url">Website URL</label>
  <input id="url" name="url" type="url" required placeholder="{DEFAULT_URL}">
  <label for="knowledge_base">Knowledge Base</label>
  <textarea id="knowledge_base" name="knowledge_base" placeholder="Business intent, important flows, or domain notes"></textarea>
  <label for="max_tests">Maximum Tests</label>
  <input id="max_tests" name="max_tests" type="number" min="5" max="10" value="8">
  <button type="submit">Generate Tests</button>
</form>"""
    )


@app.post("/generate", response_class=HTMLResponse)
def generate(url: str = Form(...), knowledge_base: str = Form(""), max_tests: int = Form(8)) -> HTMLResponse:
    state = generate_tests(GenerationRequest(url=url, knowledge_base=knowledge_base, max_tests=max_tests))
    failure = state.get("failure_report")
    if failure:
        details = "".join(f"<li>{escape(detail)}</li>" for detail in failure.details)
        return _page(
            f"""<h1>Generation Failed</h1>
<section><p>{escape(failure.message)}</p><ul>{details}</ul></section>
<p><a href="/">Try another URL</a></p>"""
        )
    test_cases = state.get("test_cases", [])
    written = state.get("written_files", [])
    test_case_items = "".join(f"<li><strong>{escape(item.name)}</strong>: {escape(item.intent)}</li>" for item in test_cases)
    files = "".join(f"<li>{escape(path)}</li>" for path in written) or "<li>No files written.</li>"
    generated = "\n\n".join(file.content for file in state.get("generated_files", []))
    return _page(
        f"""<h1>Generation Result</h1>
<section><p class="meta">Target: {escape(url)}</p></section>
<section><h2>Test Cases</h2><ul>{test_case_items}</ul></section>
<section><h2>Written Files</h2><ul>{files}</ul></section>
<section><h2>Generated Code</h2><pre>{escape(generated)}</pre></section>
<p><a href="/">Generate another set</a></p>"""
    )
