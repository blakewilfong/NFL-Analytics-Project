from nfl_analytics.data.database import get_connection
from nfl_analytics.data.query_runner import QueryRunner
from nfl_analytics.data.schema import SchemaService
from nfl_analytics.sql_validator import SQLValidator


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

        #dummy text for now
        sql = """
            SELECT
                season,
                COUNT(*) AS rows
            FROM pbp
            GROUP BY season
            ORDER BY season
            LIMIT 100
        """

        validation = validator.validate(sql)

        if not validation.is_valid:
            print(f"Rejected query: {validation.message}")
            return

        result = query_runner.run(sql)
        print(result)

    finally:
        conn.close()


if __name__ == "__main__":
    main()