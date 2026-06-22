import nfl_data_py as nfl
from nfl_analytics.database import get_connection


def load_play_by_play(start_year: int = 2024, end_year: int = 2025) -> None:
    """ Build a list of seasons.
        Download play-by-play data for those seasons.
        Open the DuckDB database.
        Temporarily register the pandas DF with DuckDB.
        Create or replace the permanent pbp table from that DataFrame.
        Count how many rows were loaded.
        Print the result."""
    seasons = list(range(start_year, end_year + 1))

    print(f"Loading play-by-play data for seasons: {seasons}")
    pbp = nfl.import_pbp_data(seasons)

    conn = get_connection()
    try:
        conn.register("pbp_df", pbp)

        conn.execute("""
            CREATE OR REPLACE TABLE pbp AS
            SELECT *
            FROM pbp_df
        """)

        row_count = conn.execute("SELECT COUNT(*) FROM pbp").fetchone()[0]
        print(f"Loaded {row_count:,} rows into table: pbp")
    finally:
        conn.close()


if __name__ == "__main__":
    load_play_by_play(2024, 2025)