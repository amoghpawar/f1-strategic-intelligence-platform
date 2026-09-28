# Formula One Strategic Intelligence Platform

A Business Intelligence solution for Formula One race strategy, performance analytics, and operational decision support.

## Project Overview

Race data in Formula One comes from several places: timing feeds, official race documents, weather services, and reference listings. Each source uses its own identifiers, date formats, name spellings, and units. Driver names may appear as `Max Verstappen`, `VERSTAPPEN, Max`, or `MAX VERSTAPPEN` depending on the source. Circuit lengths may be recorded in kilometres by one source and metres by another, while constructor names can change across seasons after rebrands.

Answering a basic business question such as **"Which team scores most reliably at wet races?"** therefore requires these datasets to be reconciled and standardized first.

This project builds a **Business Intelligence pipeline** to perform that reconciliation. A Python ETL process extracts raw files from five simulated source systems, cleans and standardizes the data, and loads it into a **star-schema data warehouse**. SQL queries define the analytical KPIs, while a **Power BI report** presents the results across four pages:

- **Championship Analysis**
- **Driver Performance**
- **Constructor Performance**
- **Race & Circuit Analysis**

The data covers 70 race weekends across the 2023 to 2025 seasons. All values are synthetic (see [Data Disclaimer](#️-data-disclaimer)).

## 🎯 Objectives

- Integrate data from multiple Formula One-related source systems
- Clean and standardize heterogeneous data: names, timestamps, units, missing values, duplicates
- Build a dimensional data warehouse with two fact tables and five dimension tables
- Define KPIs for drivers, constructors, pit stops, tyres, weather, and reliability
- Present the results in Power BI for driver, constructor, race, and circuit analysis

## 🏗️ System Architecture

```text
┌──────────────────────────────────────────────────────────────┐
│  DATA SOURCES (simulated)                                    │
│  OpenF1 · FastF1 · OpenWeather · FIA · Formula1.com          │
└───────────────────────────────┬──────────────────────────────┘
                                │  raw_data/  (CSV + JSON)
                                ▼
┌──────────────────────────────────────────────────────────────┐
│  PYTHON ETL  (etl/run_pipeline.py)                           │
│  extract.py → clean.py → transform_star_schema.py            │
│                        → load_to_warehouse.py                │
└───────────────────────────────┬──────────────────────────────┘
                                ▼
┌──────────────────────────────────────────────────────────────┐
│  DATA WAREHOUSE (star schema)                                │
│  SQLite: data_warehouse/f1_dw.sqlite                         │
│  CSV export: data_warehouse/csv/                             │
│  MySQL: optional target (sql/schema_mysql.sql)               │
└───────────────────────────────┬──────────────────────────────┘
                                ▼
┌──────────────────────────────────────────────────────────────┐
│  SQL KPI QUERIES  (sql/kpi_queries.sql)                      │
└───────────────────────────────┬──────────────────────────────┘
                                ▼
┌──────────────────────────────────────────────────────────────┐
│  POWER BI  (powerbi/dashboard.pbix)                          │
│  4 report pages                                              │
└───────────────────────────────┬──────────────────────────────┘
                                ▼
                    Business insights / decision support
```

## 📥 Data Sources

The five source systems are simulated. `raw_data/METADATA_README.md` documents each file, its columns, and its known data-quality issues.

| Source | Files | Contribution |
|---|---|---|
| OpenF1 | `sessions.json`, `drivers.json`, `laps.json`, `pit_stops.json`, `weather.json`, `positions.json`, plus `telemetry/telemetry.csv` (OpenF1-style) | Session metadata, driver entries, lap and sector times, tyre compound and age, pit stops, track weather, sampled race positions, car telemetry |
| FastF1 | `race_results.csv`, `stints.csv`, `qualifying.csv`, `pit_stops.csv`, `lap_data.csv` | Race classification, tyre stints, qualifying times, a second pit-stop extract, lap summaries with track-status codes |
| OpenWeather | `weather.json` | Independent weather observations near each circuit, not keyed by session |
| FIA | `race_reports.csv` | Classification and penalty data styled after steward documents |
| Formula1.com | `drivers_master.csv`, `constructors_master.csv`, `circuits_master.csv`, `race_events.csv`, `race_calendar.csv`, `driver_standings.csv`, `constructor_standings.csv` | Driver, constructor and circuit reference data, race events, calendar, season standings |

**Not every extracted file reaches the warehouse.** `extract.py` reads all of the files above. The warehouse builds from a subset: drivers, constructors, circuits and race events from Formula1.com, OpenF1 sessions, laps, pit stops and weather, and FastF1 race results and stints. Other files (FIA reports, OpenWeather, FastF1 pit stops, qualifying, standings, calendar, positions, telemetry) are extracted, and some are cleaned, but they are not used in the warehouse tables.

**Repository note:** `openf1/laps.json`, `openf1/weather.json`, `openf1/positions.json`, `openweather/weather.json` and `telemetry/telemetry.csv` are large files documented in the metadata but not included in this repository. `extract.py` expects them at those paths, so the ETL cannot run end to end without them. The committed warehouse files (`f1_dw.sqlite` and `data_warehouse/csv/`) let you use the SQL and Power BI steps without re-running the pipeline.

## 🔄 ETL Pipeline

`etl/run_pipeline.py` runs four stages in order: extract, clean, transform, load.

### Extract

`etl/extract.py` reads every raw file into a pandas DataFrame (`pd.read_csv` / `pd.read_json`) and returns a dictionary of tables. It applies no cleaning.

### Transform

Cleaning is in `etl/clean.py`. Star-schema construction is in `etl/transform_star_schema.py`.

**Cleaning**

| Operation | What the code does |
|---|---|
| Duplicate handling | Drops exact duplicates on every dataset that is cleaned. For laps, duplicates are detected on `session_key`, `driver_number`, `lap_number`, `lap_duration`. |
| Missing values | Median imputation for `altitude_m`, pit-stop durations, weather fields (`humidity`, `rainfall`, `rain`, `wind_speed`), `end_lap`, and `grid_position`. Linear interpolation of lap and sector times within each driver's session lap sequence. Defaults for other fields: `points` to 0, missing `city` to "Unknown", missing FIA `penalty` and `penalty_reason` to "None". |
| Name standardization | Converts `LAST, First` and upper-case forms to `First Last`. Title-cases nationality, team, constructor, circuit and race names. |
| Case standardization | Upper-cases `driver_code` and tyre `compound`. |
| Timestamp processing | Parses mixed date and time string formats with `python-dateutil` and rewrites them as ISO 8601 (`%Y-%m-%dT%H:%M:%S`). No timezone conversion is applied. Date-of-birth separators are normalized from `/` to `-`. |
| Unit conversion | Track length is converted from metres to kilometres for OpenF1-sourced circuit rows. |
| Key checks | Drops driver rows with no `driver_id`. |

**Star-schema build**

- Generates integer surrogate keys for every dimension.
- Keeps one canonical row per driver, constructor and circuit (latest season).
- Back-fills missing driver numbers from other seasons and adds fallback driver rows for numbers found in race results but absent from the driver master.
- Maps constructor aliases (AlphaTauri and RB to Racing Bulls, Alfa Romeo to Kick Sauber) before joining.
- Assigns `constructor_sk = -1` when a constructor name cannot be matched, so the row is flagged instead of dropped.
- Calculates the fields listed below.

| Calculated field | Definition |
|---|---|
| `position_gained` | `grid_position - finish_position` |
| `avg_lap_time_s`, `fastest_lap_time_s` | Mean and minimum lap duration per driver per race |
| `pit_stop_count`, `avg_pit_stop_duration_s` | Count and mean of OpenF1 pit stops per driver per race |
| `dominant_tyre_compound` | Compound with the most stint laps in that race |
| Weather aggregates | Race-session means (air temp, track temp, humidity) and total rainfall |
| `condition_flag` | "Wet" if total rainfall exceeds 0.5 mm, otherwise "Dry" |

### Load

`etl/load_to_warehouse.py` writes every table to `data_warehouse/csv/` and, by default, rebuilds the SQLite database `data_warehouse/f1_dw.sqlite` with indexes on the main fact-table keys. With `--mysql`, it writes the CSVs and loads the tables into a MySQL server using SQLAlchemy and `mysql-connector-python`.

## 🗄️ Data Warehouse

The warehouse is a star schema. Fact tables reference dimensions by surrogate key. Row counts below come from the committed `f1_dw.sqlite`.

### Fact Tables

| Table | Grain | Rows | Purpose |
|---|---|---|---|
| `fact_race_performance` | One row per driver per race | 1,424 | Grid and finish position, positions gained, average and fastest lap time, pit-stop count and duration, dominant tyre compound, championship points, status, laps completed. Keys: race, driver, constructor, circuit, weather. |
| `fact_lap_telemetry` | One row per driver per lap | 79,856 | Lap duration, sector times, tyre compound and age, pit-in and pit-out flags, running position. Supports lap-level tyre analysis. Keys: race, driver. |

### Dimension Tables

| Table | Rows | Purpose |
|---|---|---|
| `dim_driver` | 27 | Driver identity: natural key, car number, name, nationality, team |
| `dim_constructor` | 10 | Constructor name (latest season, after rebrands) and nationality |
| `dim_circuit` | 24 | Circuit name, country, city, track length (km), number of corners, altitude (m) |
| `dim_race` | 70 | Season, round, grand prix name, circuit, race date (2023 to 2025) |
| `dim_weather` | 70 | One row per race: average air and track temperature, average humidity, total rainfall, wet/dry flag |

### SQLite and MySQL

| Engine | Role |
|---|---|
| SQLite | Default target. `data_warehouse/f1_dw.sqlite` is built by the pipeline and committed, so the warehouse can be queried without installing a database server. |
| MySQL | Optional target. `sql/schema_mysql.sql` creates the `f1_dw` database with keys, foreign keys and indexes; `--mysql` loads data into it. |

> **Known schema difference:** the SQLite/CSV `dim_driver` has the columns `full_name`, `full_name_clean` and `team_name` (among others), while `schema_mysql.sql` and `docs/data_dictionary.md` describe `driver_name` and `current_team`. Align these before loading into MySQL. The MySQL path has not been verified here.

## 📊 KPI Framework

Ten KPIs are defined in `sql/kpi_queries.sql`. Power BI measures are listed separately below.

### Driver Performance

| KPI | Definition |
|---|---|
| Driver Consistency Index | Standard deviation of a driver's average lap time across races (lower means more consistent) |
| Position Gain/Loss | Grid position, finish position and positions gained; top 20 gains |
| Podium Conversion Rate | Podium finishes divided by race starts, per driver |
| Average Lap Time Comparison | Average lap time by circuit, driver and constructor |

### Constructor Performance

| KPI | Definition |
|---|---|
| Constructor Performance Score | Total points + 5 × wins + 2 × podiums |

### Race Operations and Strategy

| KPI | Definition |
|---|---|
| Average Pit Stop Duration | Mean pit-stop duration and total stops by constructor and circuit |
| Tyre Degradation Rate | Least-squares slope of lap time against tyre age, by driver and compound (at least 5 laps) |
| Race Strategy Success Rate | Average positions gained and share of drivers gaining places, grouped by pit-stop count (a proxy, as noted in the SQL) |

### Reliability and Environment

| KPI | Definition |
|---|---|
| Reliability Index | Percentage of entries with status "Finished", by constructor |
| Weather Impact Score | Average lap time, track temperature and rainfall for wet versus dry races |

### Power BI measures

Total Points, Wins, Podiums, Average Finish Position, Average Grid Position, Constructor Wins, Constructor Podiums, Average Points per Race, Race Wins, Race Podiums.

## 📈 Power BI Dashboards

`powerbi/dashboard.pbix` contains four report pages.

### Dashboard 1: Championship

- **Purpose:** season-level overview of driver and constructor standings.
- **KPIs:** Total Points, Wins, Podiums.
- **Visuals:** driver table (name, points, wins, podiums), clustered bar chart of points by constructor, "Select Season" slicer.
- **Questions:** Who leads the standings in a given season? How do constructors compare on points?

### Dashboard 2: Driver Performance

- **Purpose:** race-by-race analysis of one or more drivers.
- **KPIs:** Total Points, Wins, Podiums, Average Finish Position.
- **Visuals:** four KPI cards; line charts "Points Scored by Race" and "Grid Position vs Finish Position"; column chart "Positions Gained / Lost"; donut chart "Dominant Tyre Compound Usage"; race table (grid, finish, positions gained, points); driver name slicer.
- **Questions:** How does a driver's result compare to their starting position? Which races gained or lost places? Which tyre compounds dominate their races?

### Dashboard 3: Constructor Performance

- **Purpose:** compare constructors and inspect one team's results.
- **KPIs:** Total Points, Constructor Wins, Constructor Podiums, Average Points per Race.
- **Visuals:** four KPI cards; line chart "Constructor Points by Race"; bar chart "Constructor Championship Points"; column chart "Constructor Wins & Podiums"; table "Race-by-Race Constructor Performance"; "Select Constructor" slicer.
- **Questions:** Which constructors score the most points, wins and podiums? How does a team's scoring vary across races?

### Dashboard 4: Race & Circuit Analysis

- **Purpose:** compare results across the race calendar and across circuits.
- **KPIs:** summary cards for race round, finish position, grid position and lap time.
- **Visuals:** line chart "Points Scored Across Race Calendar"; bar charts "Average Finish Position by Circuit" and "Average Grid Position by Circuit"; race and circuit table (points, grid, finish); "Select Race" slicer.
- **Questions:** How do points distribute over a season? How do grid and finish positions differ by circuit?

## 💡 Business Insights / Decision Support

The outputs are descriptive and historical. They help an analyst compare past performance and locate where results differ. They do not forecast outcomes.

- **Strategy review:** compare pit-stop counts with positions gained, and inspect tyre degradation by driver and compound.
- **Driver evaluation:** use consistency, podium conversion and grid-to-finish movement to compare drivers.
- **Constructor comparison:** combine points, wins, podiums and the reliability index.
- **Pit-stop analysis:** compare average pit-stop duration across constructors and circuits.
- **Conditions:** compare wet and dry races on lap time and track temperature.

Because the data is synthetic, these outputs demonstrate the method and should not be read as findings about real teams or drivers.

## 🛠️ Technology Stack

| Technology | Purpose |
|---|---|
| Python | ETL scripting |
| pandas | Data extraction, cleaning, transformation |
| NumPy | Numeric operations (wet/dry flag) |
| python-dateutil | Parsing mixed timestamp formats |
| SQLite | Default demo data warehouse |
| MySQL | Optional warehouse target (`schema_mysql.sql`) |
| SQLAlchemy | MySQL connection and table loading |
| mysql-connector-python | MySQL driver |
| SQL | Warehouse schema and KPI queries |
| Power BI | Dashboards (`dashboard.pbix`) |
| Git & GitHub | Version control |

## 📁 Repository Structure

```text
f1-strategic-intelligence-platform/
├── data_warehouse/
│   ├── csv/                       # Star-schema tables as CSV (5 dim, 2 fact)
│   └── f1_dw.sqlite               # SQLite warehouse
├── docs/
│   └── data_dictionary.md
├── etl/
│   ├── extract.py
│   ├── clean.py
│   ├── transform_star_schema.py
│   ├── load_to_warehouse.py
│   └── run_pipeline.py            # Pipeline entry point
├── powerbi/
│   └── dashboard.pbix
├── raw_data/
│   ├── fastf1/
│   ├── fia/
│   ├── formula1/
│   ├── openf1/                    # sessions, drivers, pit_stops only (see note)
│   └── METADATA_README.md
├── sql/
│   ├── kpi_queries.sql
│   └── schema_mysql.sql
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## 🚀 How to Use

**1. Clone the repository**

```bash
git clone https://github.com/amoghpawar/f1-strategic-intelligence-platform.git
cd f1-strategic-intelligence-platform
```

**2. Install dependencies**

```bash
pip install -r requirements.txt
```

**3. Run the ETL pipeline** (SQLite, the default)

```bash
python etl/run_pipeline.py
```

This requires all raw files listed in `raw_data/METADATA_README.md`, including the five not committed to this repository (see [Data Sources](#-data-sources)). It rewrites `data_warehouse/f1_dw.sqlite` and the CSVs in `data_warehouse/csv/`.

To load into MySQL instead:

```bash
mysql -u <user> -p < sql/schema_mysql.sql
python etl/run_pipeline.py --mysql
```

Optional flags: `--host`, `--user`, `--password`, `--database`.

**4. Access the warehouse**

Use the committed `data_warehouse/f1_dw.sqlite` or rebuild it in step 3.

```bash
sqlite3 data_warehouse/f1_dw.sqlite
```

The CSV exports in `data_warehouse/csv/` can also be opened directly.

**5. Run SQL queries**

`sql/kpi_queries.sql` is written for the MySQL schema. Against the SQLite warehouse, the queries need two adjustments:

- Replace `d.driver_name` with `d.full_name_clean` (SQLite `dim_driver` has no `driver_name` column).
- SQLite has no `STDDEV` function, so the Driver Consistency Index query needs a different calculation.

The constructor score, pit-stop, tyre degradation, strategy, weather and reliability queries run against the SQLite file with only the `driver_name` change where it applies.

**6. Open the Power BI dashboard**

Open `powerbi/dashboard.pbix` in Power BI Desktop. If a data source prompt appears, point it at the warehouse tables in `data_warehouse/`.

## 🔐 Environment Configuration

Environment variables are used only for the optional MySQL load (`--mysql`). The default SQLite run needs none.

`.env.example`:

```text
F1_DW_HOST=localhost
F1_DW_USER=root
F1_DW_PASSWORD=
F1_DW_DATABASE=f1_dw
```

| Variable | Default | Used for |
|---|---|---|
| `F1_DW_HOST` | `localhost` | MySQL server host |
| `F1_DW_USER` | `root` | MySQL user |
| `F1_DW_PASSWORD` | empty | MySQL password |
| `F1_DW_DATABASE` | `f1_dw` | Target database name |

All four are optional in the sense that defaults exist, and each can also be passed as a command-line flag. The scripts read the process environment and do not load a `.env` file, so export the variables in your shell or use the flags. `.env` is listed in `.gitignore`; never commit credentials.

## 📚 Documentation

| File | Contents |
|---|---|
| `docs/data_dictionary.md` | Star-schema columns, types, grains, and documented limitations |
| `raw_data/METADATA_README.md` | Every raw file: source, format, row count, columns, relationships, known data issues |
| `sql/schema_mysql.sql` | MySQL DDL for the warehouse |
| `sql/kpi_queries.sql` | The ten KPI queries, with comments |

## ⚠️ Data Disclaimer

All raw datasets in this project are **synthetically generated** for an academic exercise. Driver, team and circuit names refer to real Formula One entities so that the data has a realistic structure. **All performance values are randomly generated**, including lap times, race results, standings, weather, telemetry and penalties. They do not represent actual historical outcomes.

The data is not live, and it was not collected from OpenF1, FastF1, OpenWeather, the FIA or Formula1.com. Do not use this repository as a source of real Formula One history or statistics, and do not draw conclusions about real drivers or teams from its outputs.

Known limitations recorded in the project documentation:

- `constructor_sk = -1` marks a constructor name that could not be matched (for example after a mid-season rebrand), flagged for review instead of dropped.
- `avg_pit_stop_duration_s` is NULL where no pit-stop record exists for that driver and race. It does not mean zero stops.

## 🔮 Future Scope

The project materials do not include a formal roadmap. Two refinements are noted in the files:

- The tyre degradation KPI is a simple linear slope, and a comment in `kpi_queries.sql` says sector-level or segment-level analysis could refine it.
- Constructor name mismatches flagged with `constructor_sk = -1` are marked for manual review.

## 🎓 Academic Context

| | |
|---|---|
| **Institution** | G H Raisoni College of Engineering and Management, Pune |
| **Project type** | Academic Business Intelligence project |
| **Team** | Amogh Pawar, Raj Chintawar |

The project applies a BI workflow (integration, dimensional modelling, KPI definition and dashboarding) to synthetic Formula One data.

## 👥 Team Contributions

Amogh Pawar and Raj Chintawar developed this project together. Individual contributions are not documented in the repository.

## 📌 Key Takeaway

Data → Analytics → Decision Support: scattered source files are standardized into a star-schema warehouse, defined as SQL KPIs, and presented in Power BI for analyzing race strategy, driver form, and constructor performance.
