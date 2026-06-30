{{ config(materialized='view') }}

SELECT
    order_id,
    order_item_id,
    product_id,
    seller_id,
    price,
    freight_value
FROM {{ source('retail', 'order_items') }}
WHERE order_id IS NOT NULL
  AND price >= 0