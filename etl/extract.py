"""
ETL STEP 1 — EXTRACT
=====================
Loads every raw source file (as produced by the 5 simulated source systems:
OpenF1, FastF1, OpenWeather, FIA, Formula1.com) into pandas DataFrames.

This module performs NO cleaning or transformation — it is a pure extraction
layer, matching section 8.1 "Extraction" of the project proposal.

Run standalone for a smoke test:  python3 extract.py
"""
import os
import pandas as pd

RAW_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "raw_data")


def _csv(path):
    return pd.read_csv(os.path.join(RAW_DIR, path))


def _json(path):
    return pd.read_json(os.path.join(RAW_DIR, path))


def extract_all():
    """Returns a dict of {dataset_name: DataFrame} for every raw source file."""
    data = {}

    # --- OpenF1 API (telemetry, lap times, sectors, pit stops, weather, sessions)
    data["openf1_sessions"] = _json("openf1/sessions.json")
    data["openf1_drivers"] = _json("openf1/drivers.json")
    data["openf1_laps"] = _json("openf1/laps.json")
    data["openf1_pit_stops"] = _json("openf1/pit_stops.json")
    data["openf1_weather"] = _json("openf1/weather.json")
    data["openf1_positions"] = _json("openf1/positions.json")

    # --- FastF1 (official timing, telemetry, tyre compounds, lap info)
    data["fastf1_race_results"] = _csv("fastf1/race_results.csv")
    data["fastf1_stints"] = _csv("fastf1/stints.csv")
    data["fastf1_qualifying"] = _csv("fastf1/qualifying.csv")
    data["fastf1_pit_stops"] = _csv("fastf1/pit_stops.csv")
    data["fastf1_lap_data"] = _csv("fastf1/lap_data.csv")

    # --- OpenWeather API
    data["openweather"] = _json("openweather/weather.json")

    # --- FIA official reports
    data["fia_reports"] = _csv("fia/race_reports.csv")

    # --- Formula1.com official website
    data["f1_drivers_master"] = _csv("formula1/drivers_master.csv")
    data["f1_constructors_master"] = _csv("formula1/constructors_master.csv")
    data["f1_circuits_master"] = _csv("formula1/circuits_master.csv")
    data["f1_race_events"] = _csv("formula1/race_events.csv")
    data["f1_driver_standings"] = _csv("formula1/driver_standings.csv")
    data["f1_constructor_standings"] = _csv("formula1/constructor_standings.csv")
    data["f1_race_calendar"] = _csv("formula1/race_calendar.csv")

    # --- Telemetry (high-frequency, kept separate — very large)
    data["telemetry"] = _csv("telemetry/telemetry.csv")

    return data


if __name__ == "__main__":
    tables = extract_all()
    print(f"Extracted {len(tables)} raw tables from {RAW_DIR}:")
    for name, df in tables.items():
        print(f"  {name:28s} {len(df):>8,} rows   {len(df.columns):>2} cols")
