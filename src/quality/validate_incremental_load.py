# checking :
# 1. Total records loaded.
# 2. Distinct trip_id count.
# 3. Duplicate trip_id count.
# 4. Records with invalid timestamp chronology.



import duckdb


def validate_incremental_load():

    con = duckdb.connect("mobility.duckdb")

    try:
        result = con.sql("""
            SELECT
                COUNT(*) AS total_records,
                COUNT(DISTINCT trip_id) AS distinct_trip_ids,
                COUNT(*) - COUNT(DISTINCT trip_id)
                    AS duplicate_excess_rows,
                COUNT(*) FILTER (
                    WHERE trip_end_timestamp < trip_start_timestamp
                ) AS invalid_timestamp_records
            FROM raw.trips_incremental
        """).df()

        print("Incremental data validation:")
        print(result.to_string(index=False))

    finally:
        con.close()


if __name__ == "__main__":
    validate_incremental_load()
