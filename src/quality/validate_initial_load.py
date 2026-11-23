# checking three things:
# 1. Source and target row counts match.
# 2. trip_id uniqueness is preserved.
# 3. No records are missing from the target.


import duckdb


def validate_initial_load():

    con = duckdb.connect("mobility.duckdb")

    try:
        # Attach source database in read-only mode
        con.execute("""
            ATTACH 'mobility_exercise.duckdb'
            AS source_db (READ_ONLY)
        """)

        # Compare source and target row counts
        result = con.sql("""
            SELECT
                (SELECT COUNT(*)
                 FROM source_db.raw.trips_initial) AS source_count,

                (SELECT COUNT(*)
                 FROM raw.trips_initial) AS target_count
        """).df()

        print("Source vs Target:")
        print(result.to_string(index=False))

        # Check duplicate trip IDs in target
        duplicates = con.sql("""
            SELECT COUNT(*) AS duplicate_count
            FROM (
                SELECT trip_id
                FROM raw.trips_initial
                GROUP BY trip_id
                HAVING COUNT(*) > 1
            )
        """).df()

        print("\nDuplicate trip IDs:")
        print(duplicates.to_string(index=False))

        # Check missing records using EXCEPT
        missing = con.sql("""
            SELECT COUNT(*) AS missing_records
            FROM (
                SELECT * FROM source_db.raw.trips_initial

                EXCEPT

                SELECT * FROM raw.trips_initial
            )
        """).df()

        print("\nMissing records:")
        print(missing.to_string(index=False))

        con.execute("DETACH source_db")

    finally:
        con.close()


if __name__ == "__main__":
    validate_initial_load()
