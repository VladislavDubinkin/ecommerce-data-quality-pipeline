{{ config(materialized='table') }}

SELECT
    order_status,
    COUNT(*)                                  AS orders,
    ROUND(AVG(delivery_days)::numeric, 1)     AS avg_delivery_days,
    ROUND(AVG(total_value)::numeric, 2)       AS avg_order_value
FROM {{ ref('mart_order_metrics') }}
GROUP BY 1