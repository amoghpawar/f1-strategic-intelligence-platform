# RAW DATA METADATA — Formula 1 Strategic Intelligence Platform

**SYNTHETIC RAW-LIKE DATA FOR ACADEMIC BI PROJECT**

All datasets below are 100% synthetically generated. Driver, team, and circuit *names* reference real, public Formula 1 entities purely to give the data realistic structure; ALL performance values — lap times, results, standings, weather, telemetry, penalties — are randomly generated and do NOT represent actual historical outcomes. Do not use this data as a source of real F1 history or statistics.

This file is intentionally about the **raw, unprocessed** files only (no ETL, no cleaning, no star schema, no KPIs — that stage is left to you in Python/MySQL/Power BI).

## `openf1/sessions.json`
- **Source represented:** OpenF1 API (simulated)
- **Format:** JSON
- **Row count:** 350
- **Description:** Practice/Qualifying/Sprint/Race session metadata for every event, 2023-2025.
- **Columns:** session_key, meeting_key, session_name, session_type, race_id, circuit_id, circuit_short_name, country_name, date_start, date_end, gmt_offset, year, source
- **Primary identifier:** session_key
- **Important relationships:** meeting_key -> groups sessions of one race weekend; race_id -> formula1/race_events.csv, formula1/race_calendar.csv
- **Known raw-data issues:** Mixed GMT offsets; some session date fields close together (multi-day events) which need timezone handling.

## `openf1/drivers.json`
- **Source represented:** OpenF1 API (simulated)
- **Format:** JSON
- **Row count:** 1424
- **Description:** Driver entry list per Race session (car number, team, headshot).
- **Columns:** session_key, meeting_key, driver_number, broadcast_name, full_name, name_acronym, team_name, team_colour, country_code, headshot_url, source
- **Primary identifier:** session_key + driver_number
- **Important relationships:** driver_number -> formula1/drivers_master.csv; session_key -> openf1/sessions.json
- **Known raw-data issues:** ~15% missing headshot_url; full_name is upper-cased (differs from other sources) and needs standardization.

## `openf1/laps.json`
- **Source represented:** OpenF1 API (simulated)
- **Format:** JSON
- **Row count:** 80414
- **Description:** Lap-by-lap timing data for every driver in every Race session (sector times, compound, pit flags). LARGEST dataset in the project.
- **Columns:** session_key, session_name, meeting_key, race_id, driver_number, driver_code, lap_number, lap_duration, sector_1_time, sector_2_time, sector_3_time, speed_trap, date_start, is_pit_in_lap, is_pit_out_lap, compound, tyre_age, position, source
- **Primary identifier:** none guaranteed unique - (session_key, driver_number, lap_number) usually unique but ~0.7% intentional duplicate rows injected
- **Important relationships:** session_key -> openf1/sessions.json; race_id -> formula1/race_events.csv; driver_number -> formula1/drivers_master.csv
- **Known raw-data issues:** Missing sector_1/2/3_time (~2%) and lap_duration on some in-laps; driver_code/compound inconsistently cased in some rows; duplicate rows present (~0.7%); position is an ETL-approximation from cumulative time, not an official timing feed value.

## `openf1/pit_stops.json`
- **Source represented:** OpenF1 API (simulated)
- **Format:** JSON
- **Row count:** 2215
- **Description:** Pit stop events derived from pit-in laps.
- **Columns:** session_key, race_id, driver_number, driver_code, lap_number, pit_duration, pit_entry_time, pit_exit_time, date, compound_before, compound_after, source
- **Primary identifier:** none guaranteed unique - duplicate-looking rows intentionally present (~2%)
- **Important relationships:** session_key -> openf1/sessions.json; race_id + driver_number -> openf1/laps.json
- **Known raw-data issues:** ~5% missing pit_duration; date field mixes YYYY-MM-DD and DD-MM-YYYY formats; some duplicate records.

## `openf1/weather.json`
- **Source represented:** OpenF1 API (simulated)
- **Format:** JSON
- **Row count:** 3000
- **Description:** Track-side weather samples (~5 min interval) during each session.
- **Columns:** session_key, race_id, date, air_temperature, track_temperature, humidity, pressure, wind_speed, wind_direction, rainfall, source
- **Primary identifier:** none - (session_key, date) usually unique
- **Important relationships:** session_key -> openf1/sessions.json; race_id -> formula1/race_events.csv
- **Known raw-data issues:** ~4% missing humidity; ~5% missing rainfall.

## `openf1/positions.json`
- **Source represented:** OpenF1 API (simulated)
- **Format:** JSON
- **Row count:** 15598
- **Description:** Sampled race-position observations (every 5th lap) per driver.
- **Columns:** session_key, race_id, driver_number, driver_code, date, position, source
- **Primary identifier:** none
- **Important relationships:** session_key -> openf1/sessions.json; driver_number -> formula1/drivers_master.csv
- **Known raw-data issues:** Sparse (not every lap) - by design, for later position-change analysis; some null positions from DNF/incomplete laps.

## `fastf1/race_results.csv`
- **Source represented:** FastF1 library (simulated)
- **Format:** CSV
- **Row count:** 1424
- **Description:** Final classification for every driver in every race, 2023-2025.
- **Columns:** season, round, race_name, driver, driver_number, constructor, grid_position, finish_position, status, points, fastest_lap, fastest_lap_time, fastest_lap_speed, laps_completed, race_time, source
- **Primary identifier:** none - (season, round, driver_number) usually unique
- **Important relationships:** season+round -> formula1/race_calendar.csv; driver_number -> formula1/drivers_master.csv
- **Known raw-data issues:** driver name format mixes 'First Last' and 'Last, First'; ~2% missing grid_position; DNF rows have null finish_position/race_time by design.

## `fastf1/stints.csv`
- **Source represented:** FastF1 library (simulated)
- **Format:** CSV
- **Row count:** 3984
- **Description:** Tyre stint records (compound, start/end lap) per driver per race - raw input for tyre-degradation analysis.
- **Columns:** season, race, driver, constructor, stint_number, compound, start_lap, end_lap, stint_length, fresh_tyre, tyre_life, source
- **Primary identifier:** none - (season, race, driver, stint_number) usually unique
- **Important relationships:** season+race -> formula1/race_calendar.csv; driver -> formula1/drivers_master.csv
- **Known raw-data issues:** ~1.5% missing end_lap; no tyre-degradation KPI included (left for downstream ETL).

## `fastf1/qualifying.csv`
- **Source represented:** FastF1 library (simulated)
- **Format:** CSV
- **Row count:** 1424
- **Description:** Q1/Q2/Q3 session times and grid-deciding qualifying position.
- **Columns:** season, race, driver, constructor, q1_time, q2_time, q3_time, qualifying_position, source
- **Primary identifier:** none - (season, race, driver) usually unique
- **Important relationships:** season+race -> formula1/race_calendar.csv; driver -> formula1/drivers_master.csv
- **Known raw-data issues:** q2_time/q3_time are NULL when a driver did not advance out of Q1/Q2 (intentional, not missing data).

## `fastf1/pit_stops.csv`
- **Source represented:** FastF1 library (simulated)
- **Format:** CSV
- **Row count:** 2500
- **Description:** A second, independently-structured pit-stop extract (different schema from openf1/pit_stops.json) to simulate cross-source reconciliation.
- **Columns:** season, race, driver, driver_number, lap, pit_stop_duration_s, source
- **Primary identifier:** none
- **Important relationships:** season+race -> formula1/race_calendar.csv; driver_number -> formula1/drivers_master.csv
- **Known raw-data issues:** ~4% missing pit_stop_duration_s; does not share a common key with openf1 pit stops - must be reconciled on (season, race, driver, lap) during ETL.

## `fastf1/lap_data.csv`
- **Source represented:** FastF1 library (simulated)
- **Format:** CSV
- **Row count:** 27158
- **Description:** A leaner lap-summary extract (every 3rd lap) with FastF1-style track_status flags, distinct from the full openf1/laps.json feed.
- **Columns:** season, race, driver, driver_number, lap_number, lap_time_s, track_status, source
- **Primary identifier:** none
- **Important relationships:** season+race -> formula1/race_calendar.csv; driver_number -> formula1/drivers_master.csv
- **Known raw-data issues:** ~2% missing lap_time_s; track_status is a coded string ('1'=green,'2'=yellow,'4'=safety car,'5'=red) requiring a lookup during ETL.

## `openweather/weather.json`
- **Source represented:** OpenWeatherMap-style API (simulated)
- **Format:** JSON
- **Row count:** 2740
- **Description:** Independent weekend-long weather observations near each circuit (not tied to session_key - a genuinely separate source system).
- **Columns:** timestamp, latitude, longitude, temperature, feels_like, humidity, pressure, wind_speed, wind_direction, clouds, rain, weather_description, timezone, source
- **Primary identifier:** none
- **Important relationships:** latitude/longitude approximate formula1/circuits_master.csv coordinates; loosely joinable to races by date + location, not by ID (realistic integration challenge).
- **Known raw-data issues:** timestamp field uses 3 different string formats (ISO, space-separated, slash-separated); ~4% missing humidity; rain sometimes null vs 0 inconsistently.

## `fia/race_reports.csv`
- **Source represented:** FIA official race documents (simulated)
- **Format:** CSV
- **Row count:** 452
- **Description:** Extracted classification & penalty information as it might appear scraped from FIA PDF stewards' documents.
- **Columns:** document_id, race_name, season, driver, constructor, classification, grid, laps, status, points, penalty, penalty_reason, document_date, source_document
- **Primary identifier:** document_id
- **Important relationships:** race_name+season -> formula1/race_calendar.csv; driver -> formula1/drivers_master.csv
- **Known raw-data issues:** Only a sampled subset of drivers appear per race (mirrors real doc coverage gaps); penalty/penalty_reason frequently NULL; text fields not cleaned/normalized.

## `formula1/drivers_master.csv`
- **Source represented:** Formula1.com / FastF1 / OpenF1 driver listings (simulated, blended)
- **Format:** CSV
- **Row count:** 69
- **Description:** Driver reference data reported inconsistently across three simulated source systems.
- **Columns:** driver_number, driver_id, driver_code, full_name, first_name, last_name, nationality, date_of_birth, team_name, season, source
- **Primary identifier:** none - (driver_id, season, source) usually unique, ~1% exact duplicates injected
- **Important relationships:** driver_id/driver_number referenced by nearly every other dataset
- **Known raw-data issues:** full_name format varies by source ('Max Verstappen' vs 'VERSTAPPEN, Max' vs 'MAX VERSTAPPEN'); date_of_birth format varies (- vs /); ~2-10% missing values in several columns; ~1% exact duplicate rows.

## `formula1/constructors_master.csv`
- **Source represented:** Formula1.com / FastF1 (simulated)
- **Format:** CSV
- **Row count:** 35
- **Description:** Constructor/team reference data including season-over-season rebrands (e.g. AlphaTauri->RB, Alfa Romeo->Kick Sauber).
- **Columns:** constructor_id, constructor_name, team_name, nationality, season, source
- **Primary identifier:** none - (constructor_id, season, source) usually unique
- **Important relationships:** constructor_id referenced by driver lineups embedded in other datasets via team_name
- **Known raw-data issues:** constructor_name casing varies by source; team_name sometimes suffixed with 'F1 Team', sometimes not.

## `formula1/circuits_master.csv`
- **Source represented:** Formula1.com / OpenF1 (simulated)
- **Format:** CSV
- **Row count:** 27
- **Description:** Circuit reference data (location, length, corners, altitude).
- **Columns:** circuit_id, circuit_name, country, city, latitude, longitude, track_length_km, number_of_corners, altitude_m, season, source
- **Primary identifier:** none - (circuit_id, season, source) usually unique
- **Important relationships:** circuit_id -> formula1/race_events.csv, formula1/race_calendar.csv
- **Known raw-data issues:** track_length_km is in KILOMETERS for formula1_official rows but reported in METERS for openf1-sourced rows (unit inconsistency, intentional); ~4% missing altitude_m; ~5% missing city.

## `formula1/race_events.csv`
- **Source represented:** Formula1.com (simulated)
- **Format:** CSV
- **Row count:** 70
- **Description:** One row per race weekend/event, 2023-2025 (70 events).
- **Columns:** race_id, season, round, race_name, grand_prix, circuit_id, circuit_name, country, race_date, session_type, session_date, source
- **Primary identifier:** race_id
- **Important relationships:** race_id -> openf1/sessions.json, fastf1 files (via season+round), fia/race_reports.csv (via race_name+season)
- **Known raw-data issues:** race_date/session_date use 3 different date-string formats; race_name casing inconsistent.

## `formula1/driver_standings.csv`
- **Source represented:** Formula1.com (simulated)
- **Format:** CSV
- **Row count:** 61
- **Description:** End-of-season championship standings per driver, computed from the same synthetic race results used elsewhere (raw extract style, not a warehouse aggregate).
- **Columns:** season, position, driver, points, wins, podiums, source
- **Primary identifier:** none - (season, driver) unique
- **Important relationships:** season+driver -> formula1/drivers_master.csv
- **Known raw-data issues:** Provided as a flat raw extract, not deduplicated/validated against race_results.csv - reconciliation is left to downstream ETL.

## `formula1/constructor_standings.csv`
- **Source represented:** Formula1.com (simulated)
- **Format:** CSV
- **Row count:** 30
- **Description:** End-of-season championship standings per constructor.
- **Columns:** season, position, constructor, points, wins, podiums, source
- **Primary identifier:** none - (season, constructor) unique
- **Important relationships:** season+constructor -> formula1/constructors_master.csv
- **Known raw-data issues:** Same caveats as driver_standings.csv.

## `formula1/race_calendar.csv`
- **Source represented:** Formula1.com (simulated)
- **Format:** CSV
- **Row count:** 70
- **Description:** Official-style race calendar listing, 2023-2025.
- **Columns:** season, round, race_name, circuit, country, date, source
- **Primary identifier:** none - (season, round) unique
- **Important relationships:** season+round -> fastf1 files; circuit -> formula1/circuits_master.csv (by name, not ID - realistic join challenge)
- **Known raw-data issues:** circuit field is a free-text name, not an ID - must be matched to circuits_master.csv by name during ETL (possible fuzzy-match cases).

## `telemetry/telemetry.csv`
- **Source represented:** OpenF1-style high-frequency telemetry (simulated)
- **Format:** CSV
- **Row count:** 119970
- **Description:** ~0.5s-resolution car telemetry (speed/rpm/gear/throttle/brake/DRS/position) for a sampled subset of drivers and laps per race, to keep the raw file at a manageable scale.
- **Columns:** session_key, race_id, driver_number, driver_code, timestamp, speed, rpm, gear, throttle, brake, drs, distance, x, y, z, source
- **Primary identifier:** none - (session_key, driver_number, timestamp) usually unique
- **Important relationships:** session_key -> openf1/sessions.json; race_id -> formula1/race_events.csv; driver_number -> formula1/drivers_master.csv
- **Known raw-data issues:** ~1.5% missing values injected into speed/rpm/throttle/brake to simulate sensor dropout; only a sample of drivers/laps included per race (not the full grid/full race) - documented here so it is not mistaken for a complete telemetry feed.
