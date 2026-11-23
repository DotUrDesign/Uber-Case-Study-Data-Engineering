
CREATE OR REPLACE TABLE analytics.fact_weekly_mobility_metrics AS

SELECT
    d.week_start_date AS week_start_date,

    t.pickup_community_area_key,

    COUNT(DISTINCT t.trip_id) AS trip_volume,

    AVG(t.trip_total) AS average_trip_price,

    COUNT(*) FILTER (
        WHERE t.shared_trip_match = TRUE
    ) AS matched_trip_count,

    ROUND(
        100.0 *
        COUNT(*) FILTER (
            WHERE t.shared_trip_match = TRUE
        ) / COUNT(*),
        2
    ) AS shared_trip_rate

FROM analytics.fact_trips t

JOIN analytics.dim_date d
    ON t.pickup_date_key = d.date_key

WHERE t.pickup_community_area_key IS NOT NULL

GROUP BY
    d.week_start_date,
    t.pickup_community_area_key

ORDER BY
    d.week_start_date,
    t.pickup_community_area_key;
