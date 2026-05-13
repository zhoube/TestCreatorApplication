import os

import pytest
from playwright.sync_api import Page, expect


DEFAULT_TARGET_URL = "https://formy-project.herokuapp.com/form"


@pytest.fixture(scope="session")
def target_url() -> str:
    return os.getenv("TARGET_URL", DEFAULT_TARGET_URL)


def test_fill_and_verify_text_inputs(page: Page, target_url: str) -> None:
    page.goto(target_url)
    page.locator("#first-name").fill("John")
    page.locator("#last-name").fill("Doe")
    page.locator("#job-title").fill("Engineer")
    assert "Formy" in page.title()
    assert page.locator("#first-name").input_value() == "John"
    assert page.locator("#last-name").input_value() == "Doe"
    assert page.locator("#job-title").input_value() == "Engineer"


def test_select_highest_level_of_education_radio_button(page: Page, target_url: str) -> None:
    page.goto(target_url)
    radio1 = page.locator("[id=\"radio-button-1\"]").first
    radio2 = page.locator("[id=\"radio-button-2\"]").first
    radio3 = page.locator("[id=\"radio-button-3\"]").first
    radio1.click()
    assert radio1.is_checked()
    radio2.click()
    assert radio2.is_checked()
    radio3.click()
    assert radio3.is_checked()


def test_select_years_of_experience_from_dropdown(page: Page, target_url: str) -> None:
    page.goto(target_url)
    select_menu = page.locator("[id=\"select-menu\"]").first
    select_menu.select_option("2")
    assert select_menu.input_value() == "2"


def test_submit_form_and_verify_navigation(page: Page, target_url: str) -> None:
    page.goto(target_url)
    submit_button = page.get_by_role("button", name="Submit", exact=True).first
    href = submit_button.get_attribute("href")
    assert href is not None and "/thanks" in href
    submit_button.click()
    # Wait for navigation or URL change after clicking Submit
    page.wait_for_url("**/thanks")
    assert "/thanks" in page.url


def test_enter_date_in_datepicker_input(page: Page, target_url: str) -> None:
    page.goto(target_url)
    datepicker = page.locator("#datepicker").first
    datepicker.fill("06/15/2024")
    assert datepicker.input_value() == "06/15/2024"




if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
