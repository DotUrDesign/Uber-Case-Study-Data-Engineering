
-- ==========================================
-- 1. DATE DIMENSION
-- Grain: One row per calendar date
-- ==========================================

CREATE OR REPLACE TABLE analytics.dim_date AS

SELECT DISTINCT
    CAST(STRFTIME(calendar_date, '%Y%m%d') AS INTEGER)
        AS date_key,

    calendar_date AS full_date,

    EXTRACT(DAY FROM calendar_date) AS day,
    EXTRACT(MONTH FROM calendar_date) AS month,
    STRFTIME(calendar_date, '%B') AS month_name,
    EXTRACT(QUARTER FROM calendar_date) AS quarter,
    EXTRACT(YEAR FROM calendar_date) AS year,

    STRFTIME(calendar_date, '%A') AS day_of_week,

    CAST(
        DATE_TRUNC('week', calendar_date)
        AS DATE
    ) AS week_start_date

FROM (
    SELECT
        CAST(trip_start_timestamp AS DATE) AS calendar_date
    FROM staging.trips_validated

    UNION

    SELECT
        CAST(trip_end_timestamp AS DATE) AS calendar_date
    FROM staging.trips_validated
);


-- ==========================================
-- 2. COMMUNITY AREA DIMENSION
-- Grain: One row per community area
-- ==========================================

-- CREATE OR REPLACE TABLE analytics.dim_community_area AS

-- SELECT
--    ROW_NUMBER() OVER (
--        ORDER BY community_area_id
--    ) AS community_area_key,
--
--    community_area_id,
--    community_area_name
--
-- FROM source_db.reference.community_areas;


CREATE OR REPLACE TABLE analytics.dim_community_area AS

WITH all_area_ids AS (

    SELECT pickup_community_area AS community_area_id
    FROM staging.trips_validated
    WHERE pickup_community_area IS NOT NULL

    UNION

    SELECT dropoff_community_area AS community_area_id
    FROM staging.trips_validated
    WHERE dropoff_community_area IS NOT NULL

)

SELECT
    ROW_NUMBER() OVER (
        ORDER BY a.community_area_id
    ) AS community_area_key,

    a.community_area_id,
    r.community_area_name

FROM all_area_ids a

LEFT JOIN source_db.reference.community_areas r
    ON a.community_area_id = r.community_area_id;


-- ==========================================
-- 3. TRIP FACT TABLE
-- Grain: One row per valid unique trip
-- ==========================================

CREATE OR REPLACE TABLE analytics.fact_trips AS

SELECT
    t.trip_id,

    CAST(STRFTIME(t.trip_start_timestamp, '%Y%m%d') AS INTEGER)
        AS pickup_date_key,

    CAST(STRFTIME(t.trip_end_timestamp, '%Y%m%d') AS INTEGER)
        AS dropoff_date_key,

    pickup.community_area_key AS pickup_community_area_key,

    dropoff.community_area_key AS dropoff_community_area_key,

    t.trip_start_timestamp,
    t.trip_end_timestamp,
    t.trip_seconds,
    t.trip_miles,

    t.percent_time_chicago,
    t.percent_distance_chicago,

    t.fare,
    t.tip,
    t.additional_charges,
    t.trip_total,

    t.shared_trip_authorized,
    t.shared_trip_match,
    t.trips_pooled,

    t.source_dataset

FROM staging.trips_validated t

LEFT JOIN analytics.dim_community_area pickup
    ON t.pickup_community_area = pickup.community_area_id

LEFT JOIN analytics.dim_community_area dropoff
    ON t.dropoff_community_area = dropoff.community_area_id;
