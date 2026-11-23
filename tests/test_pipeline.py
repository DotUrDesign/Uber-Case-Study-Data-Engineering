
from pathlib import Path

import duckdb
import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_ROOT / "mobility.duckdb"


@pytest.fixture
def con():
    connection = duckdb.connect(str(DB_PATH), read_only=True)
    yield connection
    connection.close()


def test_fact_trip_ids_are_unique(con):
    total, unique_ids = con.execute("""
        SELECT
            COUNT(*),
            COUNT(DISTINCT trip_id)
        FROM analytics.fact_trips
    """).fetchone()

    assert total == unique_ids


def test_fact_trips_have_valid_timestamps(con):
    invalid_count = con.execute("""
        SELECT COUNT(*)
        FROM analytics.fact_trips
        WHERE trip_end_timestamp < trip_start_timestamp
    """).fetchone()[0]

    assert invalid_count == 0


def test_invalid_records_are_quarantined(con):
    result = con.execute("""
        SELECT COUNT(*)
        FROM ops.quarantine_records
        WHERE rejection_reason = 'END_BEFORE_START'
    """).fetchone()[0]

    assert result == 20


def test_weekly_metric_grain_is_unique(con):
    duplicate_count = con.execute("""
        SELECT COUNT(*)
        FROM (
            SELECT
                week_start_date,
                pickup_community_area_key
            FROM analytics.fact_weekly_mobility_metrics
            GROUP BY
                week_start_date,
                pickup_community_area_key
            HAVING COUNT(*) > 1
        ) duplicates
    """).fetchone()[0]

    assert duplicate_count == 0


def test_weekly_metrics_match_fact_trips(con):
    differences = con.execute("""
        WITH expected AS (
            SELECT
                d.week_start_date,
                t.pickup_community_area_key,

                COUNT(DISTINCT t.trip_id) AS trip_volume,

                SUM(t.trip_total) AS total_trip_price,

                COUNT(t.trip_total) AS price_observation_count,

                ROUND(
                    SUM(t.trip_total) /
                    NULLIF(COUNT(t.trip_total), 0),
                    2
                ) AS average_trip_price,

                COUNT(*) FILTER (
                    WHERE t.shared_trip_match = TRUE
                ) AS matched_trip_count,

                COUNT(*) FILTER (
                    WHERE t.shared_trip_match IS NOT NULL
                ) AS eligible_trip_count,

                ROUND(
                    100.0 * COUNT(*) FILTER (
                        WHERE t.shared_trip_match = TRUE
                    ) /
                    NULLIF(
                        COUNT(*) FILTER (
                            WHERE t.shared_trip_match IS NOT NULL
                        ), 0
                    ),
                    2
                ) AS shared_trip_rate

            FROM analytics.fact_trips t
            JOIN analytics.dim_date d
                ON t.pickup_date_key = d.date_key

            WHERE t.pickup_community_area_key IS NOT NULL

            GROUP BY
                d.week_start_date,
                t.pickup_community_area_key
        ),

        expected_minus_actual AS (
            SELECT * FROM expected
            EXCEPT
            SELECT * FROM analytics.fact_weekly_mobility_metrics
        ),

        actual_minus_expected AS (
            SELECT * FROM analytics.fact_weekly_mobility_metrics
            EXCEPT
            SELECT * FROM expected
        )

        SELECT
            (SELECT COUNT(*) FROM expected_minus_actual)
            +
            (SELECT COUNT(*) FROM actual_minus_expected)
    """).fetchone()[0]

    assert differences == 0


def test_initial_pipeline_is_completed(con):
    result = con.execute("""
        SELECT initial_load_completed
        FROM ops.pipeline_state
        WHERE pipeline_name = 'trusted_mobility_metrics'
    """).fetchone()

    assert result is not None
    assert result[0] is True


def test_last_successful_batch_is_successful(con):
    result = con.execute("""
        SELECT b.batch_status
        FROM ops.pipeline_state p
        JOIN ops.batch_log b
            ON p.last_successful_batch_id = b.batch_id
        WHERE p.pipeline_name = 'trusted_mobility_metrics'
    """).fetchone()

    assert result is not None
    assert result[0] == "SUCCESS"


def test_fact_trips_have_no_missing_pickup_area(con):
    missing_count = con.execute("""
        SELECT COUNT(*)
        FROM analytics.fact_trips
        WHERE pickup_community_area_key IS NULL
    """).fetchone()[0]

    assert missing_count == 0
