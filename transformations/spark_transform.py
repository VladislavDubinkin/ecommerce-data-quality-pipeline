import logging
import os
from dotenv import load_dotenv
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def get_jdbc_config() -> tuple[str, dict]:
    load_dotenv()
    url = (
        f"jdbc:postgresql://"
        f"{os.getenv('POSTGRES_HOST', 'localhost')}:"
        f"{os.getenv('POSTGRES_PORT', '5432')}/"
        f"{os.getenv('POSTGRES_DB', 'retail')}"
    )
    props = {
        "user": os.getenv("POSTGRES_USER", "postgres"),
        "password": os.getenv("POSTGRES_PASSWORD", "changeme"),
        "driver": "org.postgresql.Driver",
    }
    return url, props


def build_spark_session() -> SparkSession:
    return (
        SparkSession.builder
        .appName("Olist E-Commerce ETL")
        .config("spark.jars.packages", "org.postgresql:postgresql:42.6.0")
        .getOrCreate()
    )


def read_table(spark: SparkSession, table: str, jdbc_url: str, props: dict):
    logger.info(f"Reading table '{table}' from PostgreSQL...")
    return spark.read.jdbc(url=jdbc_url, table=table, properties=props)


def write_table(df, table: str, jdbc_url: str, props: dict) -> None:
    logger.info(f"Writing to '{table}'...")
    df.write.jdbc(url=jdbc_url, table=table, mode="overwrite", properties=props)
    logger.info(f"Table '{table}' written successfully.")


def build_order_metrics(orders, order_items):
    """
    Job 1: order-level metrics.
    Joins orders with order_items; computes total value,
    item count, and delivery duration per order.
    """
    return (
        orders
        .join(order_items, on="order_id", how="inner")
        .withColumn("delivery_days",
            F.datediff(
                F.col("order_delivered_customer_date"),
                F.col("order_purchase_timestamp")
            )
        )
        .groupBy(
            "order_id", "customer_id",
            "order_status", "order_purchase_timestamp"
        )
        .agg(
            F.round(F.sum("price"), 2).alias("total_value"),
            F.count("order_item_id").alias("items_count"),
            F.first("delivery_days").alias("delivery_days")
        )
    )


def build_customer_stats(order_metrics):
    """
    Job 2: customer lifetime value and segmentation.
    Aggregates order history per customer and assigns a value segment.
    """
    return (
        order_metrics
        .groupBy("customer_id")
        .agg(
            F.count("order_id").alias("total_orders"),
            F.round(F.sum("total_value"), 2).alias("lifetime_value"),
            F.round(F.avg("delivery_days"), 1).alias("avg_delivery_days")
        )
        .withColumn("customer_segment",
            F.when(F.col("lifetime_value") > 500, "high_value")
             .when(F.col("lifetime_value") > 100, "mid_value")
             .otherwise("low_value")
        )
    )


def build_monthly_revenue(order_metrics):
    """
    Job 3: monthly cohort revenue.
    Aggregates revenue, unique customers, and order count by calendar month.
    """
    return (
        order_metrics
        .withColumn("month",
            F.date_trunc("month", F.col("order_purchase_timestamp"))
        )
        .groupBy("month")
        .agg(
            F.round(F.sum("total_value"), 2).alias("revenue"),
            F.countDistinct("customer_id").alias("unique_customers"),
            F.count("order_id").alias("total_orders")
        )
        .orderBy("month")
    )


def run_transformations() -> None:
    spark = build_spark_session()
    jdbc_url, jdbc_props = get_jdbc_config()

    try:
        orders = read_table(spark, "orders", jdbc_url, jdbc_props)
        order_items = read_table(spark, "order_items", jdbc_url, jdbc_props)

        logger.info("Running Job 1: order-level metrics...")
        order_metrics = build_order_metrics(orders, order_items)
        order_metrics.cache()
        write_table(order_metrics, "order_metrics", jdbc_url, jdbc_props)

        logger.info("Running Job 2: customer lifetime value and segmentation...")
        write_table(
            build_customer_stats(order_metrics),
            "customer_stats", jdbc_url, jdbc_props
        )

        logger.info("Running Job 3: monthly cohort revenue...")
        write_table(
            build_monthly_revenue(order_metrics),
            "monthly_revenue", jdbc_url, jdbc_props
        )

        logger.info("All 3 transformation jobs completed successfully.")

    except Exception as e:
        logger.error(f"Transformation pipeline failed: {e}")
        raise
    finally:
        order_metrics.unpersist()
        spark.stop()
        logger.info("Spark session closed.")


if __name__ == "__main__":
    run_transformations()