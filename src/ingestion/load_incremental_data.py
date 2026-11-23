import duckdb


def load_incremental_data():

    con = duckdb.connect("mobility.duckdb")

    try:
        # Read incremental Parquet and load it into RAW
        con.execute("""
            CREATE OR REPLACE TABLE raw.trips_incremental AS
            SELECT *
            FROM read_parquet('data/raw/incremental_trips.parquet')
        """)

        # Verify the number of ingested records
        result = con.sql("""
            SELECT COUNT(*) AS total_records
            FROM raw.trips_incremental
        """).df()

        print("Incremental data ingestion completed!")
        print(result.to_string(index=False))

    finally:
        con.close()


if __name__ == "__main__":
    load_incremental_data()
