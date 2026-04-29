import sys

from scraper.product_scraper import run as run_product_scraper
from scraper.search_scraper import (
    DEFAULT_OUTPUT_PATH,
    DEFAULT_QUERY,
    run as run_search_scraper,
)


def main() -> None:
    query = sys.argv[1].strip() if len(sys.argv) > 1 else DEFAULT_QUERY

    data = run_search_scraper(
        query=query,
        output_path=DEFAULT_OUTPUT_PATH,
        headless=False,
    )

    print(f"Scraped {len(data['product_name'])} products to {DEFAULT_OUTPUT_PATH}.")

    enriched_df = run_product_scraper(
        excel_path=DEFAULT_OUTPUT_PATH,
        headless=False,
    )

    print(
        f"Added machine_models for {len(enriched_df)} products in {DEFAULT_OUTPUT_PATH}."
    )


if __name__ == "__main__":
    main()
