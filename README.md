# TestCreatorApplication

TestCreatorApplication is a LangGraph-powered take-home project that turns a website URL plus optional business knowledge into deterministic Python browser tests.

The LLM is used only while generating tests. The generated files in `generated_tests/` use `pytest + Playwright` directly and contain no LLM, OpenAI, or LangGraph runtime dependency.

## Architecture

The workflow is split into focused LangGraph nodes:

- **Page inspector** opens the page with Playwright and captures title, visible text, forms, links, buttons, inputs, and selector hints.
- **Page inspection error handler** stops the graph with a clear failure report if page inspection fails or captures no usable evidence.
- **Scenario finder** turns page evidence and knowledge-base text into user scenarios and critical flows.
- **Test case creator** identifies 5-10 things that can actually be tested from the inspected page.
- **Test case probe** adds deterministic Playwright-backed selector and assertion hints for each proposed test case, reducing LLM guessing before code generation.
- **Test case writer** writes deterministic `pytest + Playwright` files for those discovered test cases.
- **Writer** saves the generated test file into `generated_tests/`.

The code mirrors that graph structure:

- `src/main.py` is the PyCharm run-button entrypoint.
- `src/state.py` contains the shared LangGraph state and data models.
- `src/build.py` builds and runs the LangGraph workflow.
- `src/nodes/<agent_name>/node.py` contains each agent node's logic.
- `src/nodes/<agent_name>/prompt.py` exists only for nodes that call the LLM.
- Node-specific helpers live beside the only node that uses them, for example `src/nodes/page_inspector/browser.py`, `src/nodes/test_case_probe/node.py`, and `src/nodes/writer/writer.py`.
- `src/llm.py` is the shared LLM support module.

If `OPENAI_API_KEY` is not set, invalid, or still using the placeholder value, the graph stops and reports the LLM configuration failure. It does not generate fallback tests.

If Playwright cannot inspect the page or captures no usable page evidence, the graph stops immediately and reports the browser inspection failure. It does not call the LLM or write generic tests.

## Setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m playwright install chromium
```

## PyCharm Run Button

Edit `.env` first:

```env
OPENAI_API_KEY=your-openai-api-key
```

Then open [src/main.py](src/main.py) in PyCharm and click the green Run button. The app reads the API key from `.env`, uses the defaults inside `src/main.py`, runs the LangGraph workflow, and writes tests to `generated_tests/`.

Current defaults in `src/config.py`:

- URL: `https://www.google.com`
- max tests: `10`
- minimum enforced by the app: `5`
- output folder: `generated_tests`

Google is intentionally a difficult target because it can vary by region, session, layout, and automation behavior. For a more deterministic demo target, change `DEFAULT_URL` to:

```python
DEFAULT_URL = "https://demo.playwright.dev/todomvc"
```

You can also run the same file from a terminal:

```powershell
python src\main.py
```

## Web UI

```powershell
uvicorn nodes.web.web:app --reload
```

Open `http://127.0.0.1:8000`, enter a URL and optional knowledge base, then generate tests. The UI shows the written files, discovered test cases, and generated code.

## Running Generated Tests

Generated tests include the generation-time target URL as their default. You can override it with `TARGET_URL`.

```powershell
$env:TARGET_URL = "https://www.google.com"
python generated_tests\test_google.py
```

## Development Checks

```powershell
pytest --basetemp=.pytest_tmp
python -m py_compile src\main.py src\*.py
```

## Git Hygiene

The repository ignores local secrets, generated tests, IDE metadata, caches, and logs:

- `.env`
- `generated_tests/`
- `src/log.txt`
- `generated_tests/log.txt`
- `.idea/`
- `__pycache__/`
- `.pytest_cache/`
