import subprocess
import sys
from pathlib import Path

import duckdb

PROJECT_ROOT = Path(__file__).resolve().parents[1]

steps = [
    "src/ingestion/load_initial_data.py",
    "src/ingestion/load_incremental_data.py",
    "src/transformations/build_staging.py",
    "src/transformations/clean_staging.py",
    "src/transformations/build_trusted_model.py",
    "src/transformations/build_weekly_metrics.py",
    "src/quality/validate_trusted_model.py",
]

def run_pipeline():
    for step in steps:
        print(f"\nRunning: {step}", flush=True)

        subprocess.run(
            [sys.executable, step],
            cwd=PROJECT_ROOT,
            check=True
        )

    # Export quarantined records for inspection
    quarantine_dir = PROJECT_ROOT / "data" / "quarantine"
    quarantine_dir.mkdir(parents=True, exist_ok=True)

    output_file = quarantine_dir / "rejected_trips.parquet"

    con = duckdb.connect(str(PROJECT_ROOT / "mobility.duckdb"))

    try:
        con.execute(f"""
            COPY (
                SELECT *
                FROM ops.quarantine_records
            )
            TO '{output_file.as_posix()}'
            (FORMAT PARQUET);
        """)
    finally:
        con.close()

    print(f"\nQuarantine exported to: {output_file}", flush=True)
    print("\nPIPELINE COMPLETED SUCCESSFULLY!", flush=True)


if __name__ == "__main__":
    run_pipeline()