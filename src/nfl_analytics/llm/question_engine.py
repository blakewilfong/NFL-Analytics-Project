from dataclasses import dataclass

import pandas as pd

from nfl_analytics.data.query_runner import QueryRunner
from nfl_analytics.data.schema import SchemaService
from nfl_analytics.llm.sql_generator import SQLGenerator
from nfl_analytics.sql_validator import SQLValidator


@dataclass(frozen=True)
class QuestionResult:
    question: str
    sql: str
    data: pd.DataFrame


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

    def answer(self, question: str) -> QuestionResult:
        schema_summary = self.schema_service.build_schema_summary()

        sql = self.sql_generator.generate_sql(
            question=question,
            schema_summary=schema_summary,
        )

        max_attempts = 3
        last_validation_message = ""

        for attempt in range(max_attempts):
            validation = self.sql_validator.validate(sql)

            if validation.is_valid:
                data = self.query_runner.run(sql)

                return QuestionResult(
                    question=question,
                    sql=sql,
                    data=data,
                )

            last_validation_message = validation.message

            if not hasattr(self.sql_generator, "repair_sql"):
                break

            sql = self.sql_generator.repair_sql(
                question=question,
                schema_summary=schema_summary,
                rejected_sql=sql,
                validation_error=validation.message,
            )

        raise ValueError(
            f"Generated SQL was rejected after {max_attempts} attempts: "
            f"{last_validation_message}\n\nSQL:\n{sql}"
        )