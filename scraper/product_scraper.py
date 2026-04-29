from pathlib import Path

import numpy as np
import pandas as pd
from bs4 import BeautifulSoup
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from tqdm import tqdm

from scraper.browser import create_driver
from scraper.search_scraper import accept_cookies


DEFAULT_EXCEL_PATH = Path("data/olsson_products.xlsx")
PRODUCT_URL_COLUMN = "product_url"
MACHINE_MODELS_COLUMN = "machine_models"
FITS_FOR_TRIGGER_SELECTOR = "[aria-controls='accordion-content-5']"
FITS_FOR_CONTENT_SELECTOR = "#accordion-content-5"
MACHINE_MODELS_SELECTOR = "#accordion-content-5 .fits-for-category__models-link"


def enrich_products_with_machine_models(
    excel_path: Path = DEFAULT_EXCEL_PATH,
    headless: bool = False,
) -> pd.DataFrame:
    df = load_products_excel(excel_path)

    if PRODUCT_URL_COLUMN not in df.columns:
        raise KeyError(f"Missing required column: {PRODUCT_URL_COLUMN}")

    machine_models = scrape_machine_models(df[PRODUCT_URL_COLUMN].tolist(), headless=headless)
    df[MACHINE_MODELS_COLUMN] = machine_models
    save_products_excel(df, excel_path)

    return df


def load_products_excel(excel_path: Path = DEFAULT_EXCEL_PATH) -> pd.DataFrame:
    return pd.read_excel(excel_path, engine="openpyxl")


def save_products_excel(df: pd.DataFrame, excel_path: Path = DEFAULT_EXCEL_PATH) -> None:
    excel_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(excel_path, index=False, engine="openpyxl")


def scrape_machine_models(product_urls: list, headless: bool = False) -> list:
    driver = create_driver(headless=headless)
    machine_models = []

    try:
        first_url = _first_valid_url(product_urls)
        if first_url:
            driver.get(first_url)
            accept_cookies(driver)

        for url in tqdm(product_urls, desc="Scraping product details"):
            machine_models.append(scrape_machine_models_from_url(driver, url))
    finally:
        driver.quit()

    return machine_models


def scrape_machine_models_from_url(driver, product_url) -> str | float:
    if pd.isna(product_url) or not str(product_url).strip():
        return np.nan

    driver.get(str(product_url).strip())
    _open_fits_for_section(driver)

    models = extract_machine_models(driver.page_source)
    if not models:
        return np.nan

    return ", ".join(models)


def extract_machine_models(page_source: str) -> list[str]:
    soup = BeautifulSoup(page_source, "html.parser")
    models = []

    for link in soup.select(MACHINE_MODELS_SELECTOR):
        model = link.get_text(strip=True)
        if model and model not in models:
            models.append(model)

    return models


def _open_fits_for_section(driver, wait_time: int = 10) -> None:
    wait = WebDriverWait(driver, wait_time)

    try:
        trigger = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, FITS_FOR_TRIGGER_SELECTOR))
        )
        if trigger.get_attribute("aria-expanded") != "true":
            driver.execute_script("arguments[0].click();", trigger)

        wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, FITS_FOR_CONTENT_SELECTOR))
        )
        wait.until(
            lambda current_driver: _panel_has_models(current_driver.page_source)
            or _panel_is_open(current_driver)
        )
    except TimeoutException:
        pass


def _panel_has_models(page_source: str) -> bool:
    return MACHINE_MODELS_SELECTOR in page_source or "fits-for-category__models-link" in page_source


def _panel_is_open(driver) -> bool:
    try:
        content = driver.find_element(By.CSS_SELECTOR, FITS_FOR_CONTENT_SELECTOR)
    except Exception:
        return False

    aria_hidden = content.get_attribute("aria-hidden")
    return aria_hidden in (None, "false")


def _first_valid_url(product_urls: list) -> str | None:
    for url in product_urls:
        if pd.notna(url) and str(url).strip():
            return str(url).strip()
    return None


def run(excel_path: Path = DEFAULT_EXCEL_PATH, headless: bool = False) -> pd.DataFrame:
    df = enrich_products_with_machine_models(excel_path=excel_path, headless=headless)
    print(
        f"Updated {excel_path} with '{MACHINE_MODELS_COLUMN}' for {len(df)} products."
    )
    return df


if __name__ == "__main__":
    run()
