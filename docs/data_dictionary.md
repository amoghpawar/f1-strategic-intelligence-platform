# Data Dictionary — F1 Data Warehouse (Star Schema)

## Dim_Driver
| Column | Type | Description |
|---|---|---|
| driver_sk | INT (PK) | Surrogate key |
| driver_id | VARCHAR | Natural key from source systems |
| driver_number | INT | Car number |
| driver_name | VARCHAR | Standardized "First Last" format |
| nationality | VARCHAR | Title-cased |
| current_team | VARCHAR | Most recent season's team on record |

## Dim_Constructor
| Column | Type | Description |
|---|---|---|
| constructor_sk | INT (PK) | Surrogate key |
| constructor_id | VARCHAR | Natural key |
| constructor_name | VARCHAR | Most recent season's name (post-rebrand where applicable) |
| nationality | VARCHAR | |

## Dim_Circuit
| Column | Type | Description |
|---|---|---|
| circuit_sk | INT (PK) | Surrogate key |
| circuit_id | VARCHAR | Natural key |
| circuit_name | VARCHAR | Title-cased |
| country, city | VARCHAR | |
| track_length_km | DECIMAL | Standardized to km (source unit inconsistency resolved) |
| number_of_corners | INT | |
| altitude_m | DECIMAL | Missing values median-imputed |

## Dim_Race
| Column | Type | Description |
|---|---|---|
| race_sk | INT (PK) | Surrogate key |
| race_id | VARCHAR | Natural key, format `{season}_R{round}` |
| season, round | SMALLINT | |
| grand_prix | VARCHAR | Race name |
| circuit_id | VARCHAR | FK (natural key) to Dim_Circuit |
| race_date | DATETIME | Standardized ISO 8601 |

## Dim_Weather
| Column | Type | Description |
|---|---|---|
| weather_sk | INT (PK) | Surrogate key |
| race_id | VARCHAR | One row per race (aggregated from OpenF1 race-session weather) |
| avg_air_temp, avg_track_temp, avg_humidity | DECIMAL | Session averages |
| total_rainfall_mm | DECIMAL | Session total |
| condition_flag | VARCHAR | 'Wet' if rainfall > 0.5mm, else 'Dry' |

## Fact_RacePerformance  (grain: one row per driver per race)
| Column | Type | Description |
|---|---|---|
| fact_id | INT (PK) | Surrogate key |
| race_sk, driver_sk, constructor_sk, circuit_sk, weather_sk | INT (FK) | Dimension keys |
| grid_position, finish_position | SMALLINT | |
| position_gained | SMALLINT | grid_position − finish_position (positive = gained places) |
| avg_lap_time_s, fastest_lap_time_s | DECIMAL | From OpenF1 raw lap data |
| pit_stop_count, avg_pit_stop_duration_s | INT / DECIMAL | From OpenF1 pit stops |
| dominant_tyre_compound | VARCHAR | Compound used for the most laps in the race |
| championship_points | DECIMAL | |
| status | VARCHAR | Finished / Retired / Accident / etc. |
| laps_completed | SMALLINT | |

## Fact_LapTelemetry  (grain: one row per driver per lap — lower-grain fact)
| Column | Type | Description |
|---|---|---|
| lap_fact_id | BIGINT (PK) | Surrogate key |
| race_sk, driver_sk | INT (FK) | Dimension keys |
| lap_number | SMALLINT | |
| lap_duration_s, sector_1/2/3_time_s | DECIMAL | Missing values interpolated within driver's lap sequence |
| compound, tyre_age | VARCHAR / SMALLINT | |
| is_pit_in_lap, is_pit_out_lap | BOOLEAN | |
| position | SMALLINT | Approximate running position |

## Known limitations (documented, not hidden)
- `constructor_sk = -1` in Fact_RacePerformance indicates a name-match miss
  between `fastf1_race_results.constructor` and `dim_constructor.constructor_name`
  (can happen across a mid-season rebrand) — flagged for manual review rather
  than silently dropped.
- `Fact_RacePerformance.avg_pit_stop_duration_s` is NULL where OpenF1's
  pit-stop sampling (intentionally incomplete, per the raw-data spec) didn't
  produce a record for that driver/race — not necessarily zero pit stops.
