
import subprocess
import sys
import hashlib
from pathlib import Path
from datetime import datetime

import duckdb


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_ROOT / "mobility.duckdb"
INCREMENTAL_FILE = PROJECT_ROOT / "data" / "raw" / "incremental_trips.parquet"

PIPELINE_NAME = "trusted_mobility_metrics"


def run_step(command, description):
    print(f"\nRunning: {description}", flush=True)

    subprocess.run(
        [sys.executable] + command,
        cwd=PROJECT_ROOT,
        check=True
    )


def get_batch_id():
    sha256 = hashlib.sha256()

    with open(INCREMENTAL_FILE, "rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            sha256.update(chunk)

    return sha256.hexdigest()


def get_pipeline_state():
    con = duckdb.connect(str(DB_PATH))
    try:
        result = con.execute("""
            SELECT initial_load_completed
            FROM ops.pipeline_state
            WHERE pipeline_name = ?
        """, [PIPELINE_NAME]).fetchone()

        if result is None:
            raise RuntimeError("Pipeline state is not initialized.")

        return result[0]
    finally:
        con.close()


def get_batch_status(batch_id):
    con = duckdb.connect(str(DB_PATH))
    try:
        result = con.execute("""
            SELECT batch_status
            FROM ops.batch_log
            WHERE batch_id = ?
        """, [batch_id]).fetchone()

        return result[0] if result else None
    finally:
        con.close()


def export_quarantine():
    con = duckdb.connect(str(DB_PATH))

    try:
        tables = con.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'ops'
              AND table_name IN (
                  'quarantine_records',
                  'quarantine_records_incremental'
              )
            ORDER BY table_name
        """).fetchall()

        if not tables:
            return

        queries = [
            f"SELECT * FROM ops.{table[0]}"
            for table in tables
        ]

        output_file = (
            PROJECT_ROOT / "data" / "quarantine" / "rejected_trips.parquet"
        )
        output_file.parent.mkdir(parents=True, exist_ok=True)

        output_path = str(output_file).replace("\\", "/").replace("'", "''")

        con.execute(f"""
            COPY (
                {" UNION ALL BY NAME ".join(queries)}
            )
            TO '{output_path}'
            (FORMAT PARQUET)
        """)

        print(f"Quarantine exported to: {output_file}", flush=True)

    finally:
        con.close()


def mark_batch_failed(batch_id, error):
    con = duckdb.connect(str(DB_PATH))
    try:
        con.execute("""
            UPDATE ops.batch_log
            SET batch_status = 'FAILED',
                completed_at = ?,
                error_message = ?
            WHERE batch_id = ?
              AND batch_status != 'SUCCESS'
        """, [datetime.now(), str(error), batch_id])
    finally:
        con.close()


def run_initial_pipeline(batch_id):

    try:
        print("\nStarting INITIAL pipeline run", flush=True)

        steps = [
            ("src/ingestion/load_initial_data.py", "Initial data ingestion"),
            ("src/ingestion/load_incremental_data.py", "Incremental data ingestion"),
            ("src/transformations/build_staging.py", "Build staging"),
            ("src/transformations/clean_staging.py", "Clean and validate staging"),
            ("src/transformations/build_trusted_model.py", "Build trusted model"),
            ("src/transformations/build_weekly_metrics.py", "Build weekly metrics"),
            ("src/quality/validate_trusted_model.py", "Validate trusted model"),
        ]

        for step, description in steps:
            run_step([step], description)

        export_quarantine()

        # Update state only after all stages succeed.
        con = duckdb.connect(str(DB_PATH))
        try:
            now = datetime.now()

            con.execute("BEGIN TRANSACTION")

            con.execute("""
                UPDATE ops.batch_log
                SET batch_status = 'SUCCESS',
                    completed_at = ?,
                    error_message = NULL
                WHERE batch_id = ?
            """, [now, batch_id])

            con.execute("""
                UPDATE ops.pipeline_state
                SET initial_load_completed = TRUE,
                    last_successful_batch_id = ?,
                    last_successful_run = ?
                WHERE pipeline_name = ?
            """, [batch_id, now, PIPELINE_NAME])

            con.execute("COMMIT")

        except Exception:
            con.execute("ROLLBACK")
            raise
        finally:
            con.close()

        print("\nInitial pipeline completed successfully!", flush=True)

    except Exception as error:
        mark_batch_failed(batch_id, error)
        raise


def run_incremental_pipeline(batch_id):

    print("\nStarting INCREMENTAL pipeline run", flush=True)

    if get_batch_status(batch_id) == "SUCCESS":
        print("\nBatch already processed successfully. Skipping.", flush=True)
        return

    try:
        steps = [
            (
                ["src/ingestion/load_incremental_data.py"],
                "Incremental data ingestion"
            ),
            (
                ["src/transformations/build_staging.py"],
                "Build staging"
            ),
            (
                [
                    "-c",
                    "from src.transformations.clean_staging import clean_staging; "
                    "clean_staging(source_table='staging.trips_incremental', "
                    "output_suffix='_incremental')"
                ],
                "Validate incremental staging"
            ),
            (
                ["src/transformations/classify_incremental_records.py"],
                "Classify incremental records"
            ),
            (
                ["src/transformations/merge_incremental_trips.py"],
                "Merge new records into fact table"
            ),
            (
                ["src/transformations/refresh_incremental_weekly_metrics.py"],
                "Refresh affected weekly metrics"
            ),
            (
                ["src/quality/validate_trusted_model.py"],
                "Validate trusted model"
            ),
        ]

        for command, description in steps:
            run_step(command, description)

        export_quarantine()

        # Collect statistics after successful processing.
        con = duckdb.connect(str(DB_PATH))

        try:
            inserted, ignored, conflicts = con.execute("""
                SELECT
                    COUNT(*) FILTER (
                        WHERE record_status = 'NEW'
                    ),
                    COUNT(*) FILTER (
                        WHERE record_status = 'IDENTICAL'
                    ),
                    COUNT(*) FILTER (
                        WHERE record_status = 'CONFLICT'
                    )
                FROM staging.incremental_classification
            """).fetchone()

            quarantined = con.execute("""
                SELECT COUNT(*)
                FROM ops.quarantine_records_incremental
            """).fetchone()[0]

            now = datetime.now()

            con.execute("BEGIN TRANSACTION")

            con.execute("""
                UPDATE ops.batch_log
                SET batch_status = 'SUCCESS',
                    records_inserted = ?,
                    records_updated = 0,
                    records_ignored = ?,
                    records_quarantined = ?,
                    completed_at = ?,
                    error_message = ?
                WHERE batch_id = ?
            """, [
                inserted,
                ignored,
                quarantined,
                now,
                f"{conflicts} conflicting records flagged"
                if conflicts else None,
                batch_id
            ])

            con.execute("""
                UPDATE ops.pipeline_state
                SET last_successful_batch_id = ?,
                    last_successful_run = ?
                WHERE pipeline_name = ?
            """, [batch_id, now, PIPELINE_NAME])

            con.execute("COMMIT")

        except Exception:
            con.execute("ROLLBACK")
            raise
        finally:
            con.close()

        print("\nIncremental pipeline completed successfully!", flush=True)
        print(f"New records: {inserted}")
        print(f"Identical records ignored: {ignored}")
        print(f"Conflicts flagged: {conflicts}")
        print(f"Quarantined records: {quarantined}")

    except Exception as error:
        mark_batch_failed(batch_id, error)
        raise


def run_pipeline():

    try:
        batch_id = get_batch_id()
        initial_completed = get_pipeline_state()

        if initial_completed:
            run_incremental_pipeline(batch_id)
        else:
            run_initial_pipeline(batch_id)

        export_quarantine()

        print("\nPIPELINE COMPLETED SUCCESSFULLY!", flush=True)

    except Exception as error:
        print(f"\nPIPELINE FAILED: {error}", flush=True)
        raise


if __name__ == "__main__":
    run_pipeline()
