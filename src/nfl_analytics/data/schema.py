from duckdb import DuckDBPyConnection


class SchemaService:
    def __init__(self, conn: DuckDBPyConnection):
        self.conn = conn

    def get_tables(self) -> list[str]:
        rows = self.conn.execute("SHOW TABLES").fetchall()
        return [row[0] for row in rows]

    def get_columns(self, table_name: str) -> list[dict[str, str]]:
        df = self.conn.execute(f"DESCRIBE {table_name}").fetchdf()

        return [
            {
                "name": row["column_name"],
                "type": row["column_type"],
            }
            for _, row in df.iterrows()
        ]

    def build_schema_summary(self) -> str:
        parts = []

        for table in self.get_tables():
            columns = self.get_columns(table)

            parts.append(f"Table: {table}")
            for col in columns:
                parts.append(f"  - {col['name']}: {col['type']}")

        return "\n".join(parts)