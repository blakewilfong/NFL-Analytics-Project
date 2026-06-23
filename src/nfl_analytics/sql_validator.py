import sqlglot
from sqlglot import exp

class SQLValidator:
    def __init__(self, allowed_tables: set[str]):
        self.allowed_tables = allowed_tables

    def validate(self, sql: str) -> tuple[bool, str]:
        try:
            statements = sqlglot.parse(sql, read="duckdb")
        except Exception as e:
            return False, f"SQL parse error: {e}"

        if len(statements) != 1:
            return False, "Only one SQL statement is allowed."

        statement = statements[0]

        if not isinstance(statement, (exp.Select, exp.Union)):
            return False, "Only SELECT queries are allowed."

        used_tables = {
            table.name
            for table in statement.find_all(exp.Table)
        }

        disallowed_tables = used_tables - self.allowed_tables
        if disallowed_tables:
            return False, f"Query uses disallowed tables: {sorted(disallowed_tables)}"

        return True, "SQL is valid."