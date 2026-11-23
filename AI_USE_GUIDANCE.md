# AI Use Guidance

## 1. AI Tools Used

Generative AI (ChatGPT) was used as an assistance tool during the development of this project.

It was used for:
- Discussing pipeline architecture and data engineering design decisions.
- Understanding DuckDB SQL and Python implementation approaches.
- Identifying potential data quality issues and duplicate-handling strategies.
- Debugging implementation errors.
- Designing automated validation tests.
- Improving project documentation.

## 2. How AI Assistance Was Applied

AI assistance was used across the following areas:

| Area | AI Assistance |
|---|---|
| Architecture | Discussed Raw, Staging, and Trusted data layers |
| Ingestion | Reviewed approaches for loading initial and incremental data |
| Data quality | Discussed duplicate detection, timestamp validation, and quarantine handling |
| Data modeling | Discussed business keys, dimensions, fact tables, and weekly metric grain |
| SQL and Python | Assisted with implementation and debugging |
| Testing | Helped design automated data quality and reconciliation tests |
| Documentation | Assisted in preparing README and project documentation |

## 3. Design Decisions and Independent Validation

AI-generated suggestions were treated as recommendations rather than authoritative answers.

Important implementation decisions were checked against the supplied data and actual pipeline results.

Examples:

- The business key was established as `trip_id`.
- Duplicate records were analyzed before implementing deduplication.
- The community area dimension was expanded to include distinct non-null pickup and dropoff area IDs observed in validated trip data, rather than relying only on the limited reference records.
- Missing dropoff area keys were investigated to distinguish genuine source nulls from unmatched dimension records.
- A deterministic full-refresh strategy was selected for the supplied inputs instead of introducing unnecessary orchestration or distributed processing infrastructure.

## 4. Validation Performed

The implementation was validated through:

1. Inspecting initial and incremental source data.
2. Analyzing duplicate records and overlaps between deliveries.
3. Checking invalid timestamp records.
4. Comparing source and trusted record counts.
5. Validating fact table uniqueness.
6. Checking weekly metric grain uniqueness.
7. Reconciling weekly metric trip counts with trusted fact records.
8. Executing the complete pipeline twice and comparing the results.
9. Running the automated pytest suite.

The automated test suite contains five tests, all of which passed during the final validation run.

## 5. Limitations and Risks Considered

During development, some initial assumptions required further investigation.

For example, the supplied community area reference data did not contain every area ID observed in trip records. The dimension-building logic was therefore adjusted to include all distinct non-null pickup and dropoff IDs observed in validated trip data.

Missing dropoff area keys were also investigated. The analysis showed that these corresponded to source null values rather than unmatched non-null area IDs.

The pipeline currently uses a deterministic full-refresh approach. A production implementation handling continuous deliveries would require additional mechanisms such as persistent ingestion state, incremental merge logic, monitoring, and recovery controls.

## 6. Human Responsibility

AI assistance did not replace validation or engineering judgment.

The final implementation, business rules, data quality checks, and execution results were reviewed against the supplied dataset and assignment requirements.

The developer remains responsible for the correctness, reliability, and maintainability of the submitted solution.