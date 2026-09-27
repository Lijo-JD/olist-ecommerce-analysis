
-- ===========================================================================
-- Olist — Advanced Queries (CTEs, window functions)
-- ===========================================================================

-- @@MOM_GROWTH
-- Month-over-month revenue growth with running total.
WITH monthly AS (
    SELECT
        DATE_TRUNC('month', o.order_purchase_timestamp)::date AS month_start,
        SUM(oi.price + oi.freight_value)                      AS revenue
    FROM orders o
    JOIN order_items oi ON o.order_id = oi.order_id
    WHERE o.order_status = 'delivered'
      AND o.order_purchase_timestamp >= DATE '2017-01-01'
    GROUP BY month_start
)
SELECT
    TO_CHAR(month_start, 'YYYY-MM')                          AS year_month,
    ROUND(revenue, 2)                                        AS revenue,
    ROUND(SUM(revenue) OVER (ORDER BY month_start), 2)       AS running_total,
    ROUND(
        (revenue - LAG(revenue) OVER (ORDER BY month_start))
        * 100.0
        / NULLIF(LAG(revenue) OVER (ORDER BY month_start), 0),
        2
    )                                                        AS mom_growth_pct
FROM monthly
ORDER BY month_start;

-- @@TOP_CATEGORY_PER_YEAR
-- Top 5 categories per year, using RANK() partitioned by year.
WITH category_revenue AS (
    SELECT
        EXTRACT(YEAR FROM o.order_purchase_timestamp)::int    AS year,
        COALESCE(ct.product_category_name_english,
                 p.product_category_name)                     AS category,
        SUM(oi.price)                                         AS revenue
    FROM orders o
    JOIN order_items oi ON o.order_id = oi.order_id
    JOIN products p     ON oi.product_id = p.product_id
    LEFT JOIN category_translation ct
        ON p.product_category_name = ct.product_category_name
    WHERE o.order_status = 'delivered'
    GROUP BY year, category
),
ranked AS (
    SELECT
        year, category, revenue,
        RANK() OVER (PARTITION BY year ORDER BY revenue DESC) AS rank
    FROM category_revenue
)
SELECT year, category, ROUND(revenue, 2) AS revenue, rank
FROM ranked
WHERE rank <= 5
ORDER BY year, rank;

-- @@RFM
-- Customer RFM segmentation using NTILE quintiles.
WITH customer_agg AS (
    SELECT
        c.customer_unique_id,
        MAX(o.order_purchase_timestamp)::date  AS last_order_date,
        COUNT(DISTINCT o.order_id)             AS frequency,
        SUM(oi.price + oi.freight_value)       AS monetary
    FROM customers c
    JOIN orders o        ON c.customer_id = o.customer_id
    JOIN order_items oi  ON o.order_id = oi.order_id
    WHERE o.order_status = 'delivered'
    GROUP BY c.customer_unique_id
),
rfm_base AS (
    SELECT
        customer_unique_id,
        ((SELECT MAX(order_purchase_timestamp)::date FROM orders)
          - last_order_date)                    AS recency_days,
        frequency,
        monetary
    FROM customer_agg
),
rfm_scored AS (
    SELECT
        *,
        NTILE(5) OVER (ORDER BY recency_days DESC) AS r_score,
        NTILE(5) OVER (ORDER BY frequency ASC)     AS f_score,
        NTILE(5) OVER (ORDER BY monetary ASC)      AS m_score
    FROM rfm_base
)
SELECT
    customer_unique_id,
    recency_days,
    frequency,
    ROUND(monetary, 2)                              AS monetary,
    r_score, f_score, m_score,
    (r_score + f_score + m_score)                   AS rfm_total,
    CASE
        WHEN r_score >= 4 AND f_score >= 4 AND m_score >= 4 THEN 'Champion'
        WHEN r_score >= 3 AND f_score >= 3 AND m_score >= 3 THEN 'Loyal'
        WHEN r_score <= 2 AND f_score >= 3                  THEN 'At Risk'
        WHEN r_score <= 2 AND f_score <= 2                  THEN 'Lost'
        ELSE 'Regular'
    END                                              AS segment
FROM rfm_scored
ORDER BY rfm_total DESC;

-- @@DELAY_VS_REVIEWS
-- Does late delivery hurt review scores?
SELECT
    r.review_score,
    COUNT(*)                                             AS reviews,
    ROUND(AVG(
        EXTRACT(EPOCH FROM (
            o.order_delivered_customer_date
            - o.order_estimated_delivery_date
        )) / 86400
    ), 2)                                                AS avg_delay_days,
    ROUND(AVG(
        EXTRACT(EPOCH FROM (
            o.order_delivered_customer_date
            - o.order_purchase_timestamp
        )) / 86400
    ), 1)                                                AS avg_delivery_days
FROM orders o
JOIN order_reviews r ON o.order_id = r.order_id
WHERE o.order_status = 'delivered'
  AND o.order_delivered_customer_date IS NOT NULL
GROUP BY r.review_score
ORDER BY r.review_score;