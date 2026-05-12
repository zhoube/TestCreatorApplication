from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

from build import generate_tests
from config import DEFAULT_HEADED, DEFAULT_KNOWLEDGE_BASE, DEFAULT_MAX_TESTS, DEFAULT_OUTPUT_DIR, DEFAULT_URL
from state import GenerationRequest


ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / ".env"


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

    print("TestCreatorApplication")
    print(f"Target URL: {request.url}")
    print(f"Output directory: {request.output_dir}")
    print()

    if failure:
        print("Generation failed:")
        print(f"- {failure.message}")
        for detail in failure.details:
            print(f"- {detail}")
        return 1

    print("Identified test cases:")
    for test_case in state.get("test_cases", []):
        print(f"- [{test_case.priority}] {test_case.name}: {test_case.intent}")

    print()
    if state.get("written_files"):
        print("Written files:")
        for path in state["written_files"]:
            print(f"- {path}")
        return 0

    print("No files were written.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
