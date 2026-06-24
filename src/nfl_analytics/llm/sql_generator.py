import re
from typing import Protocol

import requests

from nfl_analytics.prompts.prompt_builder import PromptBuilder


class SQLGenerator(Protocol):
    def generate_sql(self, question: str, schema_summary: str) -> str:
        pass


class FakeSQLGenerator:
    def generate_sql(self, question: str, schema_summary: str) -> str:
        raise NotImplementedError("Real SQL generation is not wired in yet.")


class OllamaSQLGenerator:
    def __init__(
        self,
        model: str,
        base_url: str = "http://localhost:11434",
        timeout_seconds: int = 120,
        prompt_builder: PromptBuilder | None = None,
    ):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.prompt_builder = prompt_builder or PromptBuilder()

    def generate_sql(self, question: str, schema_summary: str) -> str:
        prompt = self.prompt_builder.build_sql_prompt(
            question=question,
            schema_summary=schema_summary,
        )

        response = requests.post(
            f"{self.base_url}/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0,
                },
            },
            timeout=self.timeout_seconds,
        )

        response.raise_for_status()

        raw_text = response.json().get("response", "")
        return self._clean_sql(raw_text)

    def repair_sql(
        self,
        question: str,
        schema_summary: str,
        rejected_sql: str,
        validation_error: str,
    ) -> str:
        prompt = self.prompt_builder.build_sql_repair_prompt(
            question=question,
            schema_summary=schema_summary,
            rejected_sql=rejected_sql,
            validation_error=validation_error,
        )

        response = requests.post(
            f"{self.base_url}/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0,
                },
            },
            timeout=self.timeout_seconds,
        )

        response.raise_for_status()

        raw_text = response.json().get("response", "")
        return self._clean_sql(raw_text)

    def _clean_sql(self, text: str) -> str:
        sql = text.strip()

        fenced_match = re.search(
            r"```(?:sql)?\s*(.*?)```",
            sql,
            flags=re.IGNORECASE | re.DOTALL,
        )

        if fenced_match:
            sql = fenced_match.group(1).strip()
        else:
            select_match = re.search(
                r"\b(WITH|SELECT)\b.*?(;|$)",
                sql,
                flags=re.IGNORECASE | re.DOTALL,
            )

            if select_match:
                sql = select_match.group(0).strip()

        if sql.endswith(";"):
            sql = sql[:-1].strip()

        return sql