# Databricks notebook source
catalog_name = "aerospace_demo"
schema1_name = "telemetry"
schema2_name = "test_facility"

# COMMAND ----------

# DBTITLE 1,Create catalogue
from datetime import datetime, timedelta

remove_after_date = (datetime(2025, 5, 11) + timedelta(days=90)).strftime('%Y%m%d')

spark.sql(f"CREATE CATALOG IF NOT EXISTS {catalog_name}")

spark.sql(f"ALTER CATALOG {catalog_name} SET TAGS ('removeafter' = '{remove_after_date}')")

# COMMAND ----------

# DBTITLE 1,Load sample data
import os

csv_files = [f for f in os.listdir("sample_data") if f.endswith(".csv")]

for csv_filename in csv_files:
    schema_name, table_name, _ = csv_filename.split(".")
    file_path = os.path.abspath(os.path.join("sample_data", csv_filename))
    print(file_path)
    file_path = f"file:{file_path}"

    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog_name}.{schema_name}")
    spark.sql(
        f"ALTER SCHEMA {catalog_name}.{schema_name} SET TAGS ('removeafter' = '{remove_after_date}')"
    )

    (
        spark.read.format("csv")
        .option("header", "true")
        .option("inferSchema", "true")
        .load(file_path)
        .write.format("delta")
        .option("delta.columnMapping.mode", "name")
        .mode("overwrite")
        .saveAsTable(f"{catalog_name}.{schema_name}.{table_name}")
    )

    spark.sql(
        f"""
        ALTER TABLE {catalog_name}.{schema_name}.{table_name}
        SET TAGS ('removeafter' = '{remove_after_date}')
    """)

# COMMAND ----------

# DBTITLE 1,Create derivative tables
spark.sql(f"""
CREATE OR REPLACE TABLE `{catalog_name}`.`{schema2_name}`.comp_performance_summary AS
SELECT 
    EngineID,
    AVG(MaxPressureRatio) AS avg_pressure,
    MAX(MaxPressureRatio) AS max_pressure,
    MIN(MaxPressureRatio) AS min_pressure,
    COUNT(*) AS reading_count
FROM 
    `{catalog_name}`.`{schema1_name}`.compressorhighpressure
GROUP BY 
    EngineID
""")

spark.sql(f"""
CREATE OR REPLACE TABLE `{catalog_name}`.`{schema2_name}`.bearing_counts AS
SELECT 
    SensorType,
    Parameter,
    COUNT(SensorID) AS bearing_count
FROM 
    `{catalog_name}`.`{schema1_name}`.sensor
GROUP BY ALL
""")