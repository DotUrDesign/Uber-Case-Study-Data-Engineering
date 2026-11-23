# I am calculating - 
# Cross-dataset duplication(initial_cnt > 0 and incremental_cnt > 0) => the trip_id is duplicated in both initial load and incremental load 
# Within-incremental duplicates(incremental_cnt > 1) => the trip_id is duplicated in only incremental load
# Within-initial duplicates(initial_cnt > 1) => the trip_id is duplicated in only initial load
# Getting duplicate trip ids
# Getting duplicate excess rows - one trip_id should only occur once, rest all are part of duplicate records

import duckdb


def classify_duplicates():

    con = duckdb.connect("mobility.duckdb")

    try:
        result = con.sql("""
            WITH duplicate_groups AS (
                SELECT
                    trip_id,
                    COUNT(*) AS occurrence_count,

                    COUNT(*) FILTER (
                        WHERE source_dataset = 'initial'
                    ) AS initial_count,

                    COUNT(*) FILTER (
                        WHERE source_dataset = 'incremental'
                    ) AS incremental_count

                FROM staging.trips_union
                GROUP BY trip_id
                HAVING COUNT(*) > 1
            )

            SELECT
                CASE
                    WHEN initial_count > 0
                     AND incremental_count > 0
                        THEN 'Cross-dataset duplicate'

                    WHEN incremental_count > 1
                        THEN 'Within-incremental duplicate'

                    WHEN initial_count > 1
                        THEN 'Within-initial duplicate'
                END AS duplicate_type,

                COUNT(*) AS duplicate_trip_ids,
                SUM(occurrence_count - 1)
                    AS duplicate_excess_rows

            FROM duplicate_groups
            GROUP BY 1
            ORDER BY 1
        """).df()

        print("Duplicate classification:")
        print(result.to_string(index=False))

    finally:
        con.close()


if __name__ == "__main__":
    classify_duplicates()
