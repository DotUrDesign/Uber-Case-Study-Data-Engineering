
import duckdb
from pathlib import Path


def build_weekly_metrics():

    con = duckdb.connect("mobility.duckdb")

    try:
        sql_path = Path("sql/create_weekly_metrics.sql")

        sql_script = sql_path.read_text(encoding="utf-8")

        con.execute(sql_script)

        result = con.sql("""
            SELECT
                COUNT(*) AS total_rows,

                SUM(trip_volume) AS total_trips,

                SUM(price_observation_count) AS priced_trips,

                ROUND(SUM(total_trip_price), 2) AS total_trip_price,

                ROUND(
                    SUM(total_trip_price) /
                    NULLIF(SUM(price_observation_count), 0),
                    2
                ) AS overall_average_trip_price,

                SUM(matched_trip_count) AS matched_trips,

                SUM(eligible_trip_count) AS eligible_shared_trips,

                ROUND(
                    100.0 * SUM(matched_trip_count) /
                    NULLIF(SUM(eligible_trip_count), 0),
                    2
                ) AS overall_shared_trip_rate

            FROM analytics.fact_weekly_mobility_metrics
        """).df()

        print("Weekly metrics created successfully!")
        print(result.to_string(index=False))

    finally:
        con.close()


if __name__ == "__main__":
    build_weekly_metrics()
