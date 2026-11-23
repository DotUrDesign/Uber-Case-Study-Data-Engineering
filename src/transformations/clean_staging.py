
import duckdb

DURATION_TOLERANCE_SECONDS = 900


def clean_staging(
    source_table="staging.trips_union",
    output_suffix=""
):

    con = duckdb.connect("mobility.duckdb")

    try:
        deduplicated_table = f"staging.trips_deduplicated{output_suffix}"
        validated_table = f"staging.trips_validated{output_suffix}"
        diagnosis_table = f"staging.trip_diagnosis{output_suffix}"

        quarantine_table = (
            "ops.quarantine_records"
            if not output_suffix
            else f"ops.quarantine_records{output_suffix}"
        )

        # 1. Quarantine records with missing business keys.
        con.execute(f"""
            CREATE OR REPLACE TABLE {quarantine_table} AS
            SELECT
                *,
                'MISSING_BUSINESS_KEY' AS rejection_reason
            FROM {source_table}
            WHERE trip_id IS NULL
        """)

        # 2. Deduplicate records.
        con.execute(f"""
            CREATE OR REPLACE TABLE {deduplicated_table} AS
            SELECT * EXCLUDE (row_num)
            FROM (
                SELECT
                    *,
                    ROW_NUMBER() OVER (
                        PARTITION BY trip_id
                        ORDER BY
                            CASE
                                WHEN source_dataset = 'initial'
                                    THEN 1
                                ELSE 2
                            END
                    ) AS row_num
                FROM {source_table}
                WHERE trip_id IS NOT NULL
            )
            WHERE row_num = 1
        """)

        # 3. Diagnose duration anomalies.
        con.execute(f"""
            CREATE OR REPLACE TABLE {diagnosis_table} AS

            WITH duration_comparison AS (
                SELECT
                    trip_id,
                    source_dataset,
                    trip_seconds,

                    DATE_DIFF(
                        'second',
                        trip_start_timestamp,
                        trip_end_timestamp
                    ) AS calculated_trip_duration

                FROM {deduplicated_table}
                WHERE trip_start_timestamp IS NOT NULL
                  AND trip_end_timestamp IS NOT NULL
            )

            SELECT
                *,
                ABS(
                    trip_seconds - calculated_trip_duration
                ) AS duration_difference_seconds,

                CASE
                    WHEN trip_seconds IS NULL
                        THEN 'MISSING_TRIP_SECONDS'

                    WHEN ABS(
                        trip_seconds - calculated_trip_duration
                    ) > {DURATION_TOLERANCE_SECONDS}
                        THEN 'DURATION_MISMATCH'
                END AS diagnosis_reason

            FROM duration_comparison

            WHERE trip_seconds IS NULL
               OR ABS(
                    trip_seconds - calculated_trip_duration
               ) > {DURATION_TOLERANCE_SECONDS}
        """)

        # 4. Quarantine invalid timestamps.
        con.execute(f"""
            INSERT INTO {quarantine_table}

            SELECT
                *,
                CASE
                    WHEN trip_start_timestamp IS NULL
                     AND trip_end_timestamp IS NULL
                        THEN 'MISSING_START_AND_END_TIMESTAMP'

                    WHEN trip_start_timestamp IS NULL
                        THEN 'MISSING_START_TIMESTAMP'

                    WHEN trip_end_timestamp IS NULL
                        THEN 'MISSING_END_TIMESTAMP'

                    WHEN trip_end_timestamp < trip_start_timestamp
                        THEN 'END_BEFORE_START'
                END AS rejection_reason

            FROM {deduplicated_table}

            WHERE trip_start_timestamp IS NULL
               OR trip_end_timestamp IS NULL
               OR trip_end_timestamp < trip_start_timestamp
        """)

        # 5. Create validated records.
        con.execute(f"""
            CREATE OR REPLACE TABLE {validated_table} AS

            SELECT *
            FROM {deduplicated_table}

            WHERE trip_start_timestamp IS NOT NULL
              AND trip_end_timestamp IS NOT NULL
              AND trip_end_timestamp >= trip_start_timestamp
        """)

        # 6. Print summary for the selected dataset.
        result = con.execute(f"""
            SELECT
                (SELECT COUNT(*) FROM {source_table})
                    AS records_received,

                (SELECT COUNT(*) FROM {deduplicated_table})
                    AS deduplicated_count,

                (SELECT COUNT(*) FROM {quarantine_table})
                    AS quarantined_count,

                (SELECT COUNT(*) FROM {validated_table})
                    AS valid_count,

                (SELECT COUNT(*) FROM {diagnosis_table})
                    AS diagnosis_count
        """).df()

        print("Staging cleanup completed!")
        print(result.to_string(index=False))

    finally:
        con.close()


if __name__ == "__main__":
    clean_staging()
