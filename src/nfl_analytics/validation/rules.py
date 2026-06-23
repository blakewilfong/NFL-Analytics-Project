from abc import ABC, abstractmethod

from sqlglot import exp

from nfl_analytics.validation.context import ValidationContext
from nfl_analytics.validation.result import ValidationResult

# rules that sql_validator will run

class ValidationRule(ABC):
    @abstractmethod
    def validate(self, context: ValidationContext) -> ValidationResult:
        pass


class SelectOnlyRule(ValidationRule):
    def validate(self, context: ValidationContext) -> ValidationResult:
        if not isinstance(context.statement, (exp.Select, exp.Union)):
            return ValidationResult.fail("Only SELECT queries are allowed.")

        return ValidationResult.ok()


class AllowedTablesRule(ValidationRule):
    def validate(self, context: ValidationContext) -> ValidationResult:
        used_tables = {
            table.name
            for table in context.statement.find_all(exp.Table)
        }

        cte_names = {
            cte.alias
            for cte in context.statement.find_all(exp.CTE)
            if cte.alias
        }

        disallowed_tables = used_tables - context.allowed_tables - cte_names

        if disallowed_tables:
            return ValidationResult.fail(
                f"Query uses disallowed tables: {sorted(disallowed_tables)}"
            )

        return ValidationResult.ok()


class NoSelectStarRule(ValidationRule):
    def validate(self, context: ValidationContext) -> ValidationResult:
        for select in context.statement.find_all(exp.Select):
            for projection in select.expressions:
                if isinstance(projection, exp.Star):
                    return ValidationResult.fail("SELECT * is not allowed.")

                if isinstance(projection, exp.Column) and projection.name == "*":
                    return ValidationResult.fail("SELECT * is not allowed.")

        return ValidationResult.ok()


class LimitRequiredRule(ValidationRule):
    def validate(self, context: ValidationContext) -> ValidationResult:
        limit = context.statement.args.get("limit")

        if limit is None:
            return ValidationResult.fail("Queries must include a LIMIT.")

        return ValidationResult.ok()


class MaxLimitRule(ValidationRule):
    def validate(self, context: ValidationContext) -> ValidationResult:
        limit = context.statement.args.get("limit")

        if limit is None:
            return ValidationResult.ok()

        limit_value = limit.expression

        if not isinstance(limit_value, exp.Literal):
            return ValidationResult.fail("LIMIT must be a numeric literal.")

        try:
            value = int(limit_value.this)
        except ValueError:
            return ValidationResult.fail("LIMIT must be an integer.")

        if value > context.max_limit:
            return ValidationResult.fail(
                f"LIMIT cannot be greater than {context.max_limit}."
            )

        return ValidationResult.ok()