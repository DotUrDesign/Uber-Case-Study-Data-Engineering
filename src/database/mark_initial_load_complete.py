
import duckdb


def mark_initial_load_complete():

    con = duckdb.connect("mobility.duckdb")

    try:
        # Verify fact table integrity before marking initialization complete.
        result = con.execute("""
            SELECT
                COUNT(*) AS total_records,
                COUNT(DISTINCT trip_id) AS distinct_trip_ids,
                COUNT(*) FILTER (
                    WHERE trip_id IS NULL
                ) AS null_trip_ids
            FROM analytics.fact_trips
        """).fetchone()

        total_records, distinct_ids, null_ids = result

        if total_records == 0 or total_records != distinct_ids or null_ids > 0:
            raise ValueError(
                "Fact table integrity check failed. "
                "Initial load cannot be marked complete."
            )

        # Register the existing fact table as initialized.
        con.execute("""
            UPDATE ops.pipeline_state
            SET
                initial_load_completed = TRUE,
                last_successful_run = CURRENT_TIMESTAMP
            WHERE pipeline_name = 'trusted_mobility_metrics'
        """)

        print("Initial load registered successfully!")
        print(f"Fact records: {total_records}")

    finally:
        con.close()


if __name__ == "__main__":
    mark_initial_load_complete()
