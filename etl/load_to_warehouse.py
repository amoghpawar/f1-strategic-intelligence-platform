"""
ETL STEP 4 — LOAD
====================
Writes the star schema (from transform_star_schema.py) to:
  1. CSV files under data_warehouse/csv/   -> ready for MySQL LOAD DATA INFILE,
     Power BI's "Get Data > Text/CSV", or Excel.
  2. A runnable SQLite database data_warehouse/f1_dw.sqlite -> lets you (and
     anyone marking this project) query the finished warehouse immediately
     without needing a MySQL server installed. The schema is intentionally
     kept MySQL-compatible (see sql/schema_mysql.sql) so switching the actual
     production target to MySQL is a connection-string change, not a redesign.

To load into a REAL MySQL server instead, run sql/schema_mysql.sql on your
server, then use load_to_mysql() below (requires `pip install mysql-connector-python`).
"""
import os
import sqlite3
import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_DIR = os.path.join(PROJECT_ROOT, "data_warehouse", "csv")
SQLITE_PATH = os.path.join(PROJECT_ROOT, "data_warehouse", "f1_dw.sqlite")

TABLE_ORDER = [
    "dim_driver", "dim_constructor", "dim_circuit", "dim_race", "dim_weather",
    "fact_race_performance", "fact_lap_telemetry",
]


def load_to_csv(star: dict):
    os.makedirs(CSV_DIR, exist_ok=True)
    print(f"Writing star schema CSVs to {CSV_DIR} ...")
    for name in TABLE_ORDER:
        path = os.path.join(CSV_DIR, f"{name}.csv")
        star[name].to_csv(path, index=False)
        print(f"  wrote {name:26s} {len(star[name]):>8,} rows -> {os.path.basename(path)}")


def load_to_sqlite(star: dict):
    """Runnable demo warehouse — same schema/keys as the MySQL DDL, just a
    different engine so the project is immediately queryable in this sandbox."""
    if os.path.exists(SQLITE_PATH):
        os.remove(SQLITE_PATH)
    print(f"\nLoading star schema into SQLite demo warehouse: {SQLITE_PATH}")
    conn = sqlite3.connect(SQLITE_PATH)
    for name in TABLE_ORDER:
        star[name].to_sql(name, conn, index=False, if_exists="replace")
        print(f"  loaded table {name}")
    # basic indexes mirroring the MySQL DDL, for query performance
    cur = conn.cursor()
    cur.execute("CREATE INDEX IF NOT EXISTS idx_fact_race_driver ON fact_race_performance(driver_sk)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_fact_race_race ON fact_race_performance(race_sk)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_fact_lap_driver ON fact_lap_telemetry(driver_sk)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_fact_lap_race ON fact_lap_telemetry(race_sk)")
    conn.commit()
    conn.close()
    print("SQLite load complete.")


def load_to_mysql(star: dict, host="localhost", user="root", password="", database="f1_dw"):
    """
    Loads the star schema into a REAL MySQL server.
    Requires: pip install mysql-connector-python sqlalchemy
    Run sql/schema_mysql.sql on the target database FIRST to create the tables.
    """
    from sqlalchemy import create_engine
    conn_str = f"mysql+mysqlconnector://{user}:{password}@{host}/{database}"
    engine = create_engine(conn_str)
    for name in TABLE_ORDER:
        star[name].to_sql(name, engine, if_exists="append", index=False, method="multi", chunksize=5000)
        print(f"  loaded table {name} into MySQL ({database}.{name})")


def load_all(star: dict, target="sqlite"):
    load_to_csv(star)
    if target == "sqlite":
        load_to_sqlite(star)
    elif target == "mysql":
        load_to_mysql(star)
    else:
        raise ValueError("target must be 'sqlite' or 'mysql'")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from extract import extract_all
    from clean import clean_all
    from transform_star_schema import transform_all

    raw = extract_all()
    cleaned = clean_all(raw)
    star = transform_all(cleaned)
    load_all(star, target="sqlite")

    # smoke-test query against the loaded warehouse
    conn = sqlite3.connect(SQLITE_PATH)
    q = """
    SELECT d.driver_name, COUNT(*) AS races, SUM(f.championship_points) AS total_points
    FROM fact_race_performance f
    JOIN dim_driver d ON d.driver_sk = f.driver_sk
    GROUP BY d.driver_name
    ORDER BY total_points DESC
    LIMIT 5
    """
    print("\nSmoke test — top 5 drivers by total (synthetic) points:")
    print(pd.read_sql(q, conn).to_string(index=False))
    conn.close()
