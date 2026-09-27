"""Feature engineering for Olist analytics.

Builds four analytics-ready tables from the cleaned Parquet layer:

- features_orders     : order-level cycle times, delay, temporal features
- features_customers  : RFM segmentation + satisfaction
- features_products   : aggregated product performance
- features_sellers    : aggregated seller performance

These tables are the inputs for the business analysis notebook.
"""
import time

import numpy as np
import pandas as pd

from .config import DATA_PROCESSED


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _days_between(later: pd.Series, earlier: pd.Series) -> pd.Series:
    """Return the number of days between two timestamp Series.

    Handles NaT correctly by returning NaN (not 0).
    """
    return (later - earlier).dt.total_seconds() / 86400.0


# ---------------------------------------------------------------------------
# Order-level features
# ---------------------------------------------------------------------------
def build_order_features() -> pd.DataFrame:
    """Order-level features.

    Adds:
    - order_value   : sum of item prices
    - freight_value : sum of freight
    - n_items       : count of line items
    - days_to_*     : cycle times (approval, carrier, delivery, estimate)
    - delivery_delay_days : signed delay vs estimate
    - is_late       : binary flag
    - order_month/year/dow/hour : temporal features
    """
    orders = pd.read_parquet(DATA_PROCESSED / "orders.parquet")
    items = pd.read_parquet(DATA_PROCESSED / "order_items.parquet")

    # Aggregate items to order level
    item_agg = (
        items.groupby("order_id", as_index=False)
        .agg(
            order_value=("price", "sum"),
            freight_value=("freight_value", "sum"),
            n_items=("order_item_id", "count"),
        )
    )

    df = orders.merge(item_agg, on="order_id", how="left")

    # Cycle times
    df["days_to_approval"] = _days_between(
        df["order_approved_at"], df["order_purchase_timestamp"]
    )
    df["days_to_carrier"] = _days_between(
        df["order_delivered_carrier_date"], df["order_purchase_timestamp"]
    )
    df["days_to_delivery"] = _days_between(
        df["order_delivered_customer_date"], df["order_purchase_timestamp"]
    )
    df["days_estimated"] = _days_between(
        df["order_estimated_delivery_date"], df["order_purchase_timestamp"]
    )

    # Signed delay: positive means late, negative means early
    df["delivery_delay_days"] = _days_between(
        df["order_delivered_customer_date"],
        df["order_estimated_delivery_date"],
    )
    df["is_late"] = (df["delivery_delay_days"] > 0).astype("Int64")

    # Temporal
    ts = df["order_purchase_timestamp"]
    df["order_month"] = ts.dt.to_period("M").astype(str)
    df["order_year"] = ts.dt.year
    df["order_dow"] = ts.dt.dayofweek  # 0=Monday
    df["order_hour"] = ts.dt.hour

    df.to_parquet(DATA_PROCESSED / "features_orders.parquet", index=False)
    print(f"OK    features_orders: {df.shape}")
    return df


# ---------------------------------------------------------------------------
# Customer-level features
# ---------------------------------------------------------------------------
def build_customer_features() -> pd.DataFrame:
    """Customer-level RFM and satisfaction features.

    Vectorized implementation — no Python-level lambdas, so it scales to
    millions of rows. Runs in ~2 seconds on the Olist dataset.
    """
    customers = pd.read_parquet(DATA_PROCESSED / "customers.parquet")
    orders = pd.read_parquet(DATA_PROCESSED / "features_orders.parquet")

    # Only delivered orders count toward RFM
    delivered = orders[orders["order_status"] == "delivered"].copy()

    # Merge customer metadata onto orders
    delivered = delivered.merge(
        customers[
            ["customer_id", "customer_unique_id",
             "customer_state", "customer_city"]
        ],
        on="customer_id",
        how="left",
    )

    # Snapshot = one day after the last order in the dataset
    snapshot = delivered["order_purchase_timestamp"].max() + pd.Timedelta(days=1)

    # -------- Vectorized aggregation --------
    # Standard groupby — all reductions are built-in C-level operations
    # (max, nunique, sum, mean), so this is fast.
    grouped = delivered.groupby("customer_unique_id", sort=False)

    rfm = grouped.agg(
        last_order_ts=("order_purchase_timestamp", "max"),
        frequency=("order_id", "nunique"),
        monetary=("order_value", "sum"),
        avg_order_value=("order_value", "mean"),
        n_late_orders=("is_late", "sum"),
        avg_delivery_days=("days_to_delivery", "mean"),
        state=("customer_state", "first"),
        city=("customer_city", "first"),
    ).reset_index()

    # Compute recency as a vectorized subtraction (not a lambda)
    rfm["recency_days"] = (snapshot - rfm["last_order_ts"]).dt.days

    # Late rate
    rfm["late_rate"] = rfm["n_late_orders"] / rfm["frequency"]

    # -------- RFM quintile scores --------
    rfm["r_score"] = pd.qcut(
        rfm["recency_days"], 5, labels=[5, 4, 3, 2, 1], duplicates="drop"
    ).astype(int)
    rfm["f_score"] = pd.qcut(
        rfm["frequency"].rank(method="first"), 5,
        labels=[1, 2, 3, 4, 5], duplicates="drop"
    ).astype(int)
    rfm["m_score"] = pd.qcut(
        rfm["monetary"], 5, labels=[1, 2, 3, 4, 5], duplicates="drop"
    ).astype(int)
    rfm["rfm_total"] = rfm[["r_score", "f_score", "m_score"]].sum(axis=1)

    # -------- Segment assignment --------
    conditions = [
        (rfm["r_score"] >= 4) & (rfm["f_score"] >= 4) & (rfm["m_score"] >= 4),
        (rfm["r_score"] >= 3) & (rfm["f_score"] >= 3) & (rfm["m_score"] >= 3),
        (rfm["r_score"] <= 2) & (rfm["f_score"] >= 3),
        (rfm["r_score"] <= 2) & (rfm["f_score"] <= 2),
    ]
    rfm["segment"] = np.select(
        conditions,
        ["Champion", "Loyal", "At Risk", "Lost"],
        default="Regular",
    )

    # Drop intermediate timestamp column before saving
    rfm = rfm.drop(columns=["last_order_ts"])

    rfm.to_parquet(DATA_PROCESSED / "features_customers.parquet", index=False)
    print(f"OK    features_customers: {rfm.shape}")
    return rfm

# ---------------------------------------------------------------------------
# Product-level features
# ---------------------------------------------------------------------------
def build_product_features() -> pd.DataFrame:
    """Per-product performance metrics."""
    items = pd.read_parquet(DATA_PROCESSED / "order_items.parquet")
    products = pd.read_parquet(DATA_PROCESSED / "products.parquet")
    translation = pd.read_parquet(DATA_PROCESSED / "category_translation.parquet")
    orders = pd.read_parquet(DATA_PROCESSED / "features_orders.parquet")

    df = (
        items.merge(products, on="product_id", how="left")
        .merge(translation, on="product_category_name", how="left")
        .merge(
            orders[["order_id", "order_status", "is_late"]],
            on="order_id",
            how="left",
        )
    )
    df = df[df["order_status"] == "delivered"]

    agg = (
        df.groupby("product_id")
        .agg(
            category=("product_category_name_english", "first"),
            orders=("order_id", "nunique"),
            units_sold=("order_item_id", "count"),
            revenue=("price", "sum"),
            avg_price=("price", "mean"),
            avg_freight=("freight_value", "mean"),
            avg_weight_g=("product_weight_g", "mean"),
            late_rate=("is_late", "mean"),
        )
        .reset_index()
    )

    agg.to_parquet(DATA_PROCESSED / "features_products.parquet", index=False)
    print(f"OK    features_products: {agg.shape}")
    return agg


# ---------------------------------------------------------------------------
# Seller-level features
# ---------------------------------------------------------------------------
def build_seller_features() -> pd.DataFrame:
    """Per-seller performance metrics."""
    items = pd.read_parquet(DATA_PROCESSED / "order_items.parquet")
    sellers = pd.read_parquet(DATA_PROCESSED / "sellers.parquet")
    orders = pd.read_parquet(DATA_PROCESSED / "features_orders.parquet")

    df = (
        items.merge(sellers, on="seller_id", how="left")
        .merge(
            orders[["order_id", "order_status", "is_late", "days_to_delivery"]],
            on="order_id",
            how="left",
        )
    )
    df = df[df["order_status"] == "delivered"]

    agg = (
        df.groupby("seller_id")
        .agg(
            state=("seller_state", "first"),
            city=("seller_city", "first"),
            orders=("order_id", "nunique"),
            revenue=("price", "sum"),
            avg_order_value=("price", "mean"),
            late_rate=("is_late", "mean"),
            avg_delivery_days=("days_to_delivery", "mean"),
        )
        .reset_index()
    )

    agg.to_parquet(DATA_PROCESSED / "features_sellers.parquet", index=False)
    print(f"OK    features_sellers: {agg.shape}")
    return agg


# ---------------------------------------------------------------------------
# Timing helper
# ---------------------------------------------------------------------------
def _timed(label: str, fn, *args, **kwargs):
    """Run fn(*args, **kwargs), print how long it took, return the result.

    Used to make progress visible during long-running feature builds.
    """
    t0 = time.time()
    result = fn(*args, **kwargs)
    elapsed = time.time() - t0
    print(f"[{label}] done in {elapsed:.2f}s")
    return result


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------
def build_all_features() -> dict[str, pd.DataFrame]:
    """Build every feature table, with per-step timing.

    Prints a line per builder so you can see where time is spent.
    """
    return {
        "orders":    _timed("orders",    build_order_features),
        "customers": _timed("customers", build_customer_features),
        "products":  _timed("products",  build_product_features),
        "sellers":   _timed("sellers",   build_seller_features),
    }

if __name__ == "__main__":
    build_all_features()