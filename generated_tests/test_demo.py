import os

import pytest
from playwright.sync_api import Page, expect


DEFAULT_TARGET_URL = "https://demo.playwright.dev/todomvc"


@pytest.fixture(scope="session")
def target_url() -> str:
    return os.getenv("TARGET_URL", DEFAULT_TARGET_URL)


def test_add_new_todo_item(page: Page, target_url: str) -> None:
    page.goto(target_url)
    input_locator = page.locator("input[placeholder=\"What needs to be done?\"]")
    new_todo_text = "Buy groceries"
    input_locator.fill(new_todo_text)
    input_locator.press("Enter")
    todo_item = page.locator(".todo-list li", has_text=new_todo_text).first
    assert todo_item.is_visible()


def test_edit_existing_todo_item_by_dblclick(page: Page, target_url: str) -> None:
    page.goto(target_url)
    # Add a new todo item to ensure one exists
    new_todo_input = page.locator("input[placeholder='What needs to be done?']")
    new_todo_text = "Test editing todo"
    new_todo_input.fill(new_todo_text)
    new_todo_input.press("Enter")
    # Locate the created todo item label
    todo_label = page.locator(".todo-list li label").filter(has_text=new_todo_text).first
    assert todo_label.is_visible()
    # Double-click the todo item label to enter edit mode
    todo_label.dblclick()
    # The editing input should appear within the li.editing element
    edit_input = page.locator(".todo-list li.editing .edit").first
    assert edit_input.is_visible()
    # Change the todo item's text
    edited_text = "Edited todo item"
    edit_input.fill(edited_text)
    # Submit the edit by pressing Enter
    edit_input.press("Enter")
    # After submitting, the edit input should be gone
    assert page.locator(".todo-list li.editing .edit").count() == 0
    # The new text should be visible in the todo list
    updated_label = page.locator(".todo-list li label").filter(has_text=edited_text).first
    assert updated_label.is_visible()


def test_verify_link_to_real_todomvc_app(page: Page, target_url: str) -> None:
    page.goto(target_url)
    link = page.get_by_role("link", name="real TodoMVC app.", exact=True)
    href = link.get_attribute("href") or ""
    assert "todomvc.com" in href


def test_verify_link_to_author_remo_h_jansen(page: Page, target_url: str) -> None:
    page.goto(target_url)
    link = page.get_by_role("link", name="Remo H. Jansen", exact=True)
    href = link.get_attribute("href") or ""
    assert "github.com/remojansen" in href


def test_verify_link_to_todomvc_homepage(page: Page, target_url: str) -> None:
    page.goto(target_url)
    link = page.get_by_role("link", name="TodoMVC", exact=True)
    href = link.get_attribute("href") or ""
    assert "todomvc.com" in href




if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
