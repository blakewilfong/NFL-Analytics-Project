from pathlib import Path

import duckdb

DB_PATH = Path("db/nfl.duckdb")

def get_connection() -> duckdb.DuckDBPyConnection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(DB_PATH))