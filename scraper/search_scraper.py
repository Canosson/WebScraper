from pathlib import Path

import numpy as np
import pandas as pd
from bs4 import BeautifulSoup
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from scraper.browser import create_driver


BASE_URL = "https://www.olssonparts.com"
START_URL = f"{BASE_URL}/se/sv/"
COOKIE_ACCEPT_BUTTON_SELECTOR = "button#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll"
SEARCH_INPUT_ID = "header-bottom-input"
PRODUCT_CARD_SELECTOR = "div.product-shell"
PRODUCT_PRICE_SELECTOR = "div.product-price__main"
NO_RESULTS_SELECTOR = ".search-no-result, .search-result__empty, .empty-search-result"
DEFAULT_QUERY = "VOE"
DEFAULT_OUTPUT_PATH = Path("data/olsson_products.xlsx")
OUTPUT_COLUMNS = [
    "product_name",
    "article_number",
    "reference_number",
    "product_price",
    "image_url",
    "product_type",
    "product_url",
]


def accept_cookies(driver, wait_time: int = 5) -> None:
    try:
        button = WebDriverWait(driver, wait_time).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, COOKIE_ACCEPT_BUTTON_SELECTOR))
        )
        driver.execute_script("arguments[0].click();", button)
    except TimeoutException:
        pass


def search_voe_reference(driver, voe_reference: str) -> list[dict]:
    search_input = _wait_for_search_input(driver)
    _set_search_query(driver, search_input, voe_reference)
    search_input.send_keys(Keys.ENTER)
    _wait_for_search_results(driver)
    return _extract_products(driver.page_source)


def scrape_products(query: str = DEFAULT_QUERY, headless: bool = False) -> dict[str, list]:
    driver = create_driver(headless=headless)

    try:
        driver.get(START_URL)
        if not headless:
            driver.maximize_window()
        accept_cookies(driver)

        products = search_voe_reference(driver, query)
        return products_to_output_data(products)
    finally:
        driver.quit()


def products_to_output_data(products: list[dict]) -> dict[str, list]:
    data = {column: [] for column in OUTPUT_COLUMNS}

    for product in products:
        data["product_name"].append(product["product_name"])
        data["article_number"].append(product["article_number"])
        data["reference_number"].append(product["reference_number"])
        data["product_price"].append(product["product_price"])
        data["image_url"].append(product["image_url"])
        data["product_type"].append(product["product_type"])
        data["product_url"].append(product["product_url"])

    return data


def save_output_to_excel(data: dict[str, list], output_path: Path = DEFAULT_OUTPUT_PATH) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(data)
    df.to_excel(output_path, index=False, engine="openpyxl")


def run(query: str = DEFAULT_QUERY, output_path: Path = DEFAULT_OUTPUT_PATH, headless: bool = False) -> dict[str, list]:
    data = scrape_products(query=query, headless=headless)
    print(data)
    save_output_to_excel(data, output_path=output_path)
    return data


def _wait_for_search_input(driver, wait_time: int = 10):
    return WebDriverWait(driver, wait_time).until(
        EC.presence_of_element_located((By.ID, SEARCH_INPUT_ID))
    )


def _set_search_query(driver, search_input, query: str) -> None:
    driver.execute_script(
        """
        const input = arguments[0];
        const value = arguments[1];
        input.value = value;
        input.dispatchEvent(new Event('input', { bubbles: true }));
        input.dispatchEvent(new Event('change', { bubbles: true }));
        """,
        search_input,
        query.strip(),
    )


def _wait_for_search_results(driver, wait_time: int = 10) -> None:
    wait = WebDriverWait(driver, wait_time)
    wait.until(
        EC.any_of(
            EC.presence_of_element_located((By.CSS_SELECTOR, PRODUCT_CARD_SELECTOR)),
            EC.presence_of_element_located((By.CSS_SELECTOR, NO_RESULTS_SELECTOR)),
        )
    )

    if driver.find_elements(By.CSS_SELECTOR, NO_RESULTS_SELECTOR):
        return

    try:
        wait.until(lambda current_driver: _has_rendered_prices(current_driver))
    except TimeoutException:
        # Some result cards may not expose a price, so we keep the scrape going
        # if the cards are already present.
        pass


def _extract_products(page_source: str) -> list[dict]:
    soup = BeautifulSoup(page_source, "html.parser")
    products = []

    for card in soup.select(PRODUCT_CARD_SELECTOR):
        product = _parse_product_card(card)
        if pd.notna(product["reference_number"]):
            products.append(product)

    return products


def _parse_product_card(card) -> dict:
    name = card.select_one("h3.product-card__name")
    article = card.select_one("p.product-card__article-number > span")
    reference = card.select_one("p.product-card__reference-number > span")
    price = card.select_one("div.product-price__main")
    image = card.select_one("img.product-card__image")
    manufacturer = card.select_one("img.product-card__manufacturer-logo")
    link = card.select_one("a.product-card__url")

    image_url = _absolute_url(image.get("src")) if image else np.nan
    product_url = _absolute_url(link.get("href")) if link and link.get("href") else np.nan
    reference_number = _text_or_nan(reference)
    product_price = _text_or_nan(price)
    product_type = manufacturer.get("alt") if manufacturer else np.nan

    return {
        "product_name": _text_or_nan(name),
        "article_number": _text_or_nan(article),
        "reference_number": reference_number,
        "product_price": product_price,
        "image_url": image_url,
        "product_type": product_type,
        "product_url": product_url,
        # Compatibility fields used by main.py / csv_store.py
        "voe_reference": reference_number,
        "price": product_price,
        "picture": image_url,
        "selling_info": product_type,
        "availability": np.nan,
    }


def _has_rendered_prices(driver) -> bool:
    price_elements = driver.find_elements(By.CSS_SELECTOR, PRODUCT_PRICE_SELECTOR)
    if not price_elements:
        return False

    return any(element.text.strip() for element in price_elements)


def _text_or_nan(element):
    if not element:
        return np.nan
    text = element.get_text(strip=True)
    return text if text else np.nan


def _absolute_url(path: str | None):
    if not path:
        return np.nan
    if path.startswith("http://") or path.startswith("https://"):
        return path
    return f"{BASE_URL}{path}"


if __name__ == "__main__":
    run()
