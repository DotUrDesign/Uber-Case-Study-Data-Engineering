
import duckdb


def merge_incremental_trips():

    con = duckdb.connect("mobility.duckdb")

    try:
        con.execute("BEGIN TRANSACTION")

        # 1. Preserve conflicting records for investigation.
        con.execute("""
            CREATE TABLE IF NOT EXISTS ops.incremental_conflicts AS
            SELECT *
            FROM staging.incremental_classification
            WHERE 1 = 0
        """)

        con.execute("""
            INSERT INTO ops.incremental_conflicts
            SELECT *
            FROM staging.incremental_classification
            WHERE record_status = 'CONFLICT'
        """)

        # 2. Capture the records that are eligible for insertion.
        # Resolve dimension keys using the existing dimensions.
        con.execute("""
            CREATE OR REPLACE TABLE staging.incremental_new_trips AS

            SELECT
                incoming.trip_id,
                incoming.pickup_community_area,
                incoming.dropoff_community_area,

                pickup_date.date_key AS pickup_date_key,
                dropoff_date.date_key AS dropoff_date_key,

                pickup_area.community_area_key
                    AS pickup_community_area_key,

                dropoff_area.community_area_key
                    AS dropoff_community_area_key,

                incoming.trip_start_timestamp,
                incoming.trip_end_timestamp,
                incoming.trip_seconds,
                incoming.trip_miles,
                incoming.percent_time_chicago,
                incoming.percent_distance_chicago,
                incoming.fare,
                incoming.tip,
                incoming.additional_charges,
                incoming.trip_total,
                incoming.shared_trip_authorized,
                incoming.shared_trip_match,
                incoming.trips_pooled,
                incoming.source_dataset

            FROM staging.incremental_classification incoming

            LEFT JOIN analytics.dim_date pickup_date
                ON CAST(incoming.trip_start_timestamp AS DATE)
                    = pickup_date.full_date

            LEFT JOIN analytics.dim_date dropoff_date
                ON CAST(incoming.trip_end_timestamp AS DATE)
                    = dropoff_date.full_date

            LEFT JOIN analytics.dim_community_area pickup_area
                ON incoming.pickup_community_area
                    = pickup_area.community_area_id

            LEFT JOIN analytics.dim_community_area dropoff_area
                ON incoming.dropoff_community_area
                    = dropoff_area.community_area_id

            WHERE incoming.record_status = 'NEW'
        """)

        # 3. Validate dimension key resolution before insertion.
        unresolved = con.execute("""
            SELECT COUNT(*)
            FROM staging.incremental_new_trips
            WHERE pickup_date_key IS NULL
               OR dropoff_date_key IS NULL
               OR (
                    pickup_community_area IS NOT NULL
                    AND pickup_community_area_key IS NULL
               )
               OR (
                    dropoff_community_area IS NOT NULL
                    AND dropoff_community_area_key IS NULL
               )
        """).fetchone()[0]

        if unresolved > 0:
            raise ValueError(
                f"{unresolved} new records have unresolved dimension keys."
            )

        # 4. Insert only NEW records.
        con.execute("""
            INSERT INTO analytics.fact_trips (
                trip_id,
                pickup_date_key,
                dropoff_date_key,
                pickup_community_area_key,
                dropoff_community_area_key,
                trip_start_timestamp,
                trip_end_timestamp,
                trip_seconds,
                trip_miles,
                percent_time_chicago,
                percent_distance_chicago,
                fare,
                tip,
                additional_charges,
                trip_total,
                shared_trip_authorized,
                shared_trip_match,
                trips_pooled,
                source_dataset
            )

            SELECT
                n.trip_id,
                n.pickup_date_key,
                n.dropoff_date_key,
                n.pickup_community_area_key,
                n.dropoff_community_area_key,
                n.trip_start_timestamp,
                n.trip_end_timestamp,
                n.trip_seconds,
                n.trip_miles,
                n.percent_time_chicago,
                n.percent_distance_chicago,
                n.fare,
                n.tip,
                n.additional_charges,
                n.trip_total,
                n.shared_trip_authorized,
                n.shared_trip_match,
                n.trips_pooled,
                n.source_dataset

            FROM staging.incremental_new_trips n

            WHERE NOT EXISTS (
                SELECT 1
                FROM analytics.fact_trips f
                WHERE f.trip_id = n.trip_id
            )
        """)

        inserted = con.execute("""
            SELECT COUNT(*)
            FROM staging.incremental_new_trips
        """).fetchone()[0]

        conflicts = con.execute("""
            SELECT COUNT(*)
            FROM staging.incremental_classification
            WHERE record_status = 'CONFLICT'
        """).fetchone()[0]

        identical = con.execute("""
            SELECT COUNT(*)
            FROM staging.incremental_classification
            WHERE record_status = 'IDENTICAL'
        """).fetchone()[0]

        con.execute("COMMIT")

        print("Incremental fact merge completed!")
        print(f"Records inserted: {inserted}")
        print(f"Identical records ignored: {identical}")
        print(f"Conflicting records flagged: {conflicts}")

    except Exception:
        con.execute("ROLLBACK")
        raise

    finally:
        con.close()


if __name__ == "__main__":
    merge_incremental_trips()
