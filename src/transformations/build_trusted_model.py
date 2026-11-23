
import duckdb
from pathlib import Path


def build_trusted_model():

    con = duckdb.connect("mobility.duckdb")

    try:
        # Attach source database for community area reference
        con.execute("""
            ATTACH 'mobility_exercise.duckdb'
            AS source_db (READ_ONLY)
        """)

        # Execute SQL file
        sql_path = Path("sql/create_trusted_model.sql")

        sql_script = sql_path.read_text(encoding="utf-8")

        con.execute(sql_script)

        # Display table counts
        result = con.sql("""
            SELECT 'dim_date' AS table_name,
                   COUNT(*) AS total_records
            FROM analytics.dim_date

            UNION ALL

            SELECT 'dim_community_area',
                   COUNT(*)
            FROM analytics.dim_community_area

            UNION ALL

            SELECT 'fact_trips',
                   COUNT(*)
            FROM analytics.fact_trips
        """).df()

        print("Trusted dimensional model created!")
        print(result.to_string(index=False))

        con.execute("DETACH source_db")

    finally:
        con.close()


if __name__ == "__main__":
    build_trusted_model()
