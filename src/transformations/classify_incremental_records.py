
import duckdb


def classify_incremental_records():

    con = duckdb.connect("mobility.duckdb")

    try:
        # Compare incoming records against existing trusted records.
        con.execute("""
            CREATE OR REPLACE TABLE staging.incremental_classification AS

            SELECT
                incoming.*,

                CASE
                    WHEN existing.trip_id IS NULL
                        THEN 'NEW'

                    WHEN
                        incoming.trip_start_timestamp
                            IS NOT DISTINCT FROM existing.trip_start_timestamp

                        AND incoming.trip_end_timestamp
                            IS NOT DISTINCT FROM existing.trip_end_timestamp

                        AND incoming.trip_seconds
                            IS NOT DISTINCT FROM existing.trip_seconds

                        AND incoming.trip_miles
                            IS NOT DISTINCT FROM existing.trip_miles

                        AND incoming.percent_time_chicago
                            IS NOT DISTINCT FROM existing.percent_time_chicago

                        AND incoming.percent_distance_chicago
                            IS NOT DISTINCT FROM existing.percent_distance_chicago

                        AND incoming.pickup_community_area
                            IS NOT DISTINCT FROM pickup_dim.community_area_id

                        AND incoming.dropoff_community_area
                            IS NOT DISTINCT FROM dropoff_dim.community_area_id

                        AND incoming.fare
                            IS NOT DISTINCT FROM existing.fare

                        AND incoming.tip
                            IS NOT DISTINCT FROM existing.tip

                        AND incoming.additional_charges
                            IS NOT DISTINCT FROM existing.additional_charges

                        AND incoming.trip_total
                            IS NOT DISTINCT FROM existing.trip_total

                        AND incoming.shared_trip_authorized
                            IS NOT DISTINCT FROM existing.shared_trip_authorized

                        AND incoming.shared_trip_match
                            IS NOT DISTINCT FROM existing.shared_trip_match

                        AND incoming.trips_pooled
                            IS NOT DISTINCT FROM existing.trips_pooled

                    THEN 'IDENTICAL'

                    ELSE 'CONFLICT'

                END AS record_status

            FROM staging.trips_validated_incremental incoming

            LEFT JOIN analytics.fact_trips existing
                ON incoming.trip_id = existing.trip_id
            LEFT JOIN analytics.dim_community_area pickup_dim
                ON existing.pickup_community_area_key = pickup_dim.community_area_key
            LEFT JOIN analytics.dim_community_area dropoff_dim
                ON existing.dropoff_community_area_key = dropoff_dim.community_area_key
        """)

        # Display classification summary.
        result = con.execute("""
            SELECT
                record_status,
                COUNT(*) AS total_records
            FROM staging.incremental_classification
            GROUP BY record_status
            ORDER BY record_status
        """).df()

        print("Incremental record classification completed!")
        print(result.to_string(index=False))

        # Display total classified records.
        total = con.execute("""
            SELECT COUNT(*)
            FROM staging.incremental_classification
        """).fetchone()[0]

        print(f"\nTotal classified records: {total}")

    finally:
        con.close()


if __name__ == "__main__":
    classify_incremental_records()
