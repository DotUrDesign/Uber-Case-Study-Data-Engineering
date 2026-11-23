
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
                ROUND(AVG(average_trip_price), 2)
                    AS avg_of_weekly_area_prices
            FROM analytics.fact_weekly_mobility_metrics
        """).df()

        print("Weekly metrics created successfully!")
        print(result.to_string(index=False))

    finally:
        con.close()


if __name__ == "__main__":
    build_weekly_metrics()
