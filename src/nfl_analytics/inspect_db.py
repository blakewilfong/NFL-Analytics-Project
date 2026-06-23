from nfl_analytics.database import get_connection


def main() -> None:
    conn = get_connection()

    print("\nTables:")
    print(conn.execute("SHOW TABLES").fetchdf())

    print("\nSchema for pbp:")
    print(conn.execute("DESCRIBE pbp").fetchdf())

    print("\nFirst 10 rows:")
    print(conn.execute("SELECT * FROM pbp LIMIT 10").fetchdf())

    print("\nRow count:")
    print(conn.execute("SELECT COUNT(*) AS row_count FROM pbp").fetchdf())

    conn.close()


if __name__ == "__main__":
    main()