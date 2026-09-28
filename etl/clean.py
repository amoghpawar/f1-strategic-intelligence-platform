"""
ETL STEP 2 — CLEAN
====================
Implements the cleaning rules from section 5.5 / 8.1 of the project proposal:
  - Remove duplicate records
  - Handle missing/null values
  - Standardize timestamp formats -> UTC ISO 8601
  - Standardize driver / constructor / circuit naming
  - Standardize units (track length -> km, everything else already SI)
"""
import re
import numpy as np
import pandas as pd
from dateutil import parser as dtparser


# -----------------------------------------------------------------
# Name standardization
# -----------------------------------------------------------------
def standardize_person_name(raw_name: str) -> str:
    """Converts 'VERSTAPPEN, Max' / 'MAX VERSTAPPEN' / 'Max Verstappen' -> 'Max Verstappen'."""
    if pd.isna(raw_name):
        return None
    name = str(raw_name).strip()
    if "," in name:
        last, first = [p.strip() for p in name.split(",", 1)]
        name = f"{first} {last}"
    # Title-case every word, but keep short particles lower unless first word
    words = name.split()
    fixed = [w.capitalize() if not w.isupper() or len(w) > 3 else w.capitalize() for w in words]
    return " ".join(fixed)


def standardize_title_case(raw_text: str) -> str:
    if pd.isna(raw_text):
        return None
    return str(raw_text).strip().title()


# -----------------------------------------------------------------
# Timestamp standardization -> ISO 8601 UTC string
# -----------------------------------------------------------------
def standardize_timestamp(raw_ts) -> str:
    if pd.isna(raw_ts) or raw_ts in ("", None):
        return None
    try:
        dt = dtparser.parse(str(raw_ts))
        return dt.strftime("%Y-%m-%dT%H:%M:%S")
    except (ValueError, TypeError):
        return None


# -----------------------------------------------------------------
# Unit standardization
# -----------------------------------------------------------------
def standardize_track_length_km(value, source: str) -> float:
    """f1_circuits_master.csv mixes km (formula1_official) and meters (openf1)."""
    if pd.isna(value):
        return None
    value = float(value)
    if str(source).strip().lower() == "openf1":
        return round(value / 1000.0, 3)
    return round(value, 3)


# -----------------------------------------------------------------
# Generic cleaning helpers
# -----------------------------------------------------------------
def drop_exact_duplicates(df: pd.DataFrame, subset=None) -> pd.DataFrame:
    before = len(df)
    df = df.drop_duplicates(subset=subset, keep="first").reset_index(drop=True)
    removed = before - len(df)
    if removed:
        print(f"    removed {removed} duplicate row(s)")
    return df


def fill_numeric_median(df: pd.DataFrame, cols):
    for c in cols:
        if c in df.columns and df[c].isna().any():
            med = df[c].median()
            n = df[c].isna().sum()
            df[c] = df[c].fillna(med)
            print(f"    imputed {n} missing '{c}' value(s) with median={med:.2f}")
    return df


def interpolate_numeric(df: pd.DataFrame, cols, group_col=None):
    """Linear interpolation within each group (e.g. within a driver's lap sequence)."""
    for c in cols:
        if c not in df.columns:
            continue
        n_missing = df[c].isna().sum()
        if n_missing == 0:
            continue
        if group_col:
            df[c] = df.groupby(group_col)[c].transform(lambda s: s.interpolate(limit_direction="both"))
        else:
            df[c] = df[c].interpolate(limit_direction="both")
        df[c] = df[c].fillna(df[c].median())
        print(f"    interpolated {n_missing} missing '{c}' value(s)")
    return df


# -----------------------------------------------------------------
# Per-dataset cleaning functions
# -----------------------------------------------------------------
def clean_drivers_master(df: pd.DataFrame) -> pd.DataFrame:
    print("  cleaning f1_drivers_master ...")
    df = drop_exact_duplicates(df)
    df["full_name_clean"] = df["full_name"].apply(standardize_person_name)
    df["nationality"] = df["nationality"].apply(standardize_title_case)
    df["team_name"] = df["team_name"].apply(standardize_title_case)
    df["date_of_birth"] = df["date_of_birth"].astype(str).str.replace("/", "-", regex=False)
    df = df.dropna(subset=["driver_id"])
    return df


def clean_constructors_master(df: pd.DataFrame) -> pd.DataFrame:
    print("  cleaning f1_constructors_master ...")
    df = drop_exact_duplicates(df)
    df["constructor_name_clean"] = df["constructor_name"].apply(standardize_title_case)
    df["team_name"] = df["team_name"].apply(standardize_title_case)
    return df


def clean_circuits_master(df: pd.DataFrame) -> pd.DataFrame:
    print("  cleaning f1_circuits_master ...")
    df = drop_exact_duplicates(df)
    df["circuit_name_clean"] = df["circuit_name"].apply(standardize_title_case)
    df["track_length_km_clean"] = df.apply(
        lambda r: standardize_track_length_km(r["track_length_km"], r["source"]), axis=1
    )
    df = fill_numeric_median(df, ["altitude_m"])
    df["city"] = df["city"].fillna("Unknown")
    return df


def clean_race_events(df: pd.DataFrame) -> pd.DataFrame:
    print("  cleaning f1_race_events ...")
    df = drop_exact_duplicates(df)
    df["race_date_clean"] = df["race_date"].apply(standardize_timestamp)
    df["session_date_clean"] = df["session_date"].apply(standardize_timestamp)
    df["race_name_clean"] = df["race_name"].apply(standardize_title_case)
    return df


def clean_openf1_laps(df: pd.DataFrame) -> pd.DataFrame:
    print("  cleaning openf1_laps ...")
    df = drop_exact_duplicates(df, subset=["session_key", "driver_number", "lap_number", "lap_duration"])
    df["driver_code"] = df["driver_code"].str.upper()
    df["compound"] = df["compound"].str.upper()
    # interpolate missing sector/lap times within each (session, driver) lap sequence
    df["_seq_key"] = df["session_key"].astype(str) + "_" + df["driver_number"].astype(str)
    df = interpolate_numeric(df, ["lap_duration", "sector_1_time", "sector_2_time", "sector_3_time"],
                              group_col="_seq_key")
    df.drop(columns=["_seq_key"], inplace=True)
    return df


def clean_pit_stops(df: pd.DataFrame, duration_col: str) -> pd.DataFrame:
    print(f"  cleaning pit stops ({duration_col}) ...")
    df = drop_exact_duplicates(df)
    df = fill_numeric_median(df, [duration_col])
    return df


def clean_weather(df: pd.DataFrame, ts_col: str) -> pd.DataFrame:
    print(f"  cleaning weather ({ts_col}) ...")
    df = drop_exact_duplicates(df)
    df[f"{ts_col}_clean"] = df[ts_col].apply(standardize_timestamp)
    numeric_cols = [c for c in ["humidity", "rainfall", "rain", "wind_speed"] if c in df.columns]
    df = fill_numeric_median(df, numeric_cols)
    return df


def clean_stints(df: pd.DataFrame) -> pd.DataFrame:
    print("  cleaning fastf1_stints ...")
    df = drop_exact_duplicates(df)
    df["compound"] = df["compound"].str.upper()
    df = fill_numeric_median(df, ["end_lap"])
    return df


def clean_race_results(df: pd.DataFrame) -> pd.DataFrame:
    print("  cleaning fastf1_race_results ...")
    df = drop_exact_duplicates(df)
    df["driver_clean"] = df["driver"].apply(standardize_person_name)
    df = fill_numeric_median(df, ["grid_position"])
    df["points"] = df["points"].fillna(0)
    return df


def clean_fia_reports(df: pd.DataFrame) -> pd.DataFrame:
    print("  cleaning fia_reports ...")
    df = drop_exact_duplicates(df)
    df["driver_clean"] = df["driver"].apply(standardize_person_name)
    df["penalty"] = df["penalty"].fillna("None")
    df["penalty_reason"] = df["penalty_reason"].fillna("None")
    return df


def clean_all(tables: dict) -> dict:
    """Applies all cleaning rules and returns a new dict of cleaned DataFrames."""
    print("Running cleaning rules on extracted tables...")
    clean = dict(tables)  # shallow copy; we overwrite specific keys below

    clean["f1_drivers_master"] = clean_drivers_master(tables["f1_drivers_master"])
    clean["f1_constructors_master"] = clean_constructors_master(tables["f1_constructors_master"])
    clean["f1_circuits_master"] = clean_circuits_master(tables["f1_circuits_master"])
    clean["f1_race_events"] = clean_race_events(tables["f1_race_events"])

    clean["openf1_laps"] = clean_openf1_laps(tables["openf1_laps"])
    clean["openf1_pit_stops"] = clean_pit_stops(tables["openf1_pit_stops"], "pit_duration")
    clean["fastf1_pit_stops"] = clean_pit_stops(tables["fastf1_pit_stops"], "pit_stop_duration_s")
    clean["openf1_weather"] = clean_weather(tables["openf1_weather"], "date")
    clean["openweather"] = clean_weather(tables["openweather"], "timestamp")
    clean["fastf1_stints"] = clean_stints(tables["fastf1_stints"])
    clean["fastf1_race_results"] = clean_race_results(tables["fastf1_race_results"])
    clean["fia_reports"] = clean_fia_reports(tables["fia_reports"])

    print("Cleaning complete.")
    return clean


if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from extract import extract_all

    raw = extract_all()
    cleaned = clean_all(raw)
    print("\nRow counts after cleaning:")
    for name in ["f1_drivers_master", "f1_circuits_master", "openf1_laps", "fastf1_race_results"]:
        print(f"  {name:28s} {len(cleaned[name]):>8,} rows")
