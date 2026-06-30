-- 1. Monthly business performance
CREATE OR REPLACE VIEW v_monthly_performance AS
SELECT
    DATE_TRUNC('month', order_purchase_timestamp::timestamp) AS month,
    COUNT(DISTINCT order_id) AS total_orders,
    COUNT(DISTINCT customer_id) AS unique_customers,
    ROUND(SUM(total_value)::numeric, 2) AS revenue,
    ROUND(AVG(total_value)::numeric, 2) AS avg_order_value,
    ROUND(AVG(delivery_days)::numeric, 1) AS avg_delivery_days
FROM order_metrics
GROUP BY 1
ORDER BY 1;

-- 2. Delivery quality by order status
CREATE OR REPLACE VIEW v_delivery_quality AS
SELECT
    order_status,
    COUNT(*) AS orders,
    ROUND(AVG(delivery_days)::numeric, 1) AS avg_delivery_days,
    ROUND(AVG(total_value)::numeric, 2) AS avg_order_value,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 1) AS pct_of_total
FROM order_metrics
GROUP BY 1
ORDER BY 2 DESC;

-- 3. Customer segmentation summary
CREATE OR REPLACE VIEW v_customer_segments AS
SELECT
    customer_segment,
    COUNT(*)                                        AS customers,
    ROUND(AVG(lifetime_value)::numeric, 2) AS avg_ltv,
    ROUND(AVG(total_orders)::numeric, 1) AS avg_orders,
    ROUND(AVG(avg_delivery_days)::numeric, 1) AS avg_delivery_days
FROM customer_stats
GROUP BY 1;

-- 4. Data quality summary
CREATE OR REPLACE VIEW v_data_quality_summary AS
SELECT
    'orders' AS table_name,
    COUNT(*) AS total_rows,
    COUNT(order_id) - COUNT(DISTINCT order_id)  AS duplicate_ids,
    SUM(CASE WHEN customer_id IS NULL THEN 1 ELSE 0 END) AS null_customer_ids,
    SUM(CASE WHEN order_purchase_timestamp IS NULL THEN 1 ELSE 0 END) AS null_timestamps,
    SUM(CASE WHEN order_status NOT IN (
            'delivered','shipped','canceled','processing',
            'approved','invoiced','created','unavailable')
            THEN 1 ELSE 0 END) AS invalid_statuses
FROM orders;

-- 5. Top product categories by revenue
CREATE OR REPLACE VIEW v_category_performance AS
SELECT
    p.product_category_name,
    COUNT(DISTINCT oi.order_id) AS orders,
    ROUND(SUM(oi.price)::numeric, 2) AS revenue,
    ROUND(AVG(oi.price)::numeric, 2) AS avg_price,
    ROUND((100.0 * SUM(oi.price) / SUM(SUM(oi.price)) OVER())::numeric, 2) AS revenue_share_pct
FROM order_items oi
JOIN products p USING (product_id)
WHERE p.product_category_name IS NOT NULL
GROUP BY 1
ORDER BY 3 DESC
LIMIT 15;