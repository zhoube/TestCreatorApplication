from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

from build import generate_tests
from config import DEFAULT_HEADED, DEFAULT_KNOWLEDGE_BASE, DEFAULT_MAX_TESTS, DEFAULT_OUTPUT_DIR, DEFAULT_URL
from state import GenerationRequest


ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / ".env"


def _safe_print(message: object = "") -> None:
    text = str(message)
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", errors="backslashreplace").decode("ascii"))


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def build_request_from_env() -> GenerationRequest:
    load_dotenv(ENV_FILE)

    url = DEFAULT_URL
    knowledge_base = DEFAULT_KNOWLEDGE_BASE
    output_dir = DEFAULT_OUTPUT_DIR
    max_tests = max(5, min(DEFAULT_MAX_TESTS, 10))
    headed = DEFAULT_HEADED

    return GenerationRequest(
        url=url,
        knowledge_base=knowledge_base,
        output_dir=str((ROOT / output_dir).resolve()) if not Path(output_dir).is_absolute() else output_dir,
        max_tests=max_tests,
        headed=headed,
    )


def main() -> int:
    request = build_request_from_env()
    state = generate_tests(request)
    failure = state.get("failure_report")

    _safe_print("TestCreatorApplication")
    _safe_print(f"Target URL: {request.url}")
    _safe_print(f"Output directory: {request.output_dir}")
    _safe_print()

    if failure:
        _safe_print("Generation failed:")
        _safe_print(f"- {failure.message}")
        for detail in failure.details:
            _safe_print(f"- {detail}")
        return 1

    _safe_print("Identified test cases:")
    for test_case in state.get("test_cases", []):
        _safe_print(f"- [{test_case.priority}] {test_case.name}: {test_case.intent}")

    _safe_print()
    if state.get("written_files"):
        _safe_print("Written files:")
        for path in state["written_files"]:
            _safe_print(f"- {path}")
        return 0

    _safe_print("No files were written.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
