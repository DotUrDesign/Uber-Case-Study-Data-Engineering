# analyzing the count of duplicates from staging table
# what are the distinct sources of duplicates 
# LIKE -
# id = 123 has 2 occurences - 1 from initial load, 1 from incremental load
# id = 456 has 2 occurences - 0 from initial load, 2 from incremental load 
# id = 444 has 3 occurences - 1 from initial load, 2 from incremental load



import duckdb


def analyze_duplicates():

    con = duckdb.connect("mobility.duckdb")

    try:
        result = con.sql("""
            SELECT
                COUNT(*) AS total_records,
                COUNT(DISTINCT trip_id) AS distinct_trip_ids,
                COUNT(*) - COUNT(DISTINCT trip_id)
                    AS duplicate_excess_rows
            FROM staging.trips_union
        """).df()

        print("Overall duplicate analysis:")
        print(result.to_string(index=False))

        # Identify duplicate trip IDs and their source datasets
        duplicates = con.sql("""
            SELECT
                trip_id,
                COUNT(*) AS occurrence_count,
                STRING_AGG(
                    DISTINCT source_dataset,
                    ', '
                ) AS source_datasets
            FROM staging.trips_union
            GROUP BY trip_id
            HAVING COUNT(*) > 1
            ORDER BY occurrence_count DESC
            LIMIT 20
        """).df()

        print("\nSample duplicate trip IDs:")
        print(duplicates.to_string(index=False))

    finally:
        con.close()


if __name__ == "__main__":
    analyze_duplicates()
