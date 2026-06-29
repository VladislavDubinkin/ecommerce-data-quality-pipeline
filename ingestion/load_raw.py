import logging
import os
from pathlib import Path
from dotenv import load_dotenv
import pandas as pd
from sqlalchemy import create_engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

TABLES_MAPPING = {
    "orders":       "olist_orders_dataset.csv",
    "order_items":  "olist_order_items_dataset.csv",
    "customers":    "olist_customers_dataset.csv",
    "products":     "olist_products_dataset.csv",
    "sellers":      "olist_sellers_dataset.csv",
    "payments":     "olist_order_payments_dataset.csv",
    "reviews":      "olist_order_reviews_dataset.csv",
}

def get_db_engine():
    load_dotenv()
    url = (
        f"postgresql://{os.getenv('POSTGRES_USER', 'postgres')}"
        f":{os.getenv('POSTGRES_PASSWORD', 'changeme')}"
        f"@{os.getenv('POSTGRES_HOST', 'localhost')}"
        f":{os.getenv('POSTGRES_PORT', '5432')}"
        f"/{os.getenv('POSTGRES_DB', 'retail')}"
    )
    return create_engine(url)

def load_csv_to_postgres(data_dir: Path, tables: dict) -> None:
    try:
        engine = get_db_engine()
        logger.info("Database connection established.")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        return

    for table_name, file_name in tables.items():
        file_path = data_dir / file_name

        if not file_path.is_file():
            logger.warning(f"File not found: {file_path}. Skipping.")
            continue

        logger.info(f"Ingesting '{table_name}' from {file_name}...")
        try:
            df = pd.read_csv(file_path)
            df.to_sql(table_name, engine, if_exists="replace", index=False)
            logger.info(f"Loaded {len(df):,} rows into '{table_name}'.")
        except Exception as e:
            logger.error(f"Failed to load '{table_name}': {e}")

if __name__ == "__main__":
    RAW_DATA_DIR = Path(__file__).parent.parent / "data" / "raw"

    logger.info("Starting ingestion pipeline...")
    load_csv_to_postgres(RAW_DATA_DIR, TABLES_MAPPING)
    logger.info("Ingestion pipeline completed.")