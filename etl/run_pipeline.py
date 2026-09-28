"""
RUN PIPELINE — orchestrates Extract -> Clean -> Transform -> Load
====================================================================
Usage:
    python3 run_pipeline.py            # loads into SQLite demo warehouse
    python3 run_pipeline.py --mysql    # loads into a real MySQL server
                                          (edit the connection details below,
                                           or set them as environment variables)
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract import extract_all
from clean import clean_all
from transform_star_schema import transform_all
from load_to_warehouse import load_all


def main():
    parser = argparse.ArgumentParser(description="F1 BI ETL pipeline")
    parser.add_argument("--mysql", action="store_true", help="load into MySQL instead of SQLite")
    parser.add_argument("--host", default=os.environ.get("F1_DW_HOST", "localhost"))
    parser.add_argument("--user", default=os.environ.get("F1_DW_USER", "root"))
    parser.add_argument("--password", default=os.environ.get("F1_DW_PASSWORD", ""))
    parser.add_argument("--database", default=os.environ.get("F1_DW_DATABASE", "f1_dw"))
    args = parser.parse_args()

    print("=" * 70)
    print("F1 STRATEGIC INTELLIGENCE PLATFORM — ETL PIPELINE")
    print("=" * 70)

    print("\n[1/4] EXTRACT")
    raw = extract_all()

    print("\n[2/4] CLEAN")
    cleaned = clean_all(raw)

    print("\n[3/4] TRANSFORM (star schema)")
    star = transform_all(cleaned)

    print("\n[4/4] LOAD")
    if args.mysql:
        from load_to_warehouse import load_to_mysql, load_to_csv
        load_to_csv(star)  # always keep CSVs too, for Power BI / backup
        load_to_mysql(star, host=args.host, user=args.user,
                      password=args.password, database=args.database)
        print(f"\nLoaded into MySQL database '{args.database}' at {args.host}.")
        print("Make sure sql/schema_mysql.sql was run on that database first.")
    else:
        load_all(star, target="sqlite")
        print("\nLoaded into SQLite demo warehouse: data_warehouse/f1_dw.sqlite")
        print("To point this at real MySQL instead, run: python3 run_pipeline.py --mysql")

    print("\nPipeline complete. Star schema tables also written to data_warehouse/csv/")


if __name__ == "__main__":
    main()
