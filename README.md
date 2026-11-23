# Trusted Mobility Metrics

**Version:** 1.0.0  
**Project:** Mobility Data Engineering Exercise  
**Technology:** Python, DuckDB, SQL, Parquet, pytest

## 1. Project Overview

This project implements a reproducible data pipeline that processes initial and incremental mobility trip data and produces trusted, analytics-ready datasets and weekly mobility metrics.

The pipeline focuses on data correctness, reliability, data quality, deduplication, quarantine handling, and idempotent execution.

The implementation uses DuckDB for data processing and storage, Python for pipeline orchestration, Parquet for file-based data exchange, and pytest for automated validation.

## 2. Technology Stack

- Python 3.12
- DuckDB
- SQL
- Parquet
- Pandas
- PyArrow
- pytest

## 3. Project Architecture

The pipeline follows a layered data architecture:

```text
Initial DuckDB Data ──┐
                      ├──> Raw Layer
Incremental Parquet ──┘
                            |
                            v
                       Staging Layer
                            |
                            v
                  Validation & Deduplication
                       /          \
                      v            v
                Quarantine      Validated Data
                                    |
                                    v
                              Trusted Layer
                              /           \
                             v             v
                       Dimensions      Fact Trips
                                           |
                                           v
                                  Weekly Mobility Metrics
```

### Data layers

**Raw Layer**
- Loads initial trip records from the source DuckDB database.
- Loads incremental trip records from Parquet.
- Preserves the source records for downstream processing.

**Staging Layer**
- Combines initial and incremental records.
- Provides a consolidated dataset for validation and transformation.

**Validation and Deduplication**
- Uses `trip_id` as the business key.
- Removes identical duplicate records.
- Retains the initial source record when identical records overlap between initial and incremental deliveries.
- Quarantines records with invalid timestamps.
- Preserves valid records for trusted processing.

**Trusted Layer**
- Creates date and community area dimensions.
- Creates the trusted trip fact table.
- Produces weekly mobility metrics.

## 4. Repository Structure

```text
trusted-mobility-metrics/
│
├── data/
│   ├── raw/
│   │   └── incremental_trips.parquet
│   ├── quarantine/
│   │   └── rejected_trips.parquet
│   └── outputs/
│
├── docs/
│
├── sql/
│   ├── create_trusted_model.sql
│   └── create_weekly_metrics.sql
│
├── src/
│   ├── ingestion/
│   ├── transformations/
│   ├── quality/
│   └── pipeline.py
│
├── tests/
│   └── test_pipeline.py
│
├── requirements.txt
├── README.md
└── AI_USE_GUIDANCE.md
```

## 5. Setup and Execution

### Prerequisites

- Python 3.12 or compatible version
- The supplied `mobility_exercise.duckdb` database
- The supplied `incremental_trips.parquet` file

### Step 1: Create and activate a virtual environment

```bash
python -m venv venv
```

Windows:

```cmd
venv\Scripts\activate
```

### Step 2: Install dependencies

```bash
python -m pip install -r requirements.txt
```

### Step 3: Run the pipeline

From the project root:

```bash
python src/pipeline.py
```

The pipeline executes ingestion, staging, cleaning, trusted model creation, weekly metric generation, and data quality validation.

### Step 4: Run automated tests

```bash
python -m pytest tests -v
```

The test suite validates uniqueness, timestamp validity, quarantine handling, weekly grain uniqueness, and reconciliation between weekly metrics and trusted facts.

## 6. Data Model and Business Definitions

### Business key

`trip_id` is the business key used to identify an individual trip.

### Trusted tables

| Table | Description |
|---|---|
| `dim_date` | Date dimension |
| `dim_community_area` | Community area dimension |
| `fact_trips` | Validated and deduplicated trip-level records |
| `fact_weekly_mobility_metrics` | Weekly aggregated mobility metrics |

The community area dimension includes distinct non-null pickup and dropoff area IDs observed in the validated trip data. Available descriptive attributes are obtained from the supplied reference data.

### Weekly metric grain

One row represents:

`week_start_date + pickup_community_area_key`

Weeks start on Monday.

### Metric definitions

**Trip Volume**

Count of distinct valid trips:

`COUNT(DISTINCT trip_id)`

**Average Trip Price**

Average of `trip_total`:

`AVG(trip_total)`

Zero-value trip totals are retained in the calculation.

**Shared Trip Rate**

Percentage of valid trips where `shared_trip_match = TRUE`:

`Matched Shared Trips / Total Valid Trips × 100`

Trips with missing pickup community area are retained in the trusted fact table but excluded from pickup-area-level weekly aggregations.

## 7. Data Quality and Exception Handling

The pipeline applies the following checks and rules:

| Check | Handling |
|---|---|
| Duplicate `trip_id` | Identical duplicates are reduced to one record |
| Initial/incremental overlap | Identical records retain the initial source record |
| Conflicting duplicate records | Quarantine rather than silently choosing a record |
| End timestamp before start timestamp | Quarantine |
| Missing pickup area | Retain in fact table; exclude from area-level metrics |
| Missing dropoff area | Preserve source null |
| Weekly metric grain | Validate uniqueness of week and pickup area |

Quarantined records are exported to:

`data/quarantine/rejected_trips.parquet`

This provides visibility into rejected records rather than silently discarding them.

## 8. Idempotency and Incremental Data Handling

The pipeline uses a deterministic full-refresh strategy for the supplied initial and incremental input files.

- Raw tables are recreated from their source inputs.
- Staging data is rebuilt on every execution.
- Deduplication is performed using the business key.
- Quarantine and trusted tables are recreated.
- Weekly metrics are fully recomputed.

This ensures that rerunning the pipeline with the same input files produces the same trusted results without accumulating duplicate records.

Late-arriving records are included based on their trip start date. Since weekly metrics are recomputed, previously generated weeks are updated when late-arriving records are present.

This implementation does not maintain a persistent multi-delivery ingestion ledger or watermark-based checkpoint. A production implementation could introduce these mechanisms for scalable incremental processing.

## 9. Execution Results

The pipeline was executed successfully twice using the supplied input files.

| Validation | Result |
|---|---:|
| Initial records | 965,201 |
| Incremental records | 305,457 |
| Combined staging records | 1,270,658 |
| Deduplicated records | 1,270,508 |
| Quarantined records | 20 |
| Trusted fact records | 1,270,488 |
| Date dimension records | 57 |
| Community area dimension records | 78 |
| Weekly metric records | 34 |

The second execution produced the same record counts and validation results, confirming repeatability for the supplied inputs.

### Automated test results

All five automated tests passed:

- Fact trip IDs are unique.
- Trusted trip timestamps are valid.
- Invalid records are quarantined.
- Weekly metric grain is unique.
- Weekly metrics reconcile with trusted fact records.

## 10. Dataset Scope and Limitations

- The supplied dataset covers four selected Chicago community areas and does not represent complete citywide mobility activity.
- The community area dimension contains IDs observed in the supplied trip data; it should not be interpreted as a complete citywide reference dimension.
- The implementation uses a full-refresh strategy rather than a persistent incremental merge or watermark-based ingestion process.
- The pipeline is designed for local reproducibility and correctness, not distributed-scale processing.
- Source privacy protections and rounded values are retained as documented in the original data dictionary.

## 11. Production Scaling Considerations

For a production deployment, the following improvements could be introduced:

- Store raw and trusted datasets in cloud object storage such as Azure Data Lake Storage.
- Use Delta Lake or another transactional table format for reliable merge and update operations.
- Implement watermark-based incremental ingestion and persistent ingestion state.
- Introduce configurable schema enforcement and source-level validation.
- Add structured logging, monitoring, alerting, and operational metadata.
- Partition large datasets by appropriate date columns.
- Use distributed processing with Apache Spark when data volume requires it.
- Integrate automated testing and deployment through CI/CD pipelines.

These are potential production enhancements; they are not required dependencies of the current local implementation.

## 12. Reproducibility

The evaluator can reproduce the results by:

1. Installing the listed dependencies.
2. Placing the supplied source database and incremental Parquet file in their expected locations.
3. Running `python src/pipeline.py`.
4. Running `python -m pytest tests -v`.

The pipeline and tests are designed to run locally without requiring external orchestration infrastructure.