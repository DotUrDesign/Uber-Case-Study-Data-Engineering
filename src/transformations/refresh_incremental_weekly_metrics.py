
import duckdb


def refresh_incremental_weekly_metrics():

    con = duckdb.connect("mobility.duckdb")

    try:
        con.execute("BEGIN TRANSACTION")

        # 1. Identify affected week-area combinations
        con.execute("""
            CREATE OR REPLACE TABLE staging.affected_week_areas AS

            SELECT DISTINCT
                d.week_start_date,
                t.pickup_community_area_key

            FROM staging.incremental_new_trips n

            JOIN analytics.fact_trips t
                ON n.trip_id = t.trip_id

            JOIN analytics.dim_date d
                ON t.pickup_date_key = d.date_key

            WHERE t.pickup_community_area_key IS NOT NULL
        """)

        affected_count = con.execute("""
            SELECT COUNT(*)
            FROM staging.affected_week_areas
        """).fetchone()[0]

        if affected_count == 0:
            con.execute("COMMIT")
            print("No new records. Weekly metrics refresh skipped.")
            return

        # 2. Delete only affected metric rows
        con.execute("""
            DELETE FROM analytics.fact_weekly_mobility_metrics m

            WHERE EXISTS (
                SELECT 1
                FROM staging.affected_week_areas a
                WHERE m.week_start_date = a.week_start_date
                  AND m.pickup_community_area_key =
                      a.pickup_community_area_key
            )
        """)

        # 3. Recalculate affected metrics using the complete fact table
        con.execute("""
            INSERT INTO analytics.fact_weekly_mobility_metrics

            SELECT
                d.week_start_date,
                t.pickup_community_area_key,

                COUNT(DISTINCT t.trip_id) AS trip_volume,

                SUM(t.trip_total) AS total_trip_price,

                COUNT(t.trip_total) AS price_observation_count,

                ROUND(
                    SUM(t.trip_total) /
                    NULLIF(COUNT(t.trip_total), 0),
                    2
                ) AS average_trip_price,

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

            JOIN staging.affected_week_areas a
                ON d.week_start_date = a.week_start_date
               AND t.pickup_community_area_key =
                   a.pickup_community_area_key

            WHERE t.pickup_community_area_key IS NOT NULL

            GROUP BY
                d.week_start_date,
                t.pickup_community_area_key
        """)

        con.execute("COMMIT")

        print("Incremental weekly metrics refresh completed!")
        print(f"Affected week-area combinations: {affected_count}")

    except Exception:
        con.execute("ROLLBACK")
        raise

    finally:
        con.close()


if __name__ == "__main__":
    refresh_incremental_weekly_metrics()
