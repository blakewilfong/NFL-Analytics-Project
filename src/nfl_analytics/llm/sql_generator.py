import re
from typing import Protocol

import requests

from nfl_analytics.prompts.prompt_builder import PromptBuilder


class SQLGenerator(Protocol):
    def generate_sql(self, question: str, schema_summary: str) -> str:
        pass

    def repair_sql(
            self,
            question: str,
            schema_summary: str,
            rejected_sql: str,
            validation_error: str,
    ) -> str:
        pass



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


    def _strip_sql_comments(self, sql: str) -> str:
        cleaned_chars = []

        in_single_quote = False
        in_double_quote = False
        in_line_comment = False
        in_block_comment = False

        i = 0

        while i < len(sql):
            current_char = sql[i]
            next_char = sql[i + 1] if i + 1 < len(sql) else ""

            if in_line_comment:
                if current_char == "\n":
                    in_line_comment = False
                    cleaned_chars.append(current_char)
                i += 1
                continue

            if in_block_comment:
                if current_char == "*" and next_char == "/":
                    in_block_comment = False
                    i += 2
                else:
                    i += 1
                continue

            if not in_single_quote and not in_double_quote:
                if current_char == "-" and next_char == "-":
                    in_line_comment = True
                    i += 2
                    continue

                if current_char == "/" and next_char == "*":
                    in_block_comment = True
                    i += 2
                    continue

            cleaned_chars.append(current_char)

            if current_char == "'" and not in_double_quote:
                if in_single_quote and next_char == "'":
                    cleaned_chars.append(next_char)
                    i += 2
                    continue

                in_single_quote = not in_single_quote

            elif current_char == '"' and not in_single_quote:
                if in_double_quote and next_char == '"':
                    cleaned_chars.append(next_char)
                    i += 2
                    continue

                in_double_quote = not in_double_quote

            i += 1

        return "".join(cleaned_chars).strip()

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

        sql = self._strip_sql_comments(sql)

        if sql.endswith(";"):
            sql = sql[:-1].strip()

        return sql