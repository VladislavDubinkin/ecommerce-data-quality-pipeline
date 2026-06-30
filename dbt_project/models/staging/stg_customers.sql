{{ config(materialized='view') }}

SELECT
    customer_id,
    customer_unique_id,
    customer_state,
    customer_zip_code_prefix
FROM {{ source('retail', 'customers') }}
WHERE customer_id IS NOT NULL