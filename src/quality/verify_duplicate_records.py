# finding out - 
# exact duplicate ids => same trip_id with all same column values 
# conflicting duplicate ids => same trip_id but some having different column values 


import duckdb


def verify_duplicate_records():

    con = duckdb.connect("mobility.duckdb")

    try:
        result = con.sql("""
            WITH duplicate_groups AS (
                SELECT
                    trip_id,
                    COUNT(*) AS occurrence_count,
                    COUNT(DISTINCT HASH(
                        trip_start_timestamp,
                        trip_end_timestamp,
                        trip_seconds,
                        trip_miles,
                        percent_time_chicago,
                        percent_distance_chicago,
                        pickup_community_area,
                        dropoff_community_area,
                        fare,
                        tip,
                        additional_charges,
                        trip_total,
                        shared_trip_authorized,
                        shared_trip_match,
                        trips_pooled
                    )) AS distinct_versions

                FROM staging.trips_union
                GROUP BY trip_id
                HAVING COUNT(*) > 1
            )

            SELECT
                COUNT(*) AS duplicate_trip_ids,

                COUNT(*) FILTER (
                    WHERE distinct_versions = 1
                ) AS exact_duplicate_ids,

                COUNT(*) FILTER (
                    WHERE distinct_versions > 1
                ) AS conflicting_duplicate_ids

            FROM duplicate_groups
        """).df()

        print("Duplicate record verification:")
        print(result.to_string(index=False))

    finally:
        con.close()


if __name__ == "__main__":
    verify_duplicate_records()
