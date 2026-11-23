# Trusted Mobility Metrics Pipeline

A data engineering solution for processing Chicago mobility trip data, handling initial and incremental deliveries, maintaining data quality, and generating analytics-ready weekly mobility metrics.

The solution uses Python and DuckDB to build a layered data pipeline that transforms raw trip records into trusted fact and dimension tables.

---

## 1. Project Overview

The objective of this project is to build a reliable data pipeline that processes mobility trip data received through two deliveries:

- **Initial delivery:** Historical trip data provided in a DuckDB database.
- **Incremental delivery:** Additional trip records provided in Parquet format.

The pipeline combines these datasets, identifies duplicate records, validates data quality, handles invalid records, and produces trusted analytical tables.

The final output includes trip-level transactional data and weekly mobility metrics that can be used by analysts and business stakeholders.

### Key capabilities

- Initial and incremental data ingestion.
- Metadata-independent, reusable staging transformations.
- Duplicate detection using `trip_id` as the business key.
- Data validation, diagnosis, and quarantine handling.
- Dimensional modelling using fact and dimension tables.
- Batch tracking and batch-level idempotency.
- Incremental insertion of new trip records.
- Conflict detection for existing trip IDs with changed attributes.
- Targeted refresh of affected weekly metrics.
- Automated data quality and reconciliation tests using Pytest.

---

## 2. Technology Stack

| Technology | Purpose |
|---|---|
| Python | Pipeline orchestration and execution |
| DuckDB | Analytical database and SQL processing |
| SQL | Data transformations, joins, aggregations and modelling |
| Parquet | Columnar storage for incremental data and quarantine exports |
| Pandas | Lightweight data inspection and analysis |
| PyArrow | Parquet handling and columnar data support |
| Pytest | Automated testing and data validation |

DuckDB was selected because the dataset is suitable for local analytical processing. It supports efficient SQL execution and direct interaction with Parquet files without requiring additional distributed infrastructure.

For significantly larger workloads, the transformation layer could be migrated to Apache Spark or another distributed processing engine.

---

## 3. Architecture

The pipeline follows a layered architecture:

**RAW → STAGING → TRUSTED → ANALYTICS**

### RAW Layer

The raw layer stores the source data without applying business transformations.

Sources:

- Initial data: `mobility_exercise.duckdb`
- Incremental data: `incremental_trips.parquet`

Tables:

- `raw.trips_initial`
- `raw.trips_incremental`

The initial and incremental datasets are ingested separately to preserve their source identity.

### STAGING Layer

The staging layer combines the source datasets and prepares them for trusted processing.

Main operations:

1. Combine initial and incremental records using `UNION ALL`.
2. Preserve source information using a `source_dataset` column.
3. Identify duplicate `trip_id` values.
4. Deduplicate records using the defined source-priority rule.
5. Validate timestamps and required business keys.
6. Quarantine invalid records.
7. Identify trip-duration discrepancies for further diagnosis.

The same staging-cleaning function is reused for both initial and incremental processing through parameters such as `source_table` and `output_suffix`.

### TRUSTED Layer

The trusted layer contains validated, deduplicated and analytics-ready data.

It consists of:

- `analytics.fact_trips`
- `analytics.dim_date`
- `analytics.dim_community_area`
- `analytics.fact_weekly_mobility_metrics`

These tables provide a consistent foundation for downstream reporting and analysis.

---

## 4. Data Understanding and Profiling

The source datasets contain 16 columns describing individual mobility trips.

| Column | Description |
|---|---|
| `trip_id` | Unique trip identifier |
| `trip_start_timestamp` | Trip start timestamp |
| `trip_end_timestamp` | Trip end timestamp |
| `trip_seconds` | Trip duration in seconds |
| `trip_miles` | Trip distance |
| `percent_time_chicago` | Percentage of trip time within Chicago |
| `percent_distance_chicago` | Percentage of trip distance within Chicago |
| `pickup_community_area` | Pickup community area |
| `dropoff_community_area` | Drop-off community area |
| `fare` | Base fare |
| `tip` | Tip amount |
| `additional_charges` | Additional charges |
| `trip_total` | Total trip price |
| `shared_trip_authorized` | Whether shared travel was authorized |
| `shared_trip_match` | Whether a shared trip match occurred |
| `trips_pooled` | Number of trips pooled together |

### Business key

`trip_id` is used as the business key to identify individual trips.

Its uniqueness is validated rather than assumed.

### Geography

The dataset focuses on four Chicago community areas:

| Community Area ID | Name |
|---:|---|
| 24 | West Town |
| 41 | Hyde Park |
| 43 | South Shore |
| 56 | Garfield Ridge |

Community area values can be NULL. These records are retained in the fact table rather than being rejected solely because geographic information is missing.

---

## 5. Data Quality and Deduplication

### Duplicate handling

Duplicate records were identified in two forms:

1. Duplicates within an individual delivery.
2. Overlapping records between initial and incremental deliveries.

The observed source data contained:

- 100 excess duplicate records within the incremental delivery.
- 50 excess records from overlap between initial and incremental deliveries.

The deduplication process uses `trip_id` as the business key.

When the same trip exists in both deliveries, the initial source record receives priority.

Identical records are reduced to one record.

For incremental processing, records are classified into three categories:

| Classification | Meaning | Action |
|---|---|---|
| NEW | `trip_id` does not exist in the trusted fact table | Insert |
| IDENTICAL | Existing trip has identical attributes | Ignore |
| CONFLICT | Existing trip has different attributes | Flag for investigation |

Conflicting records are not silently overwritten.

### Validation and quarantine

Records that violate mandatory data-quality conditions are moved to quarantine rather than being permanently deleted.

The implemented checks include:

- Missing `trip_id`.
- Invalid or missing trip timestamps.
- End timestamp earlier than start timestamp.

The source timestamps are rounded to the nearest 15 minutes. Therefore, a duration discrepancy greater than 900 seconds is identified for diagnosis.

Duration discrepancies are retained in the validated dataset but separately identified for further investigation.

Missing community area values are preserved because they do not necessarily indicate invalid trip records.

- Missing pickup area: The trip remains in the fact table but is excluded from pickup-area weekly metrics.
- Missing dropoff area: The original NULL is preserved.

Quarantined records are also exported to:

`data/quarantine/rejected_trips.parquet`

---

## 6. Data Model

### Fact table: `analytics.fact_trips`

**Grain:** One row per unique `trip_id`.

The table contains trip-level measures and attributes, along with foreign keys referencing the date and community area dimensions.

### Dimension table: `analytics.dim_date`

Provides reusable calendar attributes:

- Date key
- Full date
- Day
- Month
- Month name
- Quarter
- Year
- Day of week
- Week start date

The week starts on Monday.

### Dimension table: `analytics.dim_community_area`

Contains community area identifiers, surrogate keys and available descriptive attributes.

The fact table references the dimension using surrogate keys.

### Weekly metrics: `analytics.fact_weekly_mobility_metrics`

**Grain:** One record per `week_start_date` and `pickup_community_area_key`.

The table contains:

| Metric | Definition |
|---|---|
| `trip_volume` | Distinct trip count |
| `total_trip_price` | Sum of trip totals |
| `price_observation_count` | Number of non-NULL trip totals |
| `average_trip_price` | Total trip price divided by price observation count |
| `matched_trip_count` | Trips where `shared_trip_match = TRUE` |
| `eligible_trip_count` | Trips where `shared_trip_match IS NOT NULL` |
| `shared_trip_rate` | Matched trips divided by eligible trips, multiplied by 100 |

Zero-value trip totals are retained in the average calculation. NULL trip totals are excluded.

The shared-trip rate uses non-NULL `shared_trip_match` values as its denominator.

---

## 7. Incremental Processing Strategy

The pipeline supports two execution paths.

### Initial execution

The initial execution performs the following operations:

1. Ingest initial data.
2. Ingest the supplied incremental delivery.
3. Build combined staging.
4. Deduplicate and validate the combined dataset.
5. Build the trusted fact and dimension tables.
6. Generate weekly metrics.
7. Validate the trusted model.
8. Export quarantine records.
9. Update pipeline state and batch status.

### Subsequent incremental executions

Once the initial load is marked complete, subsequent executions follow a different path:

1. Ingest the new incremental Parquet file.
2. Rebuild staging inputs.
3. Clean and validate only the incremental dataset.
4. Classify records as NEW, IDENTICAL or CONFLICT.
5. Insert new records into the existing fact table.
6. Ignore identical records.
7. Flag conflicting records.
8. Identify affected week-area combinations.
9. Refresh only those weekly metric combinations.
10. Validate the trusted model.
11. Update batch log and pipeline state.

The existing fact table is not rebuilt during incremental processing.

### Handling late-arriving records

Weekly metrics are based on `trip_start_timestamp`, not the date on which a record arrives.

Therefore, a late-arriving trip is assigned to its actual reporting week.

The incremental metrics refresh identifies the affected week-area combinations and recalculates those combinations using the full fact data.

This ensures historical weekly aggregates are updated without rebuilding the entire weekly metrics table.

---

## 8. Batch Tracking and Idempotency

The pipeline maintains operational metadata in DuckDB.

### `ops.batch_log`

Tracks batch execution details, including:

- Batch ID
- Batch status
- Records received
- Records inserted
- Records updated
- Records ignored
- Records quarantined
- Start and completion timestamps
- Error message

### `ops.pipeline_state`

Maintains the pipeline's execution state, including:

- Pipeline name
- Initial load completion status
- Last successful batch ID
- Last successful execution timestamp

### Batch ID generation

A deterministic SHA-256 hash is generated using the binary contents of the incremental Parquet file.

This allows the pipeline to identify a previously processed file.

- Previously successful batch: Skip processing.
- New batch: Process it.
- Previously failed batch: Allow it to be retried.

The batch identifier is based on the exact file contents, not the logical identity of the records.

---

## 9. Project Structure

```text
trusted-mobility-metrics/
│
├── data/
│   ├── raw/
│   │   └── incremental_trips.parquet
│   │
│   └── quarantine/
│       └── rejected_trips.parquet
│
├── sql/
│   ├── create_trusted_model.sql
│   └── create_weekly_metrics.sql
│
├── src/
│   ├── ingestion/
│   │   ├── load_initial_data.py
│   │   ├── load_incremental_data.py
│   │   ├── inspect_source.py
│   │   └── inspect_source_schema.py
│   │
│   ├── transformations/
│   │   ├── build_staging.py
│   │   ├── clean_staging.py
│   │   ├── build_trusted_model.py
│   │   ├── build_weekly_metrics.py
│   │   ├── classify_incremental_records.py
│   │   ├── merge_incremental_trips.py
│   │   └── refresh_incremental_weekly_metrics.py
│   │
│   ├── quality/
│   │   ├── validate_initial_load.py
│   │   ├── validate_incremental_load.py
│   │   ├── validate_trusted_model.py
│   │   ├── analyze_duplicates.py
│   │   ├── classify_duplicates.py
│   │   └── verify_duplicate_records.py
│   │
│   ├── database/
│   │   ├── initialize_pipeline_state.py
│   │   └── mark_initial_load_complete.py
│   │
│   └── pipeline.py
│
├── tests/
│   └── test_pipeline.py
│
├── .gitignore
├── README.md
└── requirements.txt
```

The DuckDB databases are generated or supplied locally and are not committed to the repository.

---

## 10. Getting Started

### Prerequisites

- Python 3.10 or later.
- Git.
- Access to the original assignment source database and incremental Parquet file.

### Step 1: Clone the repository

```bash
git clone <GITHUB_REPOSITORY_URL>
```

Navigate to the project directory:

```bash
cd trusted-mobility-metrics
```

### Step 2: Create a virtual environment

Windows:

```cmd
python -m venv .venv
.venv\Scripts\activate
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Step 3: Install dependencies

```bash
pip install -r requirements.txt
```

The requirements file should contain the project's required packages, including DuckDB, Pandas, PyArrow and Pytest.

### Step 4: Provide the input datasets

Place the source files in their expected locations:

```text
trusted-mobility-metrics/
│
├── mobility_exercise.duckdb
│
└── data/
    └── raw/
        └── incremental_trips.parquet
```

`mobility_exercise.duckdb` contains the original source data used for the initial load.

`incremental_trips.parquet` contains the incremental delivery.

These source files are not generated by the pipeline. They must be obtained from the case study data package or provided separately.

### Step 5: Initialize pipeline state

Run:

```cmd
python src/database/initialize_pipeline_state.py
```

This initializes the operational state required to track pipeline execution and batch processing.

### Step 6: Execute the pipeline

Run the main orchestration script:

```cmd
python src/pipeline.py
```

The script determines whether the pipeline should execute the initial or incremental processing path based on the persisted pipeline state.

Individual processing steps are executed sequentially.

If a step fails, execution stops rather than continuing with incomplete results.

---

## 11. Running Subsequent Incremental Loads

After the initial execution has completed successfully, the pipeline can process subsequent incremental deliveries.

Replace:

`data/raw/incremental_trips.parquet`

with the new incremental Parquet file.

Then execute:

```cmd
python src/pipeline.py
```

The pipeline will:

1. Generate the new batch ID.
2. Check whether the batch has already been processed.
3. Register and ingest the batch.
4. Validate and classify incoming records.
5. Insert new records and flag conflicts.
6. Refresh affected weekly metrics.
7. Update the batch log and pipeline state.

If the exact same successfully processed file is submitted again, the pipeline skips it.

**Important:** Keep a copy of each original delivery if you need to retain historical source files for audit or recovery.

---

## 12. Running Automated Tests

Pytest is used to validate the final trusted model and analytical outputs.

The test file is:

`tests/test_pipeline.py`

Run all tests from the project root:

```cmd
pytest -v
```

Alternatively, run the specific test file:

```cmd
pytest -v tests/test_pipeline.py
```

### Current automated test coverage

| Test | What it validates |
|---|---|
| Fact trip ID uniqueness | No duplicate business keys |
| Timestamp validation | No end timestamp before start |
| Quarantine validation | Invalid records are quarantined |
| Weekly metric grain | No duplicate week-area combinations |
| Weekly metric reconciliation | Aggregates match the trusted fact data |
| Initial pipeline state | Initial load is marked complete |
| Successful batch tracking | Last successful batch has SUCCESS status |
| Pickup area validation | No missing pickup area keys in the fact table |

The tests connect to `mobility.duckdb` in read-only mode.

**Run the pipeline successfully before executing the tests.**

The current tests validate the database state. They do not create an isolated test database or independently execute every incremental scenario.

For additional testing, new cases can be added to `tests/test_pipeline.py` using Pytest.

For example, useful scenarios include:

- New trip insertion.
- Identical record handling.
- Conflicting record handling.
- Batch-level idempotency.
- Late-arriving records.
- Invalid record quarantine.
- Weekly metrics refresh.

A new test should verify both the expected result and that existing trusted data has not been unintentionally changed.

---

## 13. Data Validation and Expected Results

For the supplied case study datasets, the initial combined processing produced the following results:

| Validation | Expected result |
|---|---:|
| Initial records | 965,201 |
| Incremental records | 305,457 |
| Combined raw records | 1,270,658 |
| Deduplicated records | 1,270,508 |
| Quarantined records | 20 |
| Valid records | 1,270,488 |
| Fact table records | 1,270,488 |
| Unique trip IDs | 1,270,488 |
| Weekly metric rows | 34 |

### Weekly metrics reconciliation

The initial trusted model produced these overall results:

| Metric | Result |
|---|---:|
| Total trip volume | 1,270,488 |
| Price observations | 1,266,711 |
| Total trip price | 29,648,959.61 |
| Weighted average trip price | 23.41 |
| Matched shared trips | 62,433 |
| Eligible shared trips | 1,270,488 |
| Shared trip rate | 4.91% |

These figures are reference results for the supplied input datasets. Results may differ when different source deliveries are provided.

---

## 14. Design Decisions

A few important decisions shaped the implementation.

**Why DuckDB?**

The supplied data could be processed efficiently on a local machine. DuckDB provides analytical SQL capabilities without requiring a distributed cluster.

**Why `UNION ALL`?**

The initial and incremental datasets are combined without prematurely removing duplicate records. This allows the cleaning layer to identify and classify duplicates explicitly.

**Why `trip_id`?**

It is the candidate business key used to identify individual trips and enforce uniqueness in the trusted fact table.

**Why retain records with missing community areas?**

A missing pickup or dropoff area does not necessarily invalidate the trip itself. The record remains available in the fact table, while pickup-area metrics exclude records without a valid pickup area.

**Why maintain separate initial and incremental processing paths?**

The initial load establishes the trusted model. Subsequent deliveries should not require rebuilding the entire fact table.

**Why refresh only affected weekly metrics?**

A late-arriving record may belong to an earlier reporting week. Refreshing affected week-area combinations maintains historical accuracy without replacing the complete weekly metrics table.

**Why quarantine instead of deleting invalid records?**

Quarantine preserves rejected records for investigation and possible reprocessing.

---

## 15. Current Scope and Future Improvements

The current implementation focuses on a reproducible local data engineering solution.

Potential improvements for a production environment include:

- Persistent diagnosis history across incremental batches.
- Automated conflict resolution using reliable source versioning or update timestamps.
- Schema evolution and schema enforcement.
- Structured logging and monitoring.
- Automated alerts and failure notifications.
- More comprehensive integration tests using an isolated test database.
- Cloud object storage and distributed processing for larger datasets.
- CI/CD integration for automated testing and deployment.
- Access control, data lineage and operational dashboards.

The current diagnosis outputs are staging-level outputs and are not designed as a cumulative historical investigation system.

---

## 16. Repository Contents and Reproducibility

The repository contains the pipeline implementation, SQL transformations, automated tests and documentation.

The following are intentionally excluded from version control:

- DuckDB database files.
- Python cache files.
- Environment files.
- Virtual environments.

Input datasets are supplied separately where required.

The generated `mobility.duckdb` database is created locally when the pipeline is executed.

---

## 17. Conclusion

This project demonstrates an end-to-end data engineering workflow for processing initial and incremental mobility data.

It covers source ingestion, staging, deduplication, data quality, quarantine handling, dimensional modelling, incremental processing, batch tracking, weekly aggregations and automated validation.

The primary objective was to build a solution that is reproducible, understandable and reliable, while keeping the architecture simple enough to run locally.

The implementation also provides a foundation for extending the pipeline to a larger production environment as data volumes and operational requirements grow.
