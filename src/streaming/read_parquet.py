import duckdb

duckdb.sql("""
    SELECT 
        "window".start AS start_time,
        "window".end AS end_time,
        stock_code,
        total_revenue,
        total_quantity,
        filename
    FROM 'stream_output/batch_2226/*.parquet'
""").show()
