
-- ===========================================================================
-- Olist — Analysis Queries
-- ===========================================================================
-- Each section is delimited by -- @@NAME so notebooks can run them
-- independently. Each section is a complete SELECT.
-- ===========================================================================

-- @@KPI_OVERVIEW
-- Top-level business KPIs.
SELECT
    COUNT(DISTINCT o.order_id)                       AS delivered_orders,
    ROUND(SUM(oi.price + oi.freight_value), 2)       AS total_revenue,
    ROUND(AVG(oi.price + oi.freight_value), 2)       AS avg_item_value,
    COUNT(DISTINCT c.customer_unique_id)             AS unique_customers,
    COUNT(DISTINCT oi.seller_id)                     AS active_sellers,
    COUNT(DISTINCT oi.product_id)                    AS active_products
FROM orders o
JOIN order_items oi ON o.order_id = oi.order_id
JOIN customers   c  ON o.customer_id = c.customer_id
WHERE o.order_status = 'delivered';

-- @@ORDER_STATUS
-- Distribution of order statuses.
SELECT
    order_status,
    COUNT(*)                                              AS orders,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2)    AS pct
FROM orders
GROUP BY order_status
ORDER BY orders DESC;

-- @@MONTHLY_REVENUE
-- Revenue per calendar month. Filters to the period with complete data.
SELECT
    TO_CHAR(DATE_TRUNC('month', o.order_purchase_timestamp),
            'YYYY-MM')                                   AS year_month,
    COUNT(DISTINCT o.order_id)                           AS orders,
    ROUND(SUM(oi.price + oi.freight_value), 2)           AS revenue
FROM orders o
JOIN order_items oi ON o.order_id = oi.order_id
WHERE o.order_status = 'delivered'
  AND o.order_purchase_timestamp >= DATE '2017-01-01'
  AND o.order_purchase_timestamp <  DATE '2018-09-01'
GROUP BY year_month
ORDER BY year_month;

-- @@TOP_CATEGORIES
-- Top 15 product categories by revenue.
SELECT
    COALESCE(ct.product_category_name_english,
             p.product_category_name)                    AS category,
    COUNT(DISTINCT oi.order_id)                          AS orders,
    ROUND(SUM(oi.price), 2)                              AS revenue,
    ROUND(AVG(oi.price), 2)                              AS avg_price
FROM order_items oi
JOIN products p  ON oi.product_id = p.product_id
LEFT JOIN category_translation ct
    ON p.product_category_name = ct.product_category_name
JOIN orders o    ON oi.order_id = o.order_id
WHERE o.order_status = 'delivered'
GROUP BY category
ORDER BY revenue DESC
LIMIT 15;

-- @@GEO_REVENUE
-- Revenue and customer count by state.
SELECT
    c.customer_state,
    COUNT(DISTINCT c.customer_unique_id)                 AS customers,
    ROUND(SUM(oi.price + oi.freight_value), 2)           AS revenue,
    ROUND(SUM(oi.price + oi.freight_value) /
          COUNT(DISTINCT c.customer_unique_id), 2)       AS revenue_per_customer
FROM customers c
JOIN orders o       ON c.customer_id = o.customer_id
JOIN order_items oi ON o.order_id = oi.order_id
WHERE o.order_status = 'delivered'
GROUP BY c.customer_state
ORDER BY revenue DESC;

-- @@DELIVERY_PERF
-- Delivery performance buckets: early, on time, late.
SELECT
    CASE
        WHEN o.order_delivered_customer_date > o.order_estimated_delivery_date
            THEN 'Late'
        WHEN o.order_delivered_customer_date < o.order_estimated_delivery_date
            THEN 'Early'
        ELSE 'On Time'
    END                                                  AS delivery_status,
    COUNT(*)                                             AS orders,
    ROUND(COUNT(*) * 100.0 /
          SUM(COUNT(*)) OVER (), 2)                      AS pct,
    ROUND(AVG(
        EXTRACT(EPOCH FROM (
            o.order_delivered_customer_date
            - o.order_purchase_timestamp
        )) / 86400
    ), 1)                                                AS avg_days
FROM orders o
WHERE o.order_status = 'delivered'
  AND o.order_delivered_customer_date IS NOT NULL
GROUP BY delivery_status
ORDER BY orders DESC;

-- @@REVIEW_DISTRIBUTION
-- Review score distribution.
SELECT
    review_score,
    COUNT(*)                                             AS reviews,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2)   AS pct
FROM order_reviews
GROUP BY review_score
ORDER BY review_score;

-- @@PAYMENT_TYPES
-- Payment method breakdown.
SELECT
    payment_type,
    COUNT(*)                              AS payments,
    ROUND(AVG(payment_installments), 2)   AS avg_installments,
    ROUND(AVG(payment_value), 2)          AS avg_value,
    ROUND(SUM(payment_value), 2)          AS total_value
FROM order_payments
GROUP BY payment_type
ORDER BY total_value DESC;