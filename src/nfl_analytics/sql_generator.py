from typing import Protocol


class SQLGenerator(Protocol):
    def generate_sql(self, question: str, schema_summary: str) -> str:
        pass


class FakeSQLGenerator:
    def generate_sql(self, question: str, schema_summary: str) -> str:
        raise NotImplementedError(
            "SQL generation not wired in yet."
        )