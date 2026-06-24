import nfl_data_py as nfl
from nfl_analytics.data.database import DB_PATH, get_connection


def load_play_by_play(start_year: int = 2024, end_year: int = 2025) -> None:
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

        conn.execute("CHECKPOINT")
    finally:
        conn.close()

    size_bytes = DB_PATH.stat().st_size
    size_mb = size_bytes / (1024 ** 2)
    size_gb = size_bytes / (1024 ** 3)

    print(f"Database size: {size_bytes:,} bytes")
    print(f"Database size: {size_mb:.2f} MB")
    print(f"Database size: {size_gb:.4f} GB")


if __name__ == "__main__":
    load_play_by_play(1999, 2025)