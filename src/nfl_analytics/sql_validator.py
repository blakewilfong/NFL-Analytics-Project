import sqlglot

from nfl_analytics.validation.context import ValidationContext
from nfl_analytics.validation.result import ValidationResult
from nfl_analytics.validation.rules import (
    AllowedTablesRule,
    LimitRequiredRule,
    MaxLimitRule,
    NoSelectStarRule,
    SelectOnlyRule,
    ValidationRule,
)

# parses SQL
# builds context
# runs rules
# returns first failure

class SQLValidator:
    def __init__(
        self,
        allowed_tables: set[str],
        max_limit: int = 100,
        rules: list[ValidationRule] | None = None,
    ):
        self.allowed_tables = allowed_tables
        self.max_limit = max_limit
        self.rules = rules or [
            SelectOnlyRule(),
            AllowedTablesRule(),
            NoSelectStarRule(),
            LimitRequiredRule(),
            MaxLimitRule(),
        ]

    def validate(self, sql: str) -> ValidationResult:
        try:
            statements = sqlglot.parse(sql, read="duckdb")
        except Exception as e:
            return ValidationResult.fail(f"SQL parse error: {e}")

        if len(statements) != 1:
            return ValidationResult.fail("Only one SQL statement is allowed.")

        context = ValidationContext(
            sql=sql,
            statement=statements[0],
            allowed_tables=self.allowed_tables,
            max_limit=self.max_limit,
        )

        for rule in self.rules:
            result = rule.validate(context)

            if not result.is_valid:
                return result

        return ValidationResult.ok()