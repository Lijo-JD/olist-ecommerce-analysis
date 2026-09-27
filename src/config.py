"""Centralized configuration for the Olist project."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

DATA_RAW = BASE_DIR / "data" / "raw"
DATA_PROCESSED = BASE_DIR / "data" / "processed"
SQL_DIR = BASE_DIR / "sql"
VISUALS_DIR = BASE_DIR / "visuals"
NOTEBOOKS_DIR = BASE_DIR / "notebooks"

for _directory in (DATA_PROCESSED, VISUALS_DIR):
    _directory.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# PostgreSQL
# ---------------------------------------------------------------------------
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_TEST_NAME = os.getenv("DB_TEST_NAME")

DATABASE_URL = (
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

TEST_DATABASE_URL = (
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_TEST_NAME}"
)

# ---------------------------------------------------------------------------
# Dataset metadata
# ---------------------------------------------------------------------------
DATASET_LICENSE = "CC BY-NC-SA 4.0"
DATASET_URL = "https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce"

CSV_FILES: dict[str, str] = {
    "customers": "olist_customers_dataset.csv",
    "geolocation": "olist_geolocation_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "payments": "olist_order_payments_dataset.csv",
    "reviews": "olist_order_reviews_dataset.csv",
    "orders": "olist_orders_dataset.csv",
    "products": "olist_products_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "category_translation": "product_category_name_translation.csv",
}

TABLE_MAPPING: dict[str, str] = {
    "customers": "customers",
    "geolocation": "geolocation",
    "order_items": "order_items",
    "payments": "order_payments",
    "reviews": "order_reviews",
    "orders": "orders",
    "products": "products",
    "sellers": "sellers",
    "category_translation": "category_translation",
}

DATE_COLUMNS: dict[str, list[str]] = {
    "orders": [
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ],
    "order_items": ["shipping_limit_date"],
    "reviews": ["review_creation_date", "review_answer_timestamp"],
}

# Columns that must be integers to match the SQL schema. Some source CSVs
# store these as floats (e.g. "40.0"), which breaks COPY. We cast explicitly.
INTEGER_COLUMNS: dict[str, list[str]] = {
    "products": [
        "product_name_lenght",
        "product_description_lenght",
        "product_photos_qty",
        "product_weight_g",
        "product_length_cm",
        "product_height_cm",
        "product_width_cm",
    ],
    "order_items": ["order_item_id"],
    "payments": ["payment_sequential", "payment_installments"],
    "reviews": ["review_score"],
    "customers": ["customer_zip_code_prefix"],
    "sellers": ["seller_zip_code_prefix"],
    "geolocation": ["geolocation_zip_code_prefix"],
}