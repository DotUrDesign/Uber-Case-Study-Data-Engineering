
import duckdb
import hashlib
from pathlib import Path
from datetime import datetime


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DB_PATH = PROJECT_ROOT / "mobility.duckdb"
PARQUET_PATH = PROJECT_ROOT / "data" / "raw" / "incremental_trips.parquet"


def generate_batch_id(file_path):

    sha256 = hashlib.sha256()

    with open(file_path, "rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            sha256.update(chunk)

    return sha256.hexdigest()


def load_incremental_data():

    if not PARQUET_PATH.exists():
        raise FileNotFoundError(
            f"Incremental file not found: {PARQUET_PATH}"
        )

    batch_id = generate_batch_id(PARQUET_PATH)

    con = duckdb.connect(str(DB_PATH))
    batch_registered = False

    try:
        # Skip successfully processed batches.
        batch_status = con.execute("""
            SELECT batch_status
            FROM ops.batch_log
            WHERE batch_id = ?
        """, [batch_id]).fetchone()

        if batch_status and batch_status[0] == "SUCCESS":
            print(f"Batch already processed. Skipping: {batch_id}")
            return

        # Load incoming Parquet data.
        con.execute("""
            CREATE OR REPLACE TABLE raw.trips_incremental AS
            SELECT *
            FROM read_parquet(?)
        """, [str(PARQUET_PATH)])

        records_received = con.execute("""
            SELECT COUNT(*)
            FROM raw.trips_incremental
        """).fetchone()[0]

        # Register or restart the batch.
        started_at = datetime.now()

        con.execute("""
            INSERT INTO ops.batch_log (
                batch_id,
                batch_status,
                records_received,
                started_at
            )
            VALUES (?, 'IN_PROGRESS', ?, ?)

            ON CONFLICT (batch_id)
            DO UPDATE SET
                batch_status = 'IN_PROGRESS',
                records_received = EXCLUDED.records_received,
                started_at = EXCLUDED.started_at,
                completed_at = NULL,
                error_message = NULL
        """, [batch_id, records_received, started_at])

        batch_registered = True

        print("Incremental data ingestion completed!")
        print(f"Batch ID: {batch_id}")
        print(f"Records received: {records_received}")
        print("Batch status: IN_PROGRESS")

    except Exception as error:

        if batch_registered:
            con.execute("""
                UPDATE ops.batch_log
                SET
                    batch_status = 'FAILED',
                    completed_at = ?,
                    error_message = ?
                WHERE batch_id = ?
            """, [datetime.now(), str(error), batch_id])

        raise

    finally:
        con.close()


if __name__ == "__main__":
    load_incremental_data()
