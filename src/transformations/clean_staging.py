
import duckdb


def clean_staging():

    con = duckdb.connect("mobility.duckdb")

    try:
        # 1. Deduplicate using trip_id
        # Prefer initial records when the same ID exists in both sources.
        con.execute("""
            CREATE OR REPLACE TABLE staging.trips_deduplicated AS

            SELECT * EXCLUDE (row_num)
            FROM (
                SELECT
                    *,
                    ROW_NUMBER() OVER (
                        PARTITION BY trip_id
                        ORDER BY
                            CASE
                                WHEN source_dataset = 'initial' THEN 1
                                ELSE 2
                            END
                    ) AS row_num
                FROM staging.trips_union
            )
            WHERE row_num = 1
        """)

        # 2. Quarantine records with invalid chronology
        con.execute("""
            CREATE OR REPLACE TABLE ops.quarantine_records AS

            SELECT
                *,
                'END_BEFORE_START' AS rejection_reason
            FROM staging.trips_deduplicated
            WHERE trip_end_timestamp < trip_start_timestamp
        """)

        # 3. Keep valid records in staging
        con.execute("""
            CREATE OR REPLACE TABLE staging.trips_validated AS

            SELECT *
            FROM staging.trips_deduplicated
            WHERE trip_end_timestamp >= trip_start_timestamp
        """)

        # 4. Print processing summary
        result = con.sql("""
            SELECT
                (SELECT COUNT(*)
                 FROM staging.trips_union) AS raw_combined_count,

                (SELECT COUNT(*)
                 FROM staging.trips_deduplicated) AS deduplicated_count,

                (SELECT COUNT(*)
                 FROM ops.quarantine_records) AS quarantined_count,

                (SELECT COUNT(*)
                 FROM staging.trips_validated) AS valid_count
        """).df()

        print("Staging cleanup completed!")
        print(result.to_string(index=False))

    finally:
        con.close()


if __name__ == "__main__":
    clean_staging()
