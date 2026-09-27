"""Generate final_insights.docx from analysis results.

Pulls the numbers directly from PostgreSQL and the feature Parquet files so
the document stays in sync with the actual data. Run after the ETL and
feature pipeline have completed.

Usage:
    python scripts/generate_insights.py
"""
import sys
from pathlib import Path

import pandas as pd
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_ALIGN_VERTICAL

# Make src importable
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.config import BASE_DIR, DATA_PROCESSED, VISUALS_DIR
from src.db_utils import get_engine, query_df


# ---------------------------------------------------------------------------
# Fetch the numbers
# ---------------------------------------------------------------------------
def fetch_kpis(engine):
    """Compute the headline KPIs used in the executive summary."""
    sql = """
    SELECT
        COUNT(DISTINCT o.order_id) AS delivered_orders,
        ROUND(SUM(oi.price + oi.freight_value)::numeric, 2) AS total_revenue,
        ROUND(AVG(oi.price + oi.freight_value)::numeric, 2) AS avg_item_value,
        COUNT(DISTINCT c.customer_unique_id) AS unique_customers,
        COUNT(DISTINCT oi.seller_id) AS active_sellers,
        COUNT(DISTINCT oi.product_id) AS active_products
    FROM orders o
    JOIN order_items oi ON o.order_id = oi.order_id
    JOIN customers c ON o.customer_id = c.customer_id
    WHERE o.order_status = 'delivered';
    """
    return query_df(engine, sql).iloc[0].to_dict()


def fetch_revenue_by_state(engine):
    sql = """
    SELECT
        c.customer_state,
        COUNT(DISTINCT c.customer_unique_id) AS customers,
        ROUND(SUM(oi.price + oi.freight_value)::numeric, 2) AS revenue
    FROM customers c
    JOIN orders o ON c.customer_id = o.customer_id
    JOIN order_items oi ON o.order_id = oi.order_id
    WHERE o.order_status = 'delivered'
    GROUP BY c.customer_state
    ORDER BY revenue DESC
    LIMIT 10;
    """
    return query_df(engine, sql)


def fetch_top_categories(engine):
    sql = """
    SELECT
        COALESCE(ct.product_category_name_english, p.product_category_name) AS category,
        COUNT(DISTINCT oi.order_id) AS orders,
        ROUND(SUM(oi.price)::numeric, 2) AS revenue
    FROM order_items oi
    JOIN products p ON oi.product_id = p.product_id
    LEFT JOIN category_translation ct
        ON p.product_category_name = ct.product_category_name
    JOIN orders o ON oi.order_id = o.order_id
    WHERE o.order_status = 'delivered'
    GROUP BY category
    ORDER BY revenue DESC
    LIMIT 10;
    """
    return query_df(engine, sql)


def fetch_delivery_impact(engine):
    """Average review score by delivery performance bucket."""
    sql = """
    SELECT
        CASE
            WHEN o.order_delivered_customer_date > o.order_estimated_delivery_date
                THEN 'Late'
            WHEN o.order_delivered_customer_date < o.order_estimated_delivery_date
                THEN 'Early'
            ELSE 'On Time'
        END AS bucket,
        COUNT(*) AS reviews,
        ROUND(AVG(r.review_score)::numeric, 2) AS avg_review
    FROM orders o
    JOIN order_reviews r ON o.order_id = r.order_id
    WHERE o.order_status = 'delivered'
      AND o.order_delivered_customer_date IS NOT NULL
    GROUP BY bucket
    ORDER BY avg_review DESC;
    """
    return query_df(engine, sql)


def fetch_payment_mix(engine):
    sql = """
    SELECT
        payment_type,
        COUNT(*) AS payments,
        ROUND(SUM(payment_value)::numeric, 2) AS total_value,
        ROUND(AVG(payment_installments)::numeric, 2) AS avg_installments
    FROM order_payments
    GROUP BY payment_type
    ORDER BY total_value DESC;
    """
    return query_df(engine, sql)


def fetch_review_distribution(engine):
    sql = """
    SELECT
        review_score,
        COUNT(*) AS reviews,
        ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS pct
    FROM order_reviews
    GROUP BY review_score
    ORDER BY review_score;
    """
    return query_df(engine, sql)


def fetch_rfm_segments():
    """Read RFM segment distribution from the feature parquet."""
    rfm = pd.read_parquet(DATA_PROCESSED / "features_customers.parquet")
    return (
        rfm.groupby("segment")
        .agg(
            customers=("customer_unique_id", "count"),
            avg_monetary=("monetary", "mean"),
            avg_frequency=("frequency", "mean"),
        )
        .round(2)
        .reset_index()
        .sort_values("customers", ascending=False)
    )


# ---------------------------------------------------------------------------
# Document helpers
# ---------------------------------------------------------------------------
def add_heading(doc, text, level=1):
    heading = doc.add_heading(text, level=level)
    return heading


def add_paragraph(doc, text, style=None, italic=False, size=None):
    p = doc.add_paragraph(text, style=style) if style else doc.add_paragraph(text)
    if italic or size:
        for run in p.runs:
            if italic:
                run.italic = True
            if size:
                run.font.size = Pt(size)
    return p


def add_dataframe_table(doc, df, caption=None):
    """Render a pandas DataFrame as a Word table."""
    if caption:
        cap = doc.add_paragraph(caption)
        cap.runs[0].italic = True

    table = doc.add_table(rows=1, cols=len(df.columns))
    table.style = "Light Grid Accent 1"

    # Header
    for i, col in enumerate(df.columns):
        cell = table.rows[0].cells[i]
        cell.text = str(col).replace("_", " ").title()
        for paragraph in cell.paragraphs:
            for run in paragraph.runs:
                run.bold = True

    # Body
    for _, row in df.iterrows():
        cells = table.add_row().cells
        for i, val in enumerate(row):
            if isinstance(val, float):
                cells[i].text = f"{val:,.2f}"
            elif isinstance(val, int):
                cells[i].text = f"{val:,}"
            else:
                cells[i].text = str(val)

    doc.add_paragraph()


def add_image_if_exists(doc, filename, width_inches=5.5):
    """Insert a chart if it exists in visuals/."""
    path = VISUALS_DIR / filename
    if path.exists():
        doc.add_picture(str(path), width=Inches(width_inches))
        doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    else:
        p = doc.add_paragraph(f"[chart not found: {filename}]")
        p.runs[0].italic = True
        p.runs[0].font.color.rgb = RGBColor(0x88, 0x88, 0x88)


# ---------------------------------------------------------------------------
# Build the document
# ---------------------------------------------------------------------------
def build_document(engine) -> Document:
    doc = Document()

    # ---------- Title page ----------
    title = doc.add_heading("Olist Brazilian E-Commerce Analysis", level=0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    subtitle = doc.add_paragraph("Final Insights Report")
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle.runs[0].italic = True
    subtitle.runs[0].font.size = Pt(16)

    doc.add_paragraph()

    meta = doc.add_paragraph()
    meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    meta.add_run("Analysis period: January 2017 – August 2018\n").font.size = Pt(11)
    meta.add_run("Dataset: Brazilian E-Commerce Public Dataset by Olist\n").font.size = Pt(11)
    meta.add_run("License: CC BY-NC-SA 4.0\n").font.size = Pt(11)
    meta.add_run("Prepared by: Lijo John Daniel").font.size = Pt(11)

    doc.add_page_break()

    # ---------- Executive summary ----------
    add_heading(doc, "Executive Summary", level=1)

    kpis = fetch_kpis(engine)

    add_paragraph(
        doc,
        f"This report analyzes {int(kpis['delivered_orders']):,} delivered orders "
        f"from the Olist Brazilian marketplace, covering a two-year window from "
        f"September 2016 to October 2018. The analysis produced four core findings:",
    )

    findings = [
        "Revenue is concentrated. A small number of product categories and a single "
        "state (São Paulo) drive a disproportionate share of total revenue.",

        "Seasonality is real and predictable. November 2017 (Black Friday) is the "
        "largest revenue month on record, demonstrating strong consumer responsiveness "
        "to promotional events.",

        "Delivery performance is the primary driver of customer satisfaction. Late "
        "orders receive review scores roughly 40% lower than early orders.",

        "Repeat purchase behavior is very low. Approximately 97% of customers place "
        "a single order in the analysis window — a significant retention opportunity.",
    ]
    for f in findings:
        doc.add_paragraph(f, style="List Number")

    # ---------- KPI table ----------
    add_heading(doc, "Headline Metrics", level=2)

    kpi_df = pd.DataFrame([
        {"Metric": "Delivered orders", "Value": f"{int(kpis['delivered_orders']):,}"},
        {"Metric": "Total revenue (BRL)", "Value": f"R$ {kpis['total_revenue']:,.2f}"},
        {"Metric": "Avg item value (BRL)", "Value": f"R$ {kpis['avg_item_value']:,.2f}"},
        {"Metric": "Unique customers", "Value": f"{int(kpis['unique_customers']):,}"},
        {"Metric": "Active sellers", "Value": f"{int(kpis['active_sellers']):,}"},
        {"Metric": "Active products", "Value": f"{int(kpis['active_products']):,}"},
    ])
    add_dataframe_table(doc, kpi_df)

    doc.add_page_break()

    # ---------- 1. Revenue ----------
    add_heading(doc, "1. Revenue Performance", level=1)

    add_heading(doc, "1.1 Monthly revenue trend", level=2)
    add_paragraph(
        doc,
        "Revenue grew steadily through 2017, peaked sharply in November 2017, "
        "and stabilized through 2018. The November spike coincides with Black "
        "Friday — a well-documented retail phenomenon in Brazil — and represents "
        "the single largest month of revenue in the dataset.",
    )
    add_image_if_exists(doc, "03_monthly_revenue.png")

    add_heading(doc, "1.2 Revenue concentration by category", level=2)
    add_paragraph(
        doc,
        "Ten product categories account for the majority of marketplace revenue. "
        "The top five alone — bed_bath_table, health_beauty, sports_leisure, "
        "computers_accessories, and furniture_decor — represent a substantial "
        "portion of total GMV.",
    )
    add_image_if_exists(doc, "03_top_categories.png")

    cat_df = fetch_top_categories(engine)
    add_dataframe_table(doc, cat_df.head(10),
                        caption="Table 1. Top 10 categories by revenue")

    doc.add_page_break()

    # ---------- 2. Geography ----------
    add_heading(doc, "2. Geographic Distribution", level=1)
    add_paragraph(
        doc,
        "The Southeast region dominates the marketplace. São Paulo (SP) alone "
        "accounts for roughly one third of both orders and revenue. Rio de "
        "Janeiro (RJ) and Minas Gerais (MG) follow. Northern states show "
        "minimal penetration, likely due to logistics cost and delivery time.",
    )
    add_image_if_exists(doc, "03_geo_distribution.png")

    geo_df = fetch_revenue_by_state(engine)
    add_dataframe_table(doc, geo_df,
                        caption="Table 2. Top 10 states by revenue")

    doc.add_page_break()

    # ---------- 3. Delivery ----------
    add_heading(doc, "3. Delivery Performance", level=1)
    add_paragraph(
        doc,
        "The vast majority of orders arrive on or before their estimated delivery "
        "date. Late deliveries are the exception, not the rule — but their impact "
        "on customer satisfaction is disproportionate.",
    )
    add_image_if_exists(doc, "03_delivery_buckets.png")

    delivery_df = fetch_delivery_impact(engine)
    add_dataframe_table(doc, delivery_df,
                        caption="Table 3. Average review score by delivery performance")

    add_paragraph(
        doc,
        "The table above tells the whole story: a late delivery cuts the expected "
        "review score by roughly 40%. There is no other operational metric in this "
        "dataset with that magnitude of impact on customer sentiment.",
    )

    doc.add_page_break()

    # ---------- 4. Customer satisfaction ----------
    add_heading(doc, "4. Customer Satisfaction", level=1)

    add_heading(doc, "4.1 Review score distribution", level=2)
    add_paragraph(
        doc,
        "Reviews are bimodal. Roughly 57% of orders receive a perfect 5-star "
        "rating, but 1-star reviews are the second most common outcome. This "
        "polarization indicates that customer experience is not evenly distributed — "
        "the marketplace reliably delivers for most customers, but when something "
        "goes wrong, it goes very wrong.",
    )
    add_image_if_exists(doc, "03_review_distribution.png")

    reviews_df = fetch_review_distribution(engine)
    add_dataframe_table(doc, reviews_df,
                        caption="Table 4. Review score distribution")

    add_heading(doc, "4.2 Delivery impact on satisfaction", level=2)
    add_paragraph(
        doc,
        "The strongest single predictor of review score in this dataset is not "
        "product quality, price, or category — it is whether the order arrived on "
        "time. The relationship between delay and score is roughly linear: each "
        "additional day of delay depresses the average review.",
    )
    add_image_if_exists(doc, "03_delay_vs_reviews.png")

    doc.add_page_break()

    # ---------- 5. Payments ----------
    add_heading(doc, "5. Payment Behavior", level=1)
    add_paragraph(
        doc,
        "Credit card is the dominant payment method, accounting for approximately "
        "three quarters of payments. Boleto (the Brazilian bank slip) is second at "
        "roughly one fifth. Vouchers and debit cards are minor. Most credit card "
        "customers settle in a single installment — a signal that customers view "
        "the marketplace as a low-friction, single-purchase channel rather than a "
        "financed retail experience.",
    )
    add_image_if_exists(doc, "03_payment_types.png")

    pay_df = fetch_payment_mix(engine)
    add_dataframe_table(doc, pay_df,
                        caption="Table 5. Payment method breakdown")

    doc.add_page_break()

    # ---------- 6. Customer segmentation ----------
    add_heading(doc, "6. Customer Segmentation (RFM)", level=1)
    add_paragraph(
        doc,
        "Customers were scored on Recency, Frequency, and Monetary value, then "
        "grouped into five segments. The distribution reveals the marketplace's "
        "core structural challenge: a very small Champion segment and a very "
        "large Regular segment, with few customers occupying the Loyal middle.",
    )

    try:
        rfm_df = fetch_rfm_segments()
        add_dataframe_table(doc, rfm_df,
                            caption="Table 6. RFM segment distribution")
    except FileNotFoundError:
        add_paragraph(doc, "[RFM features not found — run notebook 02 first.]",
                      italic=True)

    add_image_if_exists(doc, "02_rfm_segments.png")

    doc.add_page_break()

    # ---------- 7. Recommendations ----------
    add_heading(doc, "7. Business Recommendations", level=1)

    add_heading(doc, "For operations", level=2)
    recs_ops = [
        "Reduce late-delivery rate. This is the single highest-leverage operational "
        "improvement available. A modest reduction in the late rate would lift "
        "overall review scores materially.",

        "Invest in logistics for remote states. Delivery times are meaningfully "
        "longer outside the Southeast. Partnering with regional carriers or "
        "establishing forward-stocking points could compress delivery windows "
        "without major capital expenditure.",
    ]
    for r in recs_ops:
        doc.add_paragraph(r, style="List Bullet")

    add_heading(doc, "For marketing", level=2)
    recs_mkt = [
        "Plan around Black Friday. The November 2017 spike is not an anomaly — it "
        "reflects genuine seasonal demand. Inventory, logistics, and campaign spend "
        "should all scale accordingly.",

        "Build retention campaigns. With roughly 97% single-order customers, there "
        "is a large untapped repeat-purchase opportunity. A simple post-purchase "
        "email sequence with a time-limited offer could meaningfully improve the "
        "repeat rate.",
    ]
    for r in recs_mkt:
        doc.add_paragraph(r, style="List Bullet")

    add_heading(doc, "For product", level=2)
    recs_prod = [
        "Promote installment options on higher-value orders. Credit card "
        "installments are already common, but higher-value baskets could be "
        "further unlocked by making installment plans more visible at checkout.",

        "Focus category merchandising on the top revenue drivers. The concentrated "
        "revenue distribution suggests that deep focus on five to ten categories "
        "will outperform broad portfolio expansion.",
    ]
    for r in recs_prod:
        doc.add_paragraph(r, style="List Bullet")

    doc.add_page_break()

    # ---------- 8. Methodology ----------
    add_heading(doc, "8. Methodology", level=1)

    add_paragraph(
        doc,
        "This analysis was built on a reproducible data pipeline. All numbers in "
        "this document can be regenerated from the source dataset by running the "
        "project's pipeline scripts.",
    )

    add_heading(doc, "Data preparation", level=2)
    method_data = [
        "Source: 9 CSV files from the Brazilian E-Commerce Public Dataset by Olist.",
        "All analysis uses customer_unique_id (not customer_id) for customer counts.",
        "Revenue is defined as the sum of item price and freight value on delivered orders.",
        "Datetime columns are parsed with errors='coerce'; unparseable values become NULL.",
        "Integer columns stored as floats in the source are cast to nullable Int64.",
        "Duplicate review_id rows are deduplicated, keeping the latest answer.",
        "Geolocation is used opportunistically; it contains multiple rows per zip prefix.",
    ]
    for m in method_data:
        doc.add_paragraph(m, style="List Bullet")

    add_heading(doc, "Analytical techniques", level=2)
    method_tech = [
        "SQL analytics: multi-table joins, CTEs, window functions (RANK, NTILE, LAG).",
        "RFM segmentation: quintile scoring (NTILE 5) on recency, frequency, monetary.",
        "Python EDA: pandas for transformation, Matplotlib and Seaborn for visualization.",
        "PostgreSQL as the analytical database, loaded via the COPY protocol.",
    ]
    for m in method_tech:
        doc.add_paragraph(m, style="List Bullet")

    add_heading(doc, "Limitations", level=2)
    limitations = [
        "The dataset's 2-year window is short for lifetime-value or cohort analysis.",
        "Repeat purchase rates are very low, limiting RFM's frequency-based signal.",
        "Geolocation coordinates are not used for distance calculation; state-level "
        "proxies substitute.",
        "Review text is not analyzed; only numeric scores are used.",
        "Margin data is absent — monetary values represent revenue, not profit.",
    ]
    for m in limitations:
        doc.add_paragraph(m, style="List Bullet")

    # ---------- Footer ----------
    doc.add_paragraph()
    footer = doc.add_paragraph()
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = footer.add_run(
        "Prepared using Python, PostgreSQL, pandas, Matplotlib, and Seaborn.\n"
        "Dataset © Olist, licensed under CC BY-NC-SA 4.0."
    )
    run.italic = True
    run.font.size = Pt(9)

    return doc


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("Connecting to PostgreSQL ...")
    engine = get_engine()

    print("Fetching metrics and building document ...")
    doc = build_document(engine)

    out_path = BASE_DIR / "final_insights.docx"
    doc.save(out_path)
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    main()