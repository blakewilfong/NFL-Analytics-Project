from nfl_analytics.data.database import get_connection
from nfl_analytics.data.query_runner import QueryRunner
from nfl_analytics.data.schema import SchemaService
from nfl_analytics.validation.sql_validator import SQLValidator


def read_sql_statement() -> str | None:
    lines = []

    while True:
        prompt = "sql> " if not lines else "... "
        line = input(prompt)
        stripped = line.strip()

        if not lines and stripped.lower() in {"exit", "quit"}:
            return None

        if not stripped:
            continue

        lines.append(line)

        if stripped.endswith(";"):
            sql = "\n".join(lines)
            return sql.rstrip(";").strip()


def main() -> None:
    conn = get_connection()

    try:
        schema_service = SchemaService(conn)
        allowed_tables = set(schema_service.get_tables())

        validator = SQLValidator(
            allowed_tables=allowed_tables,
            max_limit=100,
        )

        query_runner = QueryRunner(conn)

        print("NFL Analytics SQL Console")
        print("Enter SQL ending with semicolon. Type 'exit' to quit.")
        print()

        while True:
            sql = read_sql_statement()

            if sql is None:
                break

            validation = validator.validate(sql)

            if not validation.is_valid:
                print(f"Rejected query: {validation.message}")
                continue

            result = query_runner.run(sql)
            print(result)

    finally:
        conn.close()


if __name__ == "__main__":
    main()