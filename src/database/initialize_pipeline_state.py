# Why are we introducing this table?
# We need persistent state because the pipeline must know whether it is performing:
# - Its first historical load.
# - A subsequent incremental batch.


import duckdb


def initialize_pipeline_state():

    con = duckdb.connect("mobility.duckdb")

    try:
        con.execute("CREATE SCHEMA IF NOT EXISTS ops")

        con.execute("""
            CREATE TABLE IF NOT EXISTS ops.pipeline_state (
                pipeline_name VARCHAR PRIMARY KEY,
                initial_load_completed BOOLEAN DEFAULT FALSE,
                last_successful_batch_id VARCHAR,
                last_successful_run TIMESTAMP
            )
        """)

        con.execute("""
            INSERT INTO ops.pipeline_state (
                pipeline_name,
                initial_load_completed
            )
            VALUES ('trusted_mobility_metrics', FALSE)
            ON CONFLICT (pipeline_name) DO NOTHING
        """)

        # Track individual incremental batches.
        con.execute("""
            CREATE TABLE IF NOT EXISTS ops.batch_log (
                batch_id VARCHAR PRIMARY KEY,
                batch_status VARCHAR,
                records_received BIGINT,
                records_inserted BIGINT,
                records_updated BIGINT,
                records_ignored BIGINT,
                records_quarantined BIGINT,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                error_message VARCHAR
            )
        """)

        print("Pipeline state and batch tracking initialized!")

        print(
            con.execute("""
                SELECT * FROM ops.pipeline_state
            """).df().to_string(index=False)
        )

    finally:
        con.close()


if __name__ == "__main__":
    initialize_pipeline_state()
