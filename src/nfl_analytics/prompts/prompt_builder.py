from nfl_analytics.prompts.column_metadata import build_column_metadata_summary
from nfl_analytics.prompts.domain_knowledge import DOMAIN_KNOWLEDGE
from nfl_analytics.prompts.prompt_examples import build_sql_examples
from nfl_analytics.prompts.prompt_rules import build_generation_rules, build_repair_rules


COLUMN_METADATA_SUMMARY = build_column_metadata_summary()
SQL_EXAMPLES_SUMMARY = build_sql_examples()


class PromptBuilder:
    def build_sql_prompt(self, question: str, schema_summary: str) -> str:
        return f"""
You convert NFL analytics questions into DuckDB SQL.

Rules:
{build_generation_rules()}

Column metadata:
{COLUMN_METADATA_SUMMARY}

Domain knowledge:
{DOMAIN_KNOWLEDGE}

Examples:
{SQL_EXAMPLES_SUMMARY}

Schema:
{schema_summary}

Question:
{question}

SQL:
""".strip()

    def build_sql_repair_prompt(
        self,
        question: str,
        schema_summary: str,
        rejected_sql: str,
        validation_error: str,
    ) -> str:
        return f"""
You generated invalid DuckDB SQL for an NFL analytics question.

Fix the SQL.

Rules:
{build_repair_rules()}

Column metadata:
{COLUMN_METADATA_SUMMARY}

Domain knowledge:
{DOMAIN_KNOWLEDGE}

Examples:
{SQL_EXAMPLES_SUMMARY}

Schema:
{schema_summary}

Question:
{question}

Rejected SQL:
{rejected_sql}

Validation error:
{validation_error}

Corrected SQL:
""".strip()