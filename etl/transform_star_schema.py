"""
ETL STEP 3 — TRANSFORM (STAR SCHEMA BUILD)
=============================================
Consumes the cleaned tables from clean.py and produces the dimensional model
described in the Phase II architecture:

    Dim_Driver, Dim_Constructor, Dim_Circuit, Dim_Race, Dim_Weather
    Fact_RacePerformance   (grain: one row per driver per race)
    Fact_LapTelemetry      (grain: one row per driver per lap - lower-grain fact)

Surrogate integer keys are generated for every dimension; the fact tables
reference dimensions ONLY by surrogate key (standard star-schema practice).
"""
import numpy as np
import pandas as pd


# -----------------------------------------------------------------
# DIM_DRIVER
# -----------------------------------------------------------------
def build_dim_driver(
    drivers_master: pd.DataFrame,
    race_results: pd.DataFrame
) -> pd.DataFrame:
    print("  building Dim_Driver ...")

    df = drivers_master.copy()
    df = df.sort_values("season")

    # Backfill missing driver numbers from other seasons
    df["driver_number"] = df.groupby("driver_id")["driver_number"].transform(
        lambda s: s.ffill().bfill()
    )

    # Keep one canonical row per driver
    df = df.drop_duplicates(subset=["driver_id"], keep="last")

    # ---------------------------------------------------------
    # FALLBACK: add drivers appearing in race results but absent
    # from drivers_master
    # ---------------------------------------------------------
    master_numbers = set(
        pd.to_numeric(df["driver_number"], errors="coerce")
        .dropna()
        .astype(int)
    )

    race_drivers = race_results.copy()
    race_drivers["driver_number"] = pd.to_numeric(
        race_drivers["driver_number"],
        errors="coerce"
    )

    missing = race_drivers[
        race_drivers["driver_number"].notna()
        & ~race_drivers["driver_number"].astype(int).isin(master_numbers)
    ].copy()

    if not missing.empty:
        fallback = (
            missing
            .sort_values("season")
            .drop_duplicates(subset=["driver_number"], keep="last")
            .copy()
        )

        fallback["driver_id"] = (
            "fallback_" + fallback["driver_number"].astype(int).astype(str)
        )
        fallback["full_name"] = fallback["driver_clean"]
        fallback["full_name_clean"] = fallback["driver_clean"]
        fallback["driver_name"] = fallback["driver_clean"]

        for col in df.columns:
            if col not in fallback.columns:
                fallback[col] = None

        fallback = fallback[df.columns]

        df = pd.concat([df, fallback], ignore_index=True)

        print(
            f"  added {len(fallback)} missing drivers from race results"
        )

    # Create surrogate key
    df = df.reset_index(drop=True)
    df["driver_sk"] = range(1, len(df) + 1)

    return df


# -----------------------------------------------------------------
# DIM_CONSTRUCTOR
# -----------------------------------------------------------------
def build_dim_constructor(constructors_master: pd.DataFrame) -> pd.DataFrame:
    print("  building Dim_Constructor ...")
    df = constructors_master.copy()
    df = df.sort_values("season").drop_duplicates(subset=["constructor_id"], keep="last")
    dim = pd.DataFrame({
        "constructor_sk": range(1, len(df) + 1),
        "constructor_id": df["constructor_id"].values,
        "constructor_name": df["constructor_name_clean"].values,
        "nationality": df["nationality"].values,
    })
    return dim.reset_index(drop=True)


# -----------------------------------------------------------------
# DIM_CIRCUIT
# -----------------------------------------------------------------
def build_dim_circuit(circuits_master: pd.DataFrame) -> pd.DataFrame:
    print("  building Dim_Circuit ...")
    df = circuits_master.copy()
    df = df.sort_values("season").drop_duplicates(subset=["circuit_id"], keep="last")
    dim = pd.DataFrame({
        "circuit_sk": range(1, len(df) + 1),
        "circuit_id": df["circuit_id"].values,
        "circuit_name": df["circuit_name_clean"].values,
        "country": df["country"].values,
        "city": df["city"].values,
        "track_length_km": df["track_length_km_clean"].values,
        "number_of_corners": df["number_of_corners"].values,
        "altitude_m": df["altitude_m"].values,
    })
    return dim.reset_index(drop=True)


# -----------------------------------------------------------------
# DIM_RACE
# -----------------------------------------------------------------
def build_dim_race(race_events: pd.DataFrame) -> pd.DataFrame:
    print("  building Dim_Race ...")
    df = race_events.drop_duplicates(subset=["race_id"]).copy()
    dim = pd.DataFrame({
        "race_sk": range(1, len(df) + 1),
        "race_id": df["race_id"].values,
        "season": df["season"].values,
        "round": df["round"].values,
        "grand_prix": df["race_name_clean"].values,
        "circuit_id": df["circuit_id"].values,
        "race_date": df["race_date_clean"].values,
    })
    return dim.reset_index(drop=True)


# -----------------------------------------------------------------
# DIM_WEATHER  (one aggregated row per race, from openf1 race-session weather)
# -----------------------------------------------------------------
def build_dim_weather(openf1_weather: pd.DataFrame, openf1_sessions: pd.DataFrame) -> pd.DataFrame:
    print("  building Dim_Weather ...")
    race_sessions = openf1_sessions[openf1_sessions["session_name"] == "Race"][["session_key", "race_id"]]
    wx = openf1_weather.drop(columns=["race_id"]).merge(race_sessions, on="session_key", how="inner")
    agg = wx.groupby("race_id").agg(
        avg_air_temp=("air_temperature", "mean"),
        avg_track_temp=("track_temperature", "mean"),
        avg_humidity=("humidity", "mean"),
        total_rainfall_mm=("rainfall", "sum"),
    ).reset_index()
    agg["condition_flag"] = np.where(agg["total_rainfall_mm"] > 0.5, "Wet", "Dry")
    agg = agg.round(2)
    dim = pd.DataFrame({
        "weather_sk": range(1, len(agg) + 1),
        "race_id": agg["race_id"].values,
        "avg_air_temp": agg["avg_air_temp"].values,
        "avg_track_temp": agg["avg_track_temp"].values,
        "avg_humidity": agg["avg_humidity"].values,
        "total_rainfall_mm": agg["total_rainfall_mm"].values,
        "condition_flag": agg["condition_flag"].values,
    })
    return dim.reset_index(drop=True)


# -----------------------------------------------------------------
# FACT_RACE_PERFORMANCE  (grain: one row per driver per race)
# -----------------------------------------------------------------
def build_fact_race_performance(cleaned: dict, dims: dict) -> pd.DataFrame:
    print("  building Fact_RacePerformance ...")
    results = cleaned["fastf1_race_results"].copy()
    qual = cleaned["fastf1_qualifying"].copy()
    laps = cleaned["openf1_laps"].copy()
    stints = cleaned["fastf1_stints"].copy()
    pits_openf1 = cleaned["openf1_pit_stops"].copy()
    race_events = cleaned["f1_race_events"][["race_id", "season", "round", "circuit_id"]].drop_duplicates()

    dim_driver = dims["dim_driver"]
    dim_constructor = dims["dim_constructor"]
    dim_race = dims["dim_race"]
    dim_weather = dims["dim_weather"]

    # --- base: race_results already has season/round/driver/constructor/points/status
    base = results.merge(race_events, on=["season", "round"], how="left")

    # --- avg / fastest lap time per (race_id, driver_number) from openf1 raw laps
    lap_agg = laps.groupby(["race_id", "driver_number"]).agg(
        avg_lap_time_s=("lap_duration", "mean"),
        fastest_lap_time_s=("lap_duration", "min"),
    ).reset_index()
    base = base.merge(lap_agg, on=["race_id", "driver_number"], how="left")

    # --- pit stop count + avg duration per (race_id, driver_number)
    pit_agg = pits_openf1.groupby(["race_id", "driver_number"]).agg(
        pit_stop_count=("pit_duration", "count"),
        avg_pit_stop_duration_s=("pit_duration", "mean"),
    ).reset_index()
    base = base.merge(pit_agg, on=["race_id", "driver_number"], how="left")
    base["pit_stop_count"] = base["pit_stop_count"].fillna(0).astype(int)

    # --- dominant tyre compound per (season, race_name, driver) from fastf1 stints
    stint_len = stints.groupby(["season", "race", "driver", "compound"])["stint_length"].sum().reset_index()
    dominant = stint_len.sort_values("stint_length", ascending=False).drop_duplicates(
        subset=["season", "race", "driver"], keep="first"
    )[["season", "race", "driver", "compound"]].rename(
        columns={"race": "race_name", "compound": "dominant_tyre_compound"}
    )
    base = base.merge(dominant, on=["season", "race_name", "driver"], how="left")

    # --- position gained (positive = gained places)
    base["position_gained"] = base["grid_position"] - base["finish_position"]

    # --- resolve surrogate keys
    driver_lookup = dim_driver.set_index("driver_number")["driver_sk"]
    base["driver_sk"] = base["driver_number"].map(driver_lookup)

    # constructor: join via constructors_master name match on the base 'constructor' text field
    def _normalize_key(s):
        return str(s).strip().lower().replace(" ", "")

    CONSTRUCTOR_ALIASES = {
        "AlphaTauri": "Racing Bulls",
        "RB": "Racing Bulls",
        "Alfa Romeo": "Kick Sauber",
    }
    base["constructor_norm"] = base["constructor"].replace(CONSTRUCTOR_ALIASES)
    base["_con_key"] = base["constructor_norm"].apply(_normalize_key)

    dim_constructor["_con_key"] = dim_constructor["constructor_name"].apply(_normalize_key)
    con_key_to_sk = dim_constructor.set_index("_con_key")["constructor_sk"]

    base["constructor_sk"] = base["_con_key"].map(con_key_to_sk)
    base["constructor_sk"] = base["constructor_sk"].fillna(-1).astype(int)

    race_sk_lookup = dim_race.set_index("race_id")["race_sk"]
    base["race_sk"] = base["race_id"].map(race_sk_lookup)

    weather_sk_lookup = dim_weather.set_index("race_id")["weather_sk"]
    base["weather_sk"] = base["race_id"].map(weather_sk_lookup)

    circuit_id_lookup = race_events.set_index("race_id")["circuit_id"]
    dim_circuit_sk_lookup = dims["dim_circuit"].set_index("circuit_id")["circuit_sk"]
    base["circuit_id_tmp"] = base["race_id"].map(circuit_id_lookup)
    base["circuit_sk"] = base["circuit_id_tmp"].map(dim_circuit_sk_lookup)

    fact = pd.DataFrame({
        "fact_id": range(1, len(base) + 1),
        "race_sk": base["race_sk"].values,
        "driver_sk": base["driver_sk"].values,
        "constructor_sk": base["constructor_sk"].values,
        "circuit_sk": base["circuit_sk"].values,
        "weather_sk": base["weather_sk"].values,
        "grid_position": base["grid_position"].values,
        "finish_position": base["finish_position"].values,
        "position_gained": base["position_gained"].values,
        "avg_lap_time_s": base["avg_lap_time_s"].round(3).values,
        "fastest_lap_time_s": base["fastest_lap_time_s"].round(3).values,
        "pit_stop_count": base["pit_stop_count"].values,
        "avg_pit_stop_duration_s": base["avg_pit_stop_duration_s"].round(2).values,
        "dominant_tyre_compound": base["dominant_tyre_compound"].values,
        "championship_points": base["points"].values,
        "status": base["status"].values,
        "laps_completed": base["laps_completed"].values,
    })
    return fact


# -----------------------------------------------------------------
# FACT_LAP_TELEMETRY (lower grain: one row per driver per lap; used for
# tyre-degradation / consistency drill-downs that Fact_RacePerformance can't answer)
# -----------------------------------------------------------------
def build_fact_lap_telemetry(cleaned: dict, dims: dict) -> pd.DataFrame:
    print("  building Fact_LapTelemetry ...")
    laps = cleaned["openf1_laps"].copy()
    dim_driver = dims["dim_driver"]
    dim_race = dims["dim_race"]

    driver_lookup = dim_driver.set_index("driver_number")["driver_sk"]
    race_lookup = dim_race.set_index("race_id")["race_sk"]

    laps["driver_sk"] = laps["driver_number"].map(driver_lookup)
    laps["race_sk"] = laps["race_id"].map(race_lookup)

    fact = pd.DataFrame({
        "lap_fact_id": range(1, len(laps) + 1),
        "race_sk": laps["race_sk"].values,
        "driver_sk": laps["driver_sk"].values,
        "lap_number": laps["lap_number"].values,
        "lap_duration_s": laps["lap_duration"].values,
        "sector_1_time_s": laps["sector_1_time"].values,
        "sector_2_time_s": laps["sector_2_time"].values,
        "sector_3_time_s": laps["sector_3_time"].values,
        "compound": laps["compound"].values,
        "tyre_age": laps["tyre_age"].values,
        "is_pit_in_lap": laps["is_pit_in_lap"].values,
        "is_pit_out_lap": laps["is_pit_out_lap"].values,
        "position": laps["position"].values,
    })
    return fact


def transform_all(cleaned: dict) -> dict:
    print("Running transformation (star schema build)...")
    dims = {}
    dims["dim_driver"] = build_dim_driver(
    cleaned["f1_drivers_master"],
    cleaned["fastf1_race_results"]
)
    dims["dim_constructor"] = build_dim_constructor(cleaned["f1_constructors_master"])
    dims["dim_circuit"] = build_dim_circuit(cleaned["f1_circuits_master"])
    dims["dim_race"] = build_dim_race(cleaned["f1_race_events"])
    dims["dim_weather"] = build_dim_weather(cleaned["openf1_weather"], cleaned["openf1_sessions"])

    facts = {}
    facts["fact_race_performance"] = build_fact_race_performance(cleaned, dims)
    facts["fact_lap_telemetry"] = build_fact_lap_telemetry(cleaned, dims)

    print("Transformation complete.")
    return {**dims, **facts}


if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from extract import extract_all
    from clean import clean_all

    raw = extract_all()
    cleaned = clean_all(raw)
    star = transform_all(cleaned)

    print("\nStar schema table sizes:")
    for name, df in star.items():
        print(f"  {name:26s} {len(df):>8,} rows   {len(df.columns):>2} cols")
    print("\nSample Fact_RacePerformance row:")
    print(star["fact_race_performance"].head(3).to_string())
