import duckdb


def get_connection():
    return duckdb.connect("mobility.duckdb")


def create_schemas(con):
    schemas = [
        "raw",  # original source data
        "staging",  # cleansed and validated data
        "trusted",  # Business ready trip data
        "analytics",  # fact and dimension tbls
        "ops"   # pipeline execution & operational metadata
    ]

    for schema in schemas:
        con.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")

    print("Database schemas created successfully!")


def main():
    con = get_connection()

    try:
        create_schemas(con)

        result = con.sql("""
            SELECT schema_name
            FROM information_schema.schemata
            WHERE schema_name NOT IN ('information_schema', 'main', 'pg_catalog')
            ORDER BY schema_name
        """).df()

        print("\nAvailable schemas:")
        print(result)

    finally:
        con.close()


if __name__ == "__main__":
    main()
