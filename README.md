# Replacement Parts Web Scraper

A two-stage Selenium-based scraper that searches an online replacement parts catalog, extracts product listings, and enriches each result with compatible machine models — all saved to Excel.

## What it does

1. **Search scrape** — searches the parts catalog by a query string (e.g. a reference number) and collects: product name, article number, reference number, price, image URL, product type, and product page URL.
2. **Product enrichment** — visits each product URL and extracts the list of machine models the part fits, adding a `machine_models` column to the output file.

## Output

Results are saved to `data/olsson_products.xlsx` with the following columns:

| Column | Description |
|---|---|
| `product_name` | Part name |
| `article_number` | Supplier article number |
| `reference_number` | OEM reference number |
| `product_price` | Listed price |
| `image_url` | Product image URL |
| `product_type` | Manufacturer / brand |
| `product_url` | Link to the product page |
| `machine_models` | Compatible machine models (added in stage 2) |

## Setup

Requires Python 3.13+ and [uv](https://github.com/astral-sh/uv), plus Google Chrome installed.

```bash
uv sync
source .venv/bin/activate
```

## Usage

```bash
# Run both stages with the default query
python main.py

# Run with a custom reference number or keyword
python main.py "123456"
```

To run a single stage independently:

```bash
# Stage 1 only: search and save product listings
python -m scraper.search_scraper

# Stage 2 only: enrich an existing Excel file with machine models
python -m scraper.product_scraper
```

## Dependencies

- `selenium` — browser automation (Chrome)
- `beautifulsoup4` — HTML parsing
- `pandas` / `openpyxl` — data handling and Excel output
- `tqdm` — progress bar during enrichment
