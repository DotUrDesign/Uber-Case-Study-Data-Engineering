
import duckdb


def inspect_source_schema():

    con = duckdb.connect(
        "mobility_exercise.duckdb",
        read_only=True
    )

    try:
        # Inspect column names and data types
        schema = con.sql("""
            DESCRIBE raw.trips_initial
        """).df()

        print("Initial trips table schema:")
        print(schema.to_string(index=False))

        # Check total number of records
        count = con.sql("""
            SELECT COUNT(*) AS total_records
            FROM raw.trips_initial
        """).df()

        print("\nTotal records:")
        print(count.to_string(index=False))

    finally:
        con.close()


if __name__ == "__main__":
    inspect_source_schema()
