import os

import pytest
from playwright.sync_api import Page, expect


DEFAULT_TARGET_URL = "https://demo.playwright.dev/todomvc"


@pytest.fixture(scope="session")
def target_url() -> str:
    return os.getenv("TARGET_URL", DEFAULT_TARGET_URL)


def test_add_new_todo_item(page: Page, target_url: str) -> None:
    page.goto(target_url)
    input_locator = page.locator("input[placeholder='What needs to be done?']")
    input_locator.fill('Buy groceries')
    input_locator.press('Enter')
    todo_item = page.locator('.todo-list li', has_text='Buy groceries').first
    assert todo_item.is_visible()


def test_mark_todo_item_completed(page: Page, target_url: str) -> None:
    page.goto(target_url)
    # Add a new todo item 'Test todo'
    input_locator = page.locator("input[placeholder='What needs to be done?']")
    input_locator.fill("Test todo")
    input_locator.press("Enter")
    # Locate the todo item labeled 'Test todo'
    todo_item = page.locator("li .view label").filter(has_text="Test todo")
    # Locate the checkbox for that todo item - checkbox is inside the same li
    todo_checkbox = todo_item.locator("xpath=..//input[@class='toggle']")
    # Click the checkbox to mark as completed
    todo_checkbox.click()
    # Assert the todo item has the completed state by checking the parent <li> class contains 'completed'
    parent_li = todo_item.locator("xpath=ancestor::li")
    classes = parent_li.first.get_attribute("class") or ""
    assert "completed" in classes, "The todo item should have 'completed' class after marking checkbox"


def test_edit_existing_todo_item(page: Page, target_url: str) -> None:
    page.goto(target_url)
    # Add a new todo item 'Write tests'
    new_todo_input = page.locator("input[placeholder='What needs to be done?']")
    new_todo_input.fill('Write tests')
    new_todo_input.press('Enter')
    # Locate the todo item with text 'Write tests' and double-click it to enter edit mode
    todo_label = page.locator('.todo-list li label').filter(has_text='Write tests').first
    todo_label.dblclick()
    # Edit the todo inline input field (.todo-list li.editing .edit) - clear and type new text
    edit_input = page.locator('.todo-list li.editing .edit').first
    edit_input.fill('Write automated tests')
    edit_input.press('Enter')
    # Assert the todo list now contains the updated text
    updated_todo_label = page.locator('.todo-list li label').filter(has_text='Write automated tests').first
    assert updated_todo_label.is_visible()
    # Optionally assert the old text is not visible
    old_todo_label = page.locator('.todo-list li label').filter(has_text='Write tests').first
    assert not old_todo_label.is_visible()


def test_verify_footer_links_presence_and_href(page: Page, target_url: str) -> None:
    page.goto(target_url)
    real_link = page.get_by_role("link", name="real TodoMVC app.", exact=True)
    remo_link = page.get_by_role("link", name="Remo H. Jansen", exact=True)
    todomvc_link = page.get_by_role("link", name="TodoMVC", exact=True)
    href_real = real_link.get_attribute("href") or ""
    href_remo = remo_link.get_attribute("href") or ""
    href_todomvc = todomvc_link.get_attribute("href") or ""
    assert "todomvc.com" in href_real
    assert "github.com" in href_remo
    assert "todomvc.com" in href_todomvc


def test_input_field_placeholder_verification(page: Page, target_url: str) -> None:
    page.goto(target_url)
    input_locator = page.locator("input[placeholder='What needs to be done?']")
    assert input_locator.count() == 1
    placeholder = input_locator.first.get_attribute("placeholder")
    assert placeholder == "What needs to be done?"




if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
