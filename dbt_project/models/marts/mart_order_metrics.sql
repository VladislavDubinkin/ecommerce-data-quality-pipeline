{{ config(materialized='table') }}

WITH orders AS (
    SELECT * FROM {{ ref('stg_orders') }}
),
items AS (
    SELECT * FROM {{ ref('stg_order_items') }}
)

SELECT
    o.order_id,
    o.customer_id,
    o.order_status,
    o.purchase_ts,
    DATE_PART('day', o.delivered_ts - o.purchase_ts) AS delivery_days,
    ROUND(SUM(i.price)::numeric, 2)                  AS total_value,
    COUNT(i.order_item_id)                           AS items_count
FROM orders o
JOIN items i USING (order_id)
GROUP BY 1, 2, 3, 4, 5