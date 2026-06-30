{{ config(materialized='view') }}

SELECT
    order_id,
    customer_id,
    order_status,
    order_purchase_timestamp::timestamp   AS purchase_ts,
    order_delivered_customer_date::timestamp AS delivered_ts
FROM {{ source('retail', 'orders') }}
WHERE order_id IS NOT NULL