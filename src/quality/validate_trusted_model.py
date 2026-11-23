
import duckdb


def validate_trusted_model():

    con = duckdb.connect("mobility.duckdb")

    try:
        result = con.sql("""
            SELECT
                (SELECT COUNT(*)
                 FROM analytics.fact_trips)
                    AS fact_trip_count,

                (SELECT COUNT(DISTINCT trip_id)
                 FROM analytics.fact_trips)
                    AS distinct_trip_count,

                (SELECT COUNT(*)
                 FROM analytics.fact_trips
                 WHERE pickup_community_area_key IS NULL)
                    AS missing_pickup_area_count,

                (SELECT COUNT(*)
                 FROM analytics.fact_trips
                 WHERE dropoff_community_area_key IS NULL)
                    AS missing_dropoff_area_count,

                (SELECT COUNT(*)
                 FROM analytics.fact_weekly_mobility_metrics)
                    AS weekly_metric_rows,

                (SELECT COUNT(*)
                 FROM (
                     SELECT
                         week_start_date,
                         pickup_community_area_key
                     FROM analytics.fact_weekly_mobility_metrics
                     GROUP BY 1, 2
                     HAVING COUNT(*) > 1
                 ))
                    AS duplicate_week_area_grains,

                (SELECT COUNT(*)
                 FROM ops.quarantine_records)
                    AS quarantined_records
        """).df()

        print("Final trusted model validation:")
        print(result.to_string(index=False))

        geography = con.sql("""
            SELECT
                COUNT(*) FILTER (
                    WHERE t.dropoff_community_area IS NULL
                ) AS source_dropoff_nulls,

                COUNT(*) FILTER (
                    WHERE t.dropoff_community_area IS NOT NULL
                    AND d.community_area_key IS NULL
                ) AS unmatched_dropoff_areas,

                COUNT(DISTINCT t.dropoff_community_area)
                    FILTER (
                        WHERE d.community_area_key IS NULL
                        AND t.dropoff_community_area IS NOT NULL
                    ) AS distinct_unmatched_area_ids

            FROM staging.trips_validated t

            LEFT JOIN analytics.dim_community_area d
                ON t.dropoff_community_area = d.community_area_id
        """).df()

        print("\nDropoff geography diagnosis:")
        print(geography.to_string(index=False))

    finally:
        con.close()


if __name__ == "__main__":
    validate_trusted_model()
