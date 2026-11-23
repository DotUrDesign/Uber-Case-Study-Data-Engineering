
import duckdb


def load_initial_data():

    # Connect to our project database
    con = duckdb.connect("mobility.duckdb")

    try:
        # Attach the original database in read-only mode
        con.execute("""
            ATTACH 'mobility_exercise.duckdb'
            AS source_db (READ_ONLY)
        """)

        # Copy initial trip records into our RAW schema
        con.execute("""
            CREATE OR REPLACE TABLE raw.trips_initial AS
            SELECT *
            FROM source_db.raw.trips_initial
        """)

        # Verify the number of ingested records
        result = con.sql("""
            SELECT COUNT(*) AS total_records
            FROM raw.trips_initial
        """).df()

        print("Initial data ingestion completed!")
        print(result.to_string(index=False))

        con.execute("DETACH source_db")

    finally:
        con.close()


if __name__ == "__main__":
    load_initial_data()
