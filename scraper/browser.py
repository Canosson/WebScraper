from selenium import webdriver
from selenium.webdriver.chrome.options import Options


def create_driver(headless: bool = False):
    options = Options()

    if headless:
        options.add_argument("--headless=new")

    options.add_argument("--window-size=1440,1200")
    options.add_argument("--disable-blink-features=AutomationControlled")

    return webdriver.Chrome(options=options)