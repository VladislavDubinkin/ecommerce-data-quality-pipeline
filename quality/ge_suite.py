import logging
import os
from unittest import suite
from dotenv import load_dotenv
import great_expectations as gx
from great_expectations.expectations import (
    ExpectColumnValuesToNotBeNull,
    ExpectColumnValuesToBeUnique,
    ExpectColumnValuesToBeInSet,
    ExpectColumnValuesToBeBetween,
    ExpectColumnValuesToMatchRegex,
    ExpectTableRowCountToBeBetween,
    ExpectColumnProportionOfUniqueValuesToBeBetween,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

load_dotenv()


def get_connection_string() -> str:
    return (
        f"postgresql+psycopg2://"
        f"{os.getenv('POSTGRES_USER', 'postgres')}:"
        f"{os.getenv('POSTGRES_PASSWORD', 'changeme')}@"
        f"{os.getenv('POSTGRES_HOST', 'localhost')}:"
        f"{os.getenv('POSTGRES_PORT', '5432')}/"
        f"{os.getenv('POSTGRES_DB', 'retail')}"
    )


def create_fresh_suite(context, suite_name: str) -> gx.ExpectationSuite:
    """Создает абсолютно чистый сьют, перезаписывая старый во избежание дублирования правил."""
    return context.suites.add_or_update(gx.ExpectationSuite(name=suite_name))


def build_orders_suite(context) -> gx.ExpectationSuite:
    suite = create_fresh_suite(context, "orders_suite")
    suite.add_expectation(ExpectColumnValuesToNotBeNull(column="order_id"))
    suite.add_expectation(ExpectColumnValuesToBeUnique(column="order_id"))
    suite.add_expectation(ExpectColumnValuesToNotBeNull(column="customer_id"))
    suite.add_expectation(ExpectColumnValuesToNotBeNull(column="order_purchase_timestamp"))
    suite.add_expectation(ExpectColumnValuesToBeInSet(
        column="order_status",
        value_set=[
            "delivered", "shipped", "canceled", "processing",
            "approved", "invoiced", "created", "unavailable"
        ]
    ))
    suite.add_expectation(ExpectTableRowCountToBeBetween(
        min_value=90_000, max_value=120_000
    ))
    return suite


def build_order_items_suite(context) -> gx.ExpectationSuite:
    suite = create_fresh_suite(context, "order_items_suite")
    suite.add_expectation(ExpectColumnValuesToNotBeNull(column="order_id"))
    suite.add_expectation(ExpectColumnValuesToNotBeNull(column="product_id"))
    suite.add_expectation(ExpectColumnValuesToNotBeNull(column="seller_id"))
    suite.add_expectation(ExpectColumnValuesToBeBetween(
        column="price", min_value=0, max_value=10_000
    ))
    suite.add_expectation(ExpectColumnValuesToBeBetween(
        column="freight_value", min_value=0, max_value=5_000
    ))
    return suite


def build_customers_suite(context) -> gx.ExpectationSuite:
    suite = create_fresh_suite(context, "customers_suite")
    suite.add_expectation(ExpectColumnValuesToNotBeNull(column="customer_id"))
    suite.add_expectation(ExpectColumnProportionOfUniqueValuesToBeBetween(
        column="customer_unique_id", min_value=0.95
    ))
    suite.add_expectation(ExpectColumnValuesToNotBeNull(column="customer_state"))
    
    # ЗАМЕНЕНО: вместо регулярной строки проверяем диапазон чисел для типа bigint/int
    suite.add_expectation(ExpectColumnValuesToBeBetween(
        column="customer_zip_code_prefix",
        min_value=0,
        max_value=99999
    ))
    return suite


def run_validation(
    context,
    datasource,
    table_name: str,
    suite_name: str
) -> bool:
    try:
        asset = datasource.get_asset(name=table_name)
    except Exception:
        asset = datasource.add_table_asset(name=table_name, table_name=table_name)
        
    try:
        batch_def = asset.get_batch_definition(f"{table_name}_batch")
    except Exception:
        batch_def = asset.add_batch_definition_whole_table(f"{table_name}_batch")
        
    validation_name = f"{table_name}_validation"
    
    # ИСПРАВЛЕНО: используем add_or_update для валидации, чтобы она всегда ссылалась на свежий сьют
    vd = context.validation_definitions.add_or_update(
        gx.ValidationDefinition(
            name=validation_name,
            data=batch_def,
            suite=context.suites.get(suite_name)
        )
    )
        
    result = vd.run()
    success = result["success"]
    status = "PASSED" if success else "FAILED"
    logger.info(f"Validation for '{table_name}': {status}")
    return success


def main() -> None:
    logger.info("Initializing Great Expectations context...")
    context = gx.get_context(
        mode="file", 
        project_root_dir=r"C:\Users\vladi\ecommerce-data-quality-pipeline"
    )
    print("Context initialized at:", context.root_directory)

    # ИСПРАВЛЕНО: заменен метод и удален невалидный параметр force_add
    datasource = context.data_sources.add_or_update_postgres(
        name="retail_postgres",
        connection_string=get_connection_string()
    )

    logger.info("Building expectation suites...")
    build_orders_suite(context)
    build_order_items_suite(context)
    build_customers_suite(context)

    results = {
        "orders":      run_validation(context, datasource, "orders",      "orders_suite"),
        "order_items": run_validation(context, datasource, "order_items", "order_items_suite"),
        "customers":   run_validation(context, datasource, "customers",   "customers_suite"),
    }

    logger.info("Building Data Docs...")
    context.build_data_docs()

    passed = sum(results.values())
    total = len(results)
    logger.info(f"Validation complete: {passed}/{total} tables passed.")

    if passed < total:
        failed = [t for t, ok in results.items() if not ok]
        logger.warning(f"Failed tables: {failed}")

if __name__ == "__main__":
    main()
