"""Smoke tests for the ETL pipeline.

These run against PostgreSQL (via the `engine` fixture in conftest.py).
The schema in sql/01_schema.sql is executed verbatim — no dialect
translation, no SQLite compatibility shims.
"""
import pandas as pd

from src.db_utils import query_df
from src.etl import transform


# ---------------------------------------------------------------------------
# Schema tests — require the `engine` fixture (Postgres)
# ---------------------------------------------------------------------------
def test_schema_creates_expected_tables(engine):
    """All 9 tables should exist in the public schema."""
    sql = """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_type = 'BASE TABLE';
    """
    tables = set(query_df(engine, sql)["table_name"])
    expected = {
        "customers", "geolocation", "order_items", "order_payments",
        "order_reviews", "orders", "products", "sellers",
        "category_translation",
    }
    assert expected.issubset(tables), f"Missing tables: {expected - tables}"


def test_schema_uses_native_timestamps(engine):
    """Timestamps should be native Postgres types, not TEXT."""
    sql = """
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'orders';
    """
    cols = dict(query_df(engine, sql).values)
    assert cols["order_purchase_timestamp"] == "timestamp without time zone"


def test_schema_indexes_are_created(engine):
    """All declared indexes should exist."""
    sql = """
        SELECT indexname
        FROM pg_indexes
        WHERE schemaname = 'public';
    """
    indexes = set(query_df(engine, sql)["indexname"])
    expected = {
        "idx_orders_customer",
        "idx_orders_status",
        "idx_orders_purchase",
        "idx_items_product",
        "idx_items_seller",
        "idx_payments_order",
        "idx_reviews_order",
    }
    assert expected.issubset(indexes), f"Missing indexes: {expected - indexes}"


# ---------------------------------------------------------------------------
# Transform tests — pure pandas, no DB required
# ---------------------------------------------------------------------------
def test_transform_parses_datetimes():
    """Date strings become datetime64."""
    raw = {"orders": pd.DataFrame({
        "order_id": ["a"],
        "order_purchase_timestamp": ["2017-05-01 10:00:00"],
    })}
    out = transform(raw)["orders"]
    assert pd.api.types.is_datetime64_any_dtype(out["order_purchase_timestamp"])


def test_transform_strips_strings():
    """Whitespace is stripped from string columns."""
    raw = {"customers": pd.DataFrame({
        "customer_id": ["  abc  "],
        "customer_unique_id": ["  xyz  "],
    })}
    out = transform(raw)["customers"]
    assert out["customer_id"].iloc[0] == "abc"
    assert out["customer_unique_id"].iloc[0] == "xyz"


def test_transform_dedupes_reviews():
    """Reviews dedupe on review_id, keeping the latest answer."""
    raw = {"reviews": pd.DataFrame({
        "review_id": ["r1", "r1"],
        "order_id": ["o1", "o1"],
        "review_score": [3, 5],
        "review_answer_timestamp": [
            "2018-01-01 10:00:00",
            "2018-01-02 10:00:00",
        ],
    })}
    out = transform(raw)["reviews"]
    assert len(out) == 1
    assert out["review_score"].iloc[0] == 5


def test_transform_casts_float_integers():
    """Float-stored integers (e.g. '40.0') become true integers."""
    raw = {"products": pd.DataFrame({
        "product_id": ["p1", "p2"],
        "product_name_lenght": [40.0, 29.0],
        "product_weight_g": [500.0, 250.0],
    })}
    out = transform(raw)["products"]
    assert pd.api.types.is_integer_dtype(out["product_name_lenght"])
    assert out["product_name_lenght"].iloc[0] == 40


def test_transform_preserves_nulls_in_integer_columns():
    """Nullable integer columns retain nulls after casting."""
    raw = {"products": pd.DataFrame({
        "product_id": ["p1", "p2"],
        "product_weight_g": [500.0, None],
    })}
    out = transform(raw)["products"]
    assert out["product_weight_g"].iloc[0] == 500
    assert pd.isna(out["product_weight_g"].iloc[1])

def test_transform_does_not_touch_parquet():
    """transform() must be a pure function — no writes to data/processed/."""
    import pandas as pd
    from src.config import DATA_PROCESSED
    from src.etl import transform

    target = DATA_PROCESSED / "orders.parquet"
    mtime_before = target.stat().st_mtime if target.exists() else None

    raw = {"orders": pd.DataFrame({
        "order_id": ["a"],
        "order_purchase_timestamp": ["2017-05-01 10:00:00"],
    })}
    transform(raw)

    mtime_after = target.stat().st_mtime if target.exists() else None
    assert mtime_before == mtime_after, (
        "transform() modified data/processed/orders.parquet — it must be a "
        "pure function with no disk side effects."
    )