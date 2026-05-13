from nodes.test_case_creator.node import _select_priority_cases
from state import TestCase as AppTestCase


def _case(name: str, priority: str) -> AppTestCase:
    return AppTestCase(
        name=name,
        intent=f"Intent for {name}",
        steps=["Open the page."],
        assertions=["The expected state is present."],
        priority=priority,
    )


def test_priority_selection_keeps_all_high_cases() -> None:
    cases = [_case(f"High {index}", "high") for index in range(1, 7)] + [_case("Medium 1", "medium")]

    selected = _select_priority_cases(cases, max_tests=10)

    assert [case.name for case in selected] == [f"High {index}" for index in range(1, 7)]


def test_priority_selection_adds_medium_until_five() -> None:
    cases = [_case("High 1", "high"), _case("High 2", "high")] + [_case(f"Medium {index}", "medium") for index in range(1, 5)]

    selected = _select_priority_cases(cases, max_tests=10)

    assert [case.name for case in selected] == ["High 1", "High 2", "Medium 1", "Medium 2", "Medium 3"]


def test_priority_selection_uses_low_only_as_minimum_fallback() -> None:
    cases = [_case("High 1", "high"), _case("Medium 1", "medium")] + [_case(f"Low {index}", "low") for index in range(1, 5)]

    selected = _select_priority_cases(cases, max_tests=10)

    assert [case.name for case in selected] == ["High 1", "Medium 1", "Low 1", "Low 2", "Low 3"]
