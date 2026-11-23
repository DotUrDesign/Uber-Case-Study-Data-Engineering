# AI Use Guidance

## Overview

ChatGPT was used as a supporting tool throughout the development of this project. It helped evaluate technical approaches, translate requirements into implementation logic, troubleshoot issues, and support testing.

The business requirements, project objectives, and expected pipeline behaviour were defined through my understanding and analysis of the case study. ChatGPT assisted in implementing and validating those requirements.

## Areas Where AI Was Used

### 1. Technology Selection and Design Decisions

ChatGPT helped evaluate technology options and prioritize tools based on the project's requirements, complexity, and scale.

Key decisions included:

- **DuckDB:** Selected as a lightweight analytical database that could handle the project's SQL-based transformations without requiring a separate database server.
- **Python and SQL:** Used for ingestion, transformations, validation, and pipeline orchestration.
- **Parquet:** Used as the storage format for efficient analytical data processing.
- **Pytest:** Used to automate pipeline and data quality checks.

Alternative technologies such as Apache Spark and dedicated orchestration platforms were considered less necessary for this case study, as they would introduce additional infrastructure and complexity without providing significant benefits for the current requirements.

### 2. Implementation and Technical Problem-Solving

ChatGPT assisted with:

- Translating pipeline requirements into Python and SQL implementations.
- Developing reusable staging and transformation logic.
- Implementing incremental loading, duplicate classification, and conflict handling.
- Designing batch tracking and idempotency mechanisms.
- Troubleshooting implementation issues and reviewing alternative approaches.

### 3. Scenario Identification and Test Design

The business scenarios and expected outcomes were identified through project analysis. ChatGPT helped translate these scenarios into implementation logic and validation checks.

Examples include:

- Handling duplicate records within and across data sources.
- Identifying new, identical, and conflicting incremental records.
- Handling missing geographical attributes.
- Quarantining records with invalid timestamps.
- Retaining and diagnosing duration discrepancies.
- Processing late-arriving records and refreshing affected weekly metrics.
- Preventing successful batches from being processed again.

### 4. Testing and Validation

ChatGPT assisted in developing and reviewing SQL validation queries and Pytest test cases.

The validation covered:

- Uniqueness of trip records.
- Timestamp validity.
- Quarantine of invalid records.
- Uniqueness of weekly metric records.
- Reconciliation of aggregated metrics with the trusted fact table.
- Pipeline state and batch execution status.

## Review and Responsibility

AI-generated suggestions and code were reviewed against the project requirements and expected business behaviour. The pipeline was executed locally, database outputs were inspected, and automated tests were run to validate the implementation.

Final decisions regarding project requirements, technical choices, implementation review, and validation remained my responsibility.

## Summary

ChatGPT was used as a technical assistant across technology evaluation, solution design, implementation, troubleshooting, and testing. It helped accelerate development while keeping the solution aligned with the requirements and avoiding unnecessary technical complexity.