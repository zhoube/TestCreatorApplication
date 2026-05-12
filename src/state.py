from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, TypedDict


@dataclass(slots=True)
class GenerationRequest:
    url: str
    knowledge_base: str = ""
    output_dir: str = "generated_tests"
    max_tests: int = 8
    headed: bool = False


@dataclass(slots=True)
class PageElement:
    kind: str
    text: str = ""
    selector: str = ""
    attributes: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class PageInspection:
    url: str
    final_url: str
    title: str
    visible_text: str
    buttons: list[PageElement] = field(default_factory=list)
    links: list[PageElement] = field(default_factory=list)
    inputs: list[PageElement] = field(default_factory=list)
    forms: list[PageElement] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def summary(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "final_url": self.final_url,
            "title": self.title,
            "visible_text": self.visible_text[:4000],
            "buttons": [asdict(element) for element in self.buttons[:30]],
            "links": [asdict(element) for element in self.links[:30]],
            "inputs": [asdict(element) for element in self.inputs[:30]],
            "forms": [asdict(element) for element in self.forms[:10]],
            "errors": self.errors,
        }


@dataclass(slots=True)
class TestCase:
    name: str
    intent: str
    steps: list[str]
    assertions: list[str]
    priority: str = "medium"


@dataclass(slots=True)
class TestCaseProbe:
    case_name: str
    selector_hints: list[str] = field(default_factory=list)
    assertion_hints: list[str] = field(default_factory=list)
    observed_values: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class GeneratedFile:
    path: str
    content: str


@dataclass(slots=True)
class FailureReport:
    message: str
    details: list[str] = field(default_factory=list)


class GraphState(TypedDict, total=False):
    request: GenerationRequest
    inspection: PageInspection
    scenarios: list[str]
    test_cases: list[TestCase]
    test_case_probes: list[TestCaseProbe]
    generated_files: list[GeneratedFile]
    failure_report: FailureReport
    written_files: list[str]
