import pandas as pd
from duckdb import DuckDBPyConnection


class QueryRunner:
    def __init__(self, conn: DuckDBPyConnection):
        self.conn = conn

    def run(self, sql: str) -> pd.DataFrame:
        return self.conn.execute(sql).fetchdf()