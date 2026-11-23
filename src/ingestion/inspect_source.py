
import duckdb


def inspect_source_database():

    # Connect to the original database in read-only mode
    con = duckdb.connect(
        "mobility_exercise.duckdb",
        read_only=True
    )

    try:
        # Retrieve all available schemas and tables
        result = con.sql("""
            SELECT
                table_schema,
                table_name
            FROM information_schema.tables
            WHERE table_schema NOT IN (
                'information_schema',
                'pg_catalog'
            )
            ORDER BY table_schema, table_name
        """).df()

        print("Tables available in source database:")
        print(result.to_string(index=False))

    finally:
        con.close()


if __name__ == "__main__":
    inspect_source_database()
