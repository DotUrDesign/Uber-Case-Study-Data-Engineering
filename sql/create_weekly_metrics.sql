
CREATE OR REPLACE TABLE analytics.fact_weekly_mobility_metrics AS

SELECT
    d.week_start_date,

    t.pickup_community_area_key,

    -- Trip volume
    COUNT(DISTINCT t.trip_id) AS trip_volume,

    -- Price components
    SUM(t.trip_total) AS total_trip_price,

    COUNT(t.trip_total) AS price_observation_count,

    ROUND(
        SUM(t.trip_total) / NULLIF(COUNT(t.trip_total), 0),
        2
    ) AS average_trip_price,

    -- Shared trip components
    COUNT(*) FILTER (
        WHERE t.shared_trip_match = TRUE
    ) AS matched_trip_count,

    COUNT(*) FILTER (
        WHERE t.shared_trip_match IS NOT NULL
    ) AS eligible_trip_count,

    ROUND(
        100.0 *
        COUNT(*) FILTER (
            WHERE t.shared_trip_match = TRUE
        ) /
        NULLIF(
            COUNT(*) FILTER (
                WHERE t.shared_trip_match IS NOT NULL
            ),
            0
        ),
        2
    ) AS shared_trip_rate

FROM analytics.fact_trips t

JOIN analytics.dim_date d
    ON t.pickup_date_key = d.date_key

-- Area-level metrics require a valid pickup area.
WHERE t.pickup_community_area_key IS NOT NULL

GROUP BY
    d.week_start_date,
    t.pickup_community_area_key

ORDER BY
    d.week_start_date,
    t.pickup_community_area_key;
