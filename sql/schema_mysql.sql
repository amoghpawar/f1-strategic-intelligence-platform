-- =====================================================================
-- F1 Strategic Intelligence Platform — Data Warehouse Schema (MySQL)
-- Star Schema: Dim_Driver, Dim_Constructor, Dim_Circuit, Dim_Race,
--              Dim_Weather, Fact_RacePerformance, Fact_LapTelemetry
-- =====================================================================
-- Run this on a fresh MySQL 8+ database BEFORE loading data:
--   mysql -u <user> -p < schema_mysql.sql
-- Then run etl/load_to_warehouse.py with target="mysql" (see that file's
-- docstring for the connection string / required packages).
-- =====================================================================

CREATE DATABASE IF NOT EXISTS f1_dw
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE f1_dw;

-- ---------------------------------------------------------------------
-- DIMENSION TABLES
-- ---------------------------------------------------------------------

DROP TABLE IF EXISTS fact_lap_telemetry;
DROP TABLE IF EXISTS fact_race_performance;
DROP TABLE IF EXISTS dim_driver;
DROP TABLE IF EXISTS dim_constructor;
DROP TABLE IF EXISTS dim_circuit;
DROP TABLE IF EXISTS dim_race;
DROP TABLE IF EXISTS dim_weather;

CREATE TABLE dim_driver (
    driver_sk       INT PRIMARY KEY AUTO_INCREMENT,
    driver_id       VARCHAR(20)  NOT NULL UNIQUE,
    driver_number   INT,
    driver_name     VARCHAR(100) NOT NULL,
    nationality     VARCHAR(50),
    current_team    VARCHAR(100),
    INDEX idx_driver_name (driver_name)
) ENGINE=InnoDB;

CREATE TABLE dim_constructor (
    constructor_sk    INT PRIMARY KEY AUTO_INCREMENT,
    constructor_id    VARCHAR(20)  NOT NULL UNIQUE,
    constructor_name  VARCHAR(100) NOT NULL,
    nationality       VARCHAR(50),
    INDEX idx_constructor_name (constructor_name)
) ENGINE=InnoDB;

CREATE TABLE dim_circuit (
    circuit_sk         INT PRIMARY KEY AUTO_INCREMENT,
    circuit_id         VARCHAR(20)  NOT NULL UNIQUE,
    circuit_name       VARCHAR(150) NOT NULL,
    country            VARCHAR(80),
    city               VARCHAR(80),
    track_length_km    DECIMAL(6,3),
    number_of_corners  INT,
    altitude_m         DECIMAL(8,2),
    INDEX idx_circuit_name (circuit_name)
) ENGINE=InnoDB;

CREATE TABLE dim_race (
    race_sk       INT PRIMARY KEY AUTO_INCREMENT,
    race_id       VARCHAR(20)  NOT NULL UNIQUE,
    season        SMALLINT     NOT NULL,
    round         SMALLINT     NOT NULL,
    grand_prix    VARCHAR(150) NOT NULL,
    circuit_id    VARCHAR(20),
    race_date     DATETIME,
    INDEX idx_race_season (season),
    FOREIGN KEY (circuit_id) REFERENCES dim_circuit(circuit_id)
) ENGINE=InnoDB;

CREATE TABLE dim_weather (
    weather_sk         INT PRIMARY KEY AUTO_INCREMENT,
    race_id            VARCHAR(20) NOT NULL UNIQUE,
    avg_air_temp       DECIMAL(5,2),
    avg_track_temp     DECIMAL(5,2),
    avg_humidity       DECIMAL(5,2),
    total_rainfall_mm  DECIMAL(6,2),
    condition_flag     VARCHAR(10),
    FOREIGN KEY (race_id) REFERENCES dim_race(race_id)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- FACT TABLES
-- ---------------------------------------------------------------------

-- Grain: one row per driver per race
CREATE TABLE fact_race_performance (
    fact_id                     INT PRIMARY KEY AUTO_INCREMENT,
    race_sk                     INT NOT NULL,
    driver_sk                   INT NOT NULL,
    constructor_sk              INT,
    circuit_sk                  INT,
    weather_sk                  INT,
    grid_position               SMALLINT,
    finish_position             SMALLINT,
    position_gained             SMALLINT,
    avg_lap_time_s              DECIMAL(7,3),
    fastest_lap_time_s          DECIMAL(7,3),
    pit_stop_count              SMALLINT,
    avg_pit_stop_duration_s     DECIMAL(6,2),
    dominant_tyre_compound      VARCHAR(20),
    championship_points         DECIMAL(5,1),
    status                      VARCHAR(30),
    laps_completed              SMALLINT,
    FOREIGN KEY (race_sk)        REFERENCES dim_race(race_sk),
    FOREIGN KEY (driver_sk)      REFERENCES dim_driver(driver_sk),
    FOREIGN KEY (constructor_sk) REFERENCES dim_constructor(constructor_sk),
    FOREIGN KEY (circuit_sk)     REFERENCES dim_circuit(circuit_sk),
    FOREIGN KEY (weather_sk)     REFERENCES dim_weather(weather_sk),
    INDEX idx_fact_race_driver (driver_sk),
    INDEX idx_fact_race_race (race_sk),
    INDEX idx_fact_race_constructor (constructor_sk)
) ENGINE=InnoDB;

-- Grain: one row per driver per lap (lower-grain fact for drill-down /
-- tyre-degradation analysis; Fact_RacePerformance aggregates from this)
CREATE TABLE fact_lap_telemetry (
    lap_fact_id      BIGINT PRIMARY KEY AUTO_INCREMENT,
    race_sk          INT NOT NULL,
    driver_sk        INT NOT NULL,
    lap_number       SMALLINT,
    lap_duration_s   DECIMAL(7,3),
    sector_1_time_s  DECIMAL(6,3),
    sector_2_time_s  DECIMAL(6,3),
    sector_3_time_s  DECIMAL(6,3),
    compound         VARCHAR(20),
    tyre_age         SMALLINT,
    is_pit_in_lap    BOOLEAN,
    is_pit_out_lap   BOOLEAN,
    position         SMALLINT,
    FOREIGN KEY (race_sk)   REFERENCES dim_race(race_sk),
    FOREIGN KEY (driver_sk) REFERENCES dim_driver(driver_sk),
    INDEX idx_fact_lap_driver (driver_sk),
    INDEX idx_fact_lap_race (race_sk),
    INDEX idx_fact_lap_compound (compound)
) ENGINE=InnoDB;
