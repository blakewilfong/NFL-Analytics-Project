from dataclasses import dataclass

from sqlglot import exp

#shared information every rule can inspect

@dataclass(frozen=True)
class ValidationContext:
    sql: str
    statement: exp.Expression
    allowed_tables: set[str]
    max_limit: int