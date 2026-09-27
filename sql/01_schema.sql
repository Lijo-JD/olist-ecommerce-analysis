
-- ===========================================================================
-- Olist E-Commerce Analytics — PostgreSQL Schema
-- ===========================================================================
-- This script is idempotent: it drops and recreates all tables.
-- Run order matters because of FK-free design (we intentionally do not add
-- foreign keys — see note at the bottom).
-- ===========================================================================

DROP TABLE IF EXISTS order_reviews CASCADE;
DROP TABLE IF EXISTS order_payments CASCADE;
DROP TABLE IF EXISTS order_items CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS customers CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS sellers CASCADE;
DROP TABLE IF EXISTS geolocation CASCADE;
DROP TABLE IF EXISTS category_translation CASCADE;

-- ---------------------------------------------------------------------------
-- customers
-- One row per (order-scoped) customer record. Note: `customer_id` is
-- per-order. `customer_unique_id` is the true customer identity.
-- ---------------------------------------------------------------------------
CREATE TABLE customers (
    customer_id              VARCHAR(50) PRIMARY KEY,
    customer_unique_id       VARCHAR(50) NOT NULL,
    customer_zip_code_prefix INTEGER,
    customer_city            VARCHAR(100),
    customer_state           CHAR(2)
);

-- ---------------------------------------------------------------------------
-- geolocation
-- Brazilian zip code → lat/lng lookup. Not a key table; may have many rows
-- per zip prefix. We keep it normalized and use it opportunistically.
-- ---------------------------------------------------------------------------
CREATE TABLE geolocation (
    geolocation_zip_code_prefix INTEGER,
    geolocation_lat             DOUBLE PRECISION,
    geolocation_lng             DOUBLE PRECISION,
    geolocation_city            VARCHAR(100),
    geolocation_state           CHAR(2)
);

-- ---------------------------------------------------------------------------
-- order_items
-- Composite PK (order_id, order_item_id): an order has one or more items.
-- ---------------------------------------------------------------------------
CREATE TABLE order_items (
    order_id            VARCHAR(50) NOT NULL,
    order_item_id       INTEGER NOT NULL,
    product_id          VARCHAR(50) NOT NULL,
    seller_id           VARCHAR(50) NOT NULL,
    shipping_limit_date TIMESTAMP,
    price               NUMERIC(10, 2),
    freight_value       NUMERIC(10, 2),
    PRIMARY KEY (order_id, order_item_id)
);

-- ---------------------------------------------------------------------------
-- order_payments
-- An order may have multiple payments (split methods/installments).
-- ---------------------------------------------------------------------------
CREATE TABLE order_payments (
    order_id             VARCHAR(50) NOT NULL,
    payment_sequential   INTEGER NOT NULL,
    payment_type         VARCHAR(30),
    payment_installments INTEGER,
    payment_value        NUMERIC(10, 2),
    PRIMARY KEY (order_id, payment_sequential)
);

-- ---------------------------------------------------------------------------
-- order_reviews
-- We intentionally do NOT set a PK because the source data contains
-- duplicate review_id rows; the ETL dedupes them on load.
-- ---------------------------------------------------------------------------
CREATE TABLE order_reviews (
    review_id              VARCHAR(50),
    order_id               VARCHAR(50),
    review_score           INTEGER,
    review_comment_title   TEXT,
    review_comment_message TEXT,
    review_creation_date   TIMESTAMP,
    review_answer_timestamp TIMESTAMP
);

-- ---------------------------------------------------------------------------
-- orders
-- One row per order. Status drives which analysis filters apply.
-- ---------------------------------------------------------------------------
CREATE TABLE orders (
    order_id                     VARCHAR(50) PRIMARY KEY,
    customer_id                  VARCHAR(50),
    order_status                 VARCHAR(20),
    order_purchase_timestamp     TIMESTAMP,
    order_approved_at            TIMESTAMP,
    order_delivered_carrier_date TIMESTAMP,
    order_delivered_customer_date TIMESTAMP,
    order_estimated_delivery_date TIMESTAMP
);

-- ---------------------------------------------------------------------------
-- products
-- Note the misspelled column names (`lenght`) — they come from the source
-- dataset. We keep them as-is to avoid silent surprises during joins.
-- ---------------------------------------------------------------------------
CREATE TABLE products (
    product_id                 VARCHAR(50) PRIMARY KEY,
    product_category_name      VARCHAR(100),
    product_name_lenght        INTEGER,
    product_description_lenght INTEGER,
    product_photos_qty         INTEGER,
    product_weight_g           INTEGER,
    product_length_cm          INTEGER,
    product_height_cm          INTEGER,
    product_width_cm           INTEGER
);

-- ---------------------------------------------------------------------------
-- sellers
-- ---------------------------------------------------------------------------
CREATE TABLE sellers (
    seller_id              VARCHAR(50) PRIMARY KEY,
    seller_zip_code_prefix INTEGER,
    seller_city            VARCHAR(100),
    seller_state           CHAR(2)
);

-- ---------------------------------------------------------------------------
-- category_translation
-- Maps Portuguese category names to English.
-- ---------------------------------------------------------------------------
CREATE TABLE category_translation (
    product_category_name         VARCHAR(100) PRIMARY KEY,
    product_category_name_english VARCHAR(100)
);

-- ---------------------------------------------------------------------------
-- Indexes
-- Chosen to match the JOIN and WHERE patterns in our analytical queries.
-- ---------------------------------------------------------------------------
CREATE INDEX idx_orders_customer   ON orders(customer_id);
CREATE INDEX idx_orders_status     ON orders(order_status);
CREATE INDEX idx_orders_purchase   ON orders(order_purchase_timestamp);
CREATE INDEX idx_items_product     ON order_items(product_id);
CREATE INDEX idx_items_seller      ON order_items(seller_id);
CREATE INDEX idx_payments_order    ON order_payments(order_id);
CREATE INDEX idx_reviews_order     ON order_reviews(order_id);

-- ===========================================================================
-- Design notes
-- ===========================================================================
-- 1. We intentionally omit FOREIGN KEY constraints. The source dataset has
--    known orphan rows (e.g., reviews referencing missing orders). FKs would
--    cause the load to fail. Correctness is enforced at the ETL layer via
--    LEFT JOINs in the analysis code.
--
-- 2. `NUMERIC(10, 2)` is used for money to avoid floating-point rounding.
--
-- 3. Timestamps are native TIMESTAMP (not TEXT), so Postgres can index and
--    compare them efficiently.
--
-- 4. `VARCHAR(n)` lengths are chosen to comfortably exceed the longest
--    observed values in the source data.
-- ===========================================================================