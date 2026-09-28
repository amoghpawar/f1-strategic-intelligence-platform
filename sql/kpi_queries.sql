-- =====================================================================
-- F1 Strategic Intelligence Platform — KPI Queries
-- Written against the star schema in schema_mysql.sql
-- (Also runs as-is against the SQLite demo warehouse data_warehouse/f1_dw.sqlite,
--  except STDDEV -> use STDDEV_POP/SAMP naming differences noted below.)
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1. DRIVER CONSISTENCY INDEX
-- Lower std-dev of avg lap time across races = more consistent driver.
-- ---------------------------------------------------------------------
SELECT
    d.driver_name,
    COUNT(*)                         AS races_completed,
    ROUND(AVG(f.avg_lap_time_s), 3)  AS mean_avg_lap_time_s,
    ROUND(STDDEV(f.avg_lap_time_s), 3) AS consistency_stddev_s   -- lower = more consistent
FROM fact_race_performance f
JOIN dim_driver d ON d.driver_sk = f.driver_sk
WHERE f.avg_lap_time_s IS NOT NULL
GROUP BY d.driver_name
ORDER BY consistency_stddev_s ASC;


-- ---------------------------------------------------------------------
-- 2. CONSTRUCTOR PERFORMANCE SCORE
-- Combines total points, wins, and podiums into one comparable score.
-- ---------------------------------------------------------------------
SELECT
    c.constructor_name,
    SUM(f.championship_points)                              AS total_points,
    SUM(CASE WHEN f.finish_position = 1 THEN 1 ELSE 0 END)   AS wins,
    SUM(CASE WHEN f.finish_position <= 3 THEN 1 ELSE 0 END)  AS podiums,
    ROUND(SUM(f.championship_points)
          + 5 * SUM(CASE WHEN f.finish_position = 1 THEN 1 ELSE 0 END)
          + 2 * SUM(CASE WHEN f.finish_position <= 3 THEN 1 ELSE 0 END), 1) AS performance_score
FROM fact_race_performance f
JOIN dim_constructor c ON c.constructor_sk = f.constructor_sk
GROUP BY c.constructor_name
ORDER BY performance_score DESC;


-- ---------------------------------------------------------------------
-- 3. AVERAGE PIT STOP DURATION (by constructor and by circuit)
-- ---------------------------------------------------------------------
SELECT
    c.constructor_name,
    ci.circuit_name,
    ROUND(AVG(f.avg_pit_stop_duration_s), 2) AS avg_pit_stop_duration_s,
    SUM(f.pit_stop_count)                    AS total_pit_stops
FROM fact_race_performance f
JOIN dim_constructor c ON c.constructor_sk = f.constructor_sk
JOIN dim_circuit ci     ON ci.circuit_sk    = f.circuit_sk
WHERE f.avg_pit_stop_duration_s IS NOT NULL
GROUP BY c.constructor_name, ci.circuit_name
ORDER BY avg_pit_stop_duration_s ASC;


-- ---------------------------------------------------------------------
-- 4. TYRE DEGRADATION RATE
-- Uses the lower-grain Fact_LapTelemetry: lap time increase per lap of
-- tyre age within a stint (a simple linear slope per driver/compound).
-- ---------------------------------------------------------------------
SELECT
    d.driver_name,
    l.compound,
    COUNT(*)                                              AS laps_sampled,
    ROUND(AVG(l.lap_duration_s), 3)                       AS avg_lap_time_s,
    ROUND(
        (SUM(l.tyre_age * l.lap_duration_s) - SUM(l.tyre_age) * SUM(l.lap_duration_s) / COUNT(*))
        / NULLIF((SUM(l.tyre_age * l.tyre_age) - SUM(l.tyre_age) * SUM(l.tyre_age) / COUNT(*)), 0)
    , 4) AS degradation_s_per_lap_of_tyre_age             -- simple OLS slope, sector/segment level analysis can refine this
FROM fact_lap_telemetry l
JOIN dim_driver d ON d.driver_sk = l.driver_sk
WHERE l.lap_duration_s IS NOT NULL AND l.is_pit_in_lap = FALSE AND l.is_pit_out_lap = FALSE
GROUP BY d.driver_name, l.compound
HAVING laps_sampled >= 5
ORDER BY degradation_s_per_lap_of_tyre_age DESC;


-- ---------------------------------------------------------------------
-- 5. POSITION GAIN/LOSS (qualifying -> race finish)
-- ---------------------------------------------------------------------
SELECT
    d.driver_name,
    r.season,
    r.grand_prix,
    f.grid_position,
    f.finish_position,
    f.position_gained
FROM fact_race_performance f
JOIN dim_driver d ON d.driver_sk = f.driver_sk
JOIN dim_race r    ON r.race_sk  = f.race_sk
WHERE f.position_gained IS NOT NULL
ORDER BY f.position_gained DESC
LIMIT 20;  -- top 20 biggest position gains across all three seasons


-- ---------------------------------------------------------------------
-- 6. RACE STRATEGY SUCCESS RATE (proxy: finish position vs grid, by pit count)
-- More pit stops than the field average but still gaining places suggests
-- an effective aggressive strategy; the reverse suggests a poor one.
-- ---------------------------------------------------------------------
SELECT
    f.pit_stop_count,
    COUNT(*)                                   AS driver_race_entries,
    ROUND(AVG(f.position_gained), 2)           AS avg_position_gained,
    ROUND(100.0 * SUM(CASE WHEN f.position_gained > 0 THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_gained_positions
FROM fact_race_performance f
WHERE f.status = 'Finished'
GROUP BY f.pit_stop_count
ORDER BY f.pit_stop_count;


-- ---------------------------------------------------------------------
-- 7. WEATHER IMPACT SCORE
-- Correlates wet/dry conditions with average lap time across the field.
-- ---------------------------------------------------------------------
SELECT
    w.condition_flag,
    COUNT(DISTINCT f.race_sk)                AS races,
    ROUND(AVG(f.avg_lap_time_s), 3)          AS avg_lap_time_s,
    ROUND(AVG(w.avg_track_temp), 1)          AS avg_track_temp_c,
    ROUND(AVG(w.total_rainfall_mm), 2)       AS avg_rainfall_mm
FROM fact_race_performance f
JOIN dim_weather w ON w.weather_sk = f.weather_sk
WHERE f.avg_lap_time_s IS NOT NULL
GROUP BY w.condition_flag;


-- ---------------------------------------------------------------------
-- 8. RELIABILITY INDEX (finishes vs mechanical/other DNFs, by constructor)
-- ---------------------------------------------------------------------
SELECT
    c.constructor_name,
    COUNT(*)                                                      AS total_entries,
    SUM(CASE WHEN f.status = 'Finished' THEN 1 ELSE 0 END)        AS finishes,
    ROUND(100.0 * SUM(CASE WHEN f.status = 'Finished' THEN 1 ELSE 0 END) / COUNT(*), 1) AS reliability_index_pct
FROM fact_race_performance f
JOIN dim_constructor c ON c.constructor_sk = f.constructor_sk
GROUP BY c.constructor_name
ORDER BY reliability_index_pct DESC;


-- ---------------------------------------------------------------------
-- 9. AVERAGE LAP TIME comparison (driver vs constructor vs circuit)
-- ---------------------------------------------------------------------
SELECT
    ci.circuit_name,
    d.driver_name,
    c.constructor_name,
    ROUND(AVG(f.avg_lap_time_s), 3) AS avg_lap_time_s
FROM fact_race_performance f
JOIN dim_driver d       ON d.driver_sk       = f.driver_sk
JOIN dim_constructor c  ON c.constructor_sk  = f.constructor_sk
JOIN dim_circuit ci     ON ci.circuit_sk     = f.circuit_sk
WHERE f.avg_lap_time_s IS NOT NULL
GROUP BY ci.circuit_name, d.driver_name, c.constructor_name
ORDER BY ci.circuit_name, avg_lap_time_s ASC;


-- ---------------------------------------------------------------------
-- 10. PODIUM CONVERSION RATE (podiums / total race starts, per driver)
-- ---------------------------------------------------------------------
SELECT
    d.driver_name,
    COUNT(*)                                                     AS race_starts,
    SUM(CASE WHEN f.finish_position <= 3 THEN 1 ELSE 0 END)      AS podiums,
    ROUND(100.0 * SUM(CASE WHEN f.finish_position <= 3 THEN 1 ELSE 0 END) / COUNT(*), 1) AS podium_conversion_pct
FROM fact_race_performance f
JOIN dim_driver d ON d.driver_sk = f.driver_sk
GROUP BY d.driver_name
ORDER BY podium_conversion_pct DESC;
