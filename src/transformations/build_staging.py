# incremental data + initial data ==> staging data
# why union-all ? --> Because I want to preserve duplicates for now. 


import duckdb


def build_staging():

    con = duckdb.connect("mobility.duckdb")

    try:
        # Combine initial and incremental datasets
        con.execute("""
            CREATE OR REPLACE TABLE staging.trips_union AS

            SELECT
                *,
                'initial' AS source_dataset
            FROM raw.trips_initial

            UNION ALL

            SELECT
                *,
                'incremental' AS source_dataset
            FROM raw.trips_incremental
        """)

        # Validate the combined record count
        result = con.sql("""
            SELECT
                source_dataset,
                COUNT(*) AS total_records
            FROM staging.trips_union
            GROUP BY source_dataset
            ORDER BY source_dataset
        """).df()

        print("Staging union created successfully!")
        print(result.to_string(index=False))

    finally:
        con.close()


if __name__ == "__main__":
    build_staging()
