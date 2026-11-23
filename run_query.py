import duckdb

con = duckdb.connect("mobility.duckdb")

query = """
SELECT
    COUNT(*) AS total_records,
    COUNT(DISTINCT trip_id) AS distinct_trip_ids,
    COUNT(*) FILTER (
        WHERE trip_id IS NULL
    ) AS null_trip_ids
FROM analytics.fact_trips;
"""

result = con.execute(query).fetchdf()

print(result)

con.close()