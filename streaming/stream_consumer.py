"""Aggregate local Parquet files with PySpark Structured Streaming."""

from __future__ import annotations

from pathlib import Path

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, sum as spark_sum, window
from pyspark.sql.types import (
    DecimalType,
    LongType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)

ROOT = Path(__file__).resolve().parent
INPUT = ROOT / "stream_input"
CHECKPOINT = ROOT / "stream_checkpoint"

RETAIL_SCHEMA = StructType(
    [
        StructField("InvoiceNo", StringType(), nullable=False),
        StructField("StockCode", StringType(), nullable=False),
        StructField("Description", StringType(), nullable=True),
        StructField("Quantity", LongType(), nullable=False),
        StructField("InvoiceDate", TimestampType(), nullable=False),
        StructField("UnitPrice", DecimalType(18, 4), nullable=False),
        StructField("CustomerID", StringType(), nullable=True),
        StructField("Country", StringType(), nullable=False),
    ]
)


def main() -> None:
    INPUT.mkdir(parents=True, exist_ok=True)
    CHECKPOINT.mkdir(parents=True, exist_ok=True)
    spark = (
        SparkSession.builder.appName("LocalOnlineRetailStreaming")
        .master("local[*]")
        .config("spark.sql.shuffle.partitions", "4")
        .config("spark.sql.session.timeZone", "Europe/London")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")

    try:
        source = (
            # The explicit schema is the contract emitted by prep_data.py.
            spark.readStream.format("parquet")
            .schema(RETAIL_SCHEMA)
            .option("maxFilesPerTrigger", "1")
            .load(str(INPUT))
        )

        # Input filenames are published in chronological order. The watermark is
        # based on InvoiceDate event time, not the feeder's wall-clock sleep; data
        # older than the active watermark can therefore be dropped from state.
        aggregate = (
            source.withWatermark("InvoiceDate", "2 hours")
            .groupBy(
                window(col("InvoiceDate"), "10 minutes", "5 minutes"),
                col("StockCode"),
            )
            .agg(
                spark_sum(col("Quantity") * col("UnitPrice")).alias("total_revenue"),
                spark_sum(col("Quantity")).alias("total_quantity"),
            )
        )

        query = (
            # Reusing this checkpoint lets Spark remember files already consumed.
            aggregate.writeStream.format("console")
            .outputMode("update")
            .option("truncate", "false")
            .option("checkpointLocation", str(CHECKPOINT))
            .trigger(processingTime="5 seconds")
            .queryName("online_retail_window_aggregates")
            .start()
        )
        print(f"Streaming consumer running; checkpoint: {CHECKPOINT}", flush=True)
        query.awaitTermination()
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
