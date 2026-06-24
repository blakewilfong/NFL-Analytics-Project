import pandas as pd

from nfl_analytics.query_runner import QueryRunner
from nfl_analytics.schema import SchemaService
from nfl_analytics.sql_generator import SQLGenerator
from nfl_analytics.sql_validator import SQLValidator


class QuestionEngine:
    def __init__(
        self,
        schema_service: SchemaService,
        sql_generator: SQLGenerator,
        sql_validator: SQLValidator,
        query_runner: QueryRunner,
    ):
        self.schema_service = schema_service
        self.sql_generator = sql_generator
        self.sql_validator = sql_validator
        self.query_runner = query_runner

    def answer(self, question: str) -> pd.DataFrame:
        schema_summary = self.schema_service.build_schema_summary()

        sql = self.sql_generator.generate_sql(
            question=question,
            schema_summary=schema_summary,
        )

        validation = self.sql_validator.validate(sql)

        if not validation.is_valid:
            raise ValueError(f"Generated SQL was rejected: {validation.message}")

        return self.query_runner.run(sql)