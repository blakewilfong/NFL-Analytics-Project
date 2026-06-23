from nfl_analytics.database import get_connection
from nfl_analytics.query_runner import QueryRunner
from nfl_analytics.schema import SchemaService
from nfl_analytics.sql_validator import SQLValidator


def main() -> None:
    conn = get_connection()

    try:
        schema_service = SchemaService(conn)
        query_runner = QueryRunner(conn)

        allowed_tables = set(schema_service.get_tables())
        validator = SQLValidator(allowed_tables)

        sql = """
            SELECT
                season,
                COUNT(*) AS rows
            FROM pbp
            GROUP BY season
            ORDER BY season
        """

        is_valid, message = validator.validate(sql)

        if not is_valid:
            print(f"Rejected query: {message}")
            return

        result = query_runner.run(sql)
        print(result)

    finally:
        conn.close()


if __name__ == "__main__":
    main()