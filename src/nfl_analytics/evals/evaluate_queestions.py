import os
import re
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from nfl_analytics.database import get_connection
from nfl_analytics.query_runner import QueryRunner
from nfl_analytics.question_engine import QuestionEngine
from nfl_analytics.schema import SchemaService
from nfl_analytics.sql_generator import OllamaSQLGenerator
from nfl_analytics.sql_validator import SQLValidator


@dataclass(frozen=True)
class EvalCase:
    case_id: str
    question: str
    focus: str


EVAL_CASES = [
    EvalCase(
        "Q01",
        "best quarterback on second down in 2025",
        "QB ranking, second down, avoid trick-play tiny samples",
    ),
    EvalCase(
        "Q02",
        "who were the top QBs by EPA on third down in 2024",
        "QB EPA ranking, third down",
    ),
    EvalCase(
        "Q03",
        "which quarterbacks had the best success rate on third and long in 2024",
        "QB success rate, third and long",
    ),
    EvalCase(
        "Q04",
        "best running back in 2025",
        "Ambiguous RB ranking, should not return LIMIT 1",
    ),
    EvalCase(
        "Q05",
        "who had the most rushing yards in 2025",
        "Rushing volume, yards_gained, play_type run",
    ),
    EvalCase(
        "Q06",
        "most efficient running backs on first down in 2024",
        "RB efficiency, first down, sample threshold",
    ),
    EvalCase(
        "Q07",
        "which offenses had the highest success rate in the red zone in 2024",
        "Team offense success rate, red zone",
    ),
    EvalCase(
        "Q08",
        "which teams had the best EPA per play in the red zone in 2025",
        "Team offense EPA, red zone",
    ),
    EvalCase(
        "Q09",
        "which defenses were best on third down in 2024",
        "Defense query, defteam, third down",
    ),
    EvalCase(
        "Q10",
        "which defenses allowed the worst EPA per play in 2025",
        "Defense allowed EPA, defteam, descending bad defenses",
    ),
    EvalCase(
        "Q11",
        "which teams used 13 personnel the most in 2025",
        "Personnel usage, 13 personnel",
    ),
    EvalCase(
        "Q12",
        "which teams were most effective using 13 personnel in 2025",
        "Personnel effectiveness, not just usage",
    ),
    EvalCase(
        "Q13",
        "which teams used 11 personnel the most in 2024",
        "Personnel usage, 11 personnel",
    ),
    EvalCase(
        "Q14",
        "best offenses out of 12 personnel in 2024",
        "Personnel effectiveness, 12 personnel",
    ),
    EvalCase(
        "Q15",
        "who were the best receivers by EPA in 2025",
        "Receiver ranking, receiver_player_name",
    ),
    EvalCase(
        "Q16",
        "which receivers had the most targets in 2024",
        "Receiver volume, target count",
    ),
    EvalCase(
        "Q17",
        "which QBs were best in the final two minutes of the fourth quarter in 2024",
        "Late game QB EPA, game_seconds_remaining",
    ),
    EvalCase(
        "Q18",
        "which offenses were best when trailing by 7 or more in 2025",
        "Game script, score_differential",
    ),
    EvalCase(
        "Q19",
        "which teams had the most explosive pass plays in 2024",
        "Explosive plays, pass, yards_gained threshold",
    ),
    EvalCase(
        "Q20",
        "which teams had the best EPA per run in 2025",
        "Team rushing EPA, play_type run",
    ),
]


RANKING_WORDS = {
    "best",
    "top",
    "highest",
    "most",
    "worst",
    "efficient",
    "effective",
    "leaders",
}


def normalize_sql(sql: str) -> str:
    return re.sub(r"\s+", " ", sql.lower()).strip()


def extract_limit(sql: str) -> int | None:
    match = re.search(r"\blimit\s+(\d+)\b", sql, flags=re.IGNORECASE)
    if not match:
        return None
    return int(match.group(1))


def contains_any(text: str, words: set[str]) -> bool:
    return any(word in text for word in words)


def has_count_threshold(sql: str) -> bool:
    normalized = normalize_sql(sql)
    return "having" in normalized and "count" in normalized


def lint_sql(question: str, sql: str, row_count: int) -> list[str]:
    warnings = []

    q = question.lower()
    s = normalize_sql(sql)
    limit = extract_limit(sql)

    is_ranking_question = contains_any(q, RANKING_WORDS)

    if "pbp_data" in s:
        warnings.append("Uses hallucinated table name pbp_data.")

    if "play_by_play" in s or "nfl_data" in s:
        warnings.append("Uses likely hallucinated table name.")

    if "play_type_nfl" in s:
        warnings.append("Uses play_type_nfl. Prefer play_type for basic pass/run filtering.")

    if "series_success" in s:
        warnings.append("Uses series_success. Prefer success for play-level success rate.")

    if "year(current_date" in s:
        warnings.append("Uses YEAR(CURRENT_DATE). Prefer explicit season from the question.")

    if "play_type = 'rushing'" in s or 'play_type = "rushing"' in s:
        warnings.append("Uses play_type = 'rushing'. Should use play_type = 'run'.")

    if "play_type = 'passing'" in s or 'play_type = "passing"' in s:
        warnings.append("Uses play_type = 'passing'. Should use play_type = 'pass'.")

    if limit is None:
        warnings.append("Missing LIMIT.")
    elif limit == 1:
        warnings.append("Uses LIMIT 1. Analytics rankings should show context, usually LIMIT 10.")
    elif is_ranking_question and limit < 5:
        warnings.append("Ranking query returns fewer than 5 rows.")

    if row_count == 0:
        warnings.append("Returned zero rows.")

    if is_ranking_question and 0 < row_count < 5:
        warnings.append("Ranking result has fewer than 5 rows.")

    qb_terms = {"quarterback", "qb", "passer", "passers"}
    if contains_any(q, qb_terms):
        if "passer_player_name" not in s:
            warnings.append("QB/passser question does not use passer_player_name.")
        if "play_type = 'pass'" not in s and 'play_type = "pass"' not in s:
            warnings.append("QB/passer ranking should filter play_type = 'pass'.")
        if "count" not in s:
            warnings.append("QB/passer ranking should include COUNT(*) as attempts.")
        if is_ranking_question and not has_count_threshold(sql):
            warnings.append("QB/passer ranking should include HAVING COUNT(*) threshold.")
        if "avg(epa)" not in s and "success rate" not in q and "success_rate" not in q:
            warnings.append("Best QB question should usually include AVG(epa).")

    rb_terms = {"running back", "rb", "rusher", "rushers", "rushing"}
    if contains_any(q, rb_terms):
        if "rusher_player_name" not in s and "posteam" not in s:
            warnings.append("Rushing player question should use rusher_player_name.")
        if "play_type = 'run'" not in s and 'play_type = "run"' not in s:
            warnings.append("Rushing question should filter play_type = 'run'.")
        if "rushing_yards" in s:
            warnings.append("Uses rushing_yards. Prefer SUM(yards_gained) with play_type = 'run'.")
        if "most rushing yards" in q and "sum(yards_gained)" not in s:
            warnings.append("Most rushing yards should usually use SUM(yards_gained).")
        if "best running back" in q and "epa" not in s:
            warnings.append("Best RB query should include EPA context, not only yards.")

    if "red zone" in q:
        if "yardline_100 <= 20" not in s and "yardline_100<=" not in s:
            warnings.append("Red zone question should use yardline_100 <= 20.")

    if "13 personnel" in q:
        for token in ["1 rb", "3 te", "1 wr"]:
            if token not in s:
                warnings.append(f"13 personnel query missing offense_personnel pattern: {token}.")

    if "12 personnel" in q:
        for token in ["1 rb", "2 te", "2 wr"]:
            if token not in s:
                warnings.append(f"12 personnel query missing offense_personnel pattern: {token}.")

    if "11 personnel" in q:
        for token in ["1 rb", "1 te", "3 wr"]:
            if token not in s:
                warnings.append(f"11 personnel query missing offense_personnel pattern: {token}.")

    if "offense" in q or "offenses" in q:
        if "posteam" not in s:
            warnings.append("Offense/team offense question should usually use posteam.")

    if "defense" in q or "defenses" in q:
        if "defteam" not in s:
            warnings.append("Defense question should usually use defteam.")

    if "success rate" in q:
        if "avg(success)" not in s and "sum(success)" not in s:
            warnings.append("Success rate question should use AVG(success) or SUM(success)/COUNT(*).")

    if "epa" in q or "effective" in q or "efficient" in q:
        if "epa" not in s:
            warnings.append("EPA/effectiveness question should include epa.")

    return warnings


def preview_dataframe(df: pd.DataFrame, max_rows: int = 10) -> str:
    if df.empty:
        return "Empty DataFrame"

    return df.head(max_rows).to_string(index=False)


def main() -> None:
    load_dotenv()

    model = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:14b")

    conn = get_connection()

    report_dir = Path("eval_reports")
    report_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = report_dir / f"eval_{timestamp}.md"

    summary_rows = []
    report_lines = [
        "# NFL Analytics LLM Evaluation Report",
        "",
        f"Model: `{model}`",
        f"Generated at: `{timestamp}`",
        "",
    ]

    try:
        schema_service = SchemaService(conn)
        allowed_tables = set(schema_service.get_tables())

        sql_generator = OllamaSQLGenerator(model=model)

        sql_validator = SQLValidator(
            allowed_tables=allowed_tables,
            max_limit=100,
        )

        query_runner = QueryRunner(conn)

        question_engine = QuestionEngine(
            schema_service=schema_service,
            sql_generator=sql_generator,
            sql_validator=sql_validator,
            query_runner=query_runner,
        )

        for case in EVAL_CASES:
            print(f"Running {case.case_id}: {case.question}")

            start_time = time.perf_counter()

            try:
                result = question_engine.answer(case.question)
                elapsed = time.perf_counter() - start_time

                row_count = len(result.data)
                warnings = lint_sql(
                    question=case.question,
                    sql=result.sql,
                    row_count=row_count,
                )

                status = "PASS" if not warnings else "REVIEW"

                summary_rows.append(
                    {
                        "case_id": case.case_id,
                        "status": status,
                        "warnings": len(warnings),
                        "rows": row_count,
                        "seconds": round(elapsed, 2),
                        "question": case.question,
                    }
                )

                report_lines.extend(
                    [
                        f"## {case.case_id}: {case.question}",
                        "",
                        f"Focus: {case.focus}",
                        "",
                        f"Status: **{status}**",
                        f"Rows returned: `{row_count}`",
                        f"Elapsed seconds: `{elapsed:.2f}`",
                        "",
                        "### Warnings",
                        "",
                    ]
                )

                if warnings:
                    for warning in warnings:
                        report_lines.append(f"- {warning}")
                else:
                    report_lines.append("- None")

                report_lines.extend(
                    [
                        "",
                        "### Generated SQL",
                        "",
                        "```sql",
                        result.sql,
                        "```",
                        "",
                        "### Result Preview",
                        "",
                        "```text",
                        preview_dataframe(result.data),
                        "```",
                        "",
                    ]
                )

            except Exception as e:
                elapsed = time.perf_counter() - start_time

                summary_rows.append(
                    {
                        "case_id": case.case_id,
                        "status": "FAIL",
                        "warnings": "",
                        "rows": "",
                        "seconds": round(elapsed, 2),
                        "question": case.question,
                    }
                )

                report_lines.extend(
                    [
                        f"## {case.case_id}: {case.question}",
                        "",
                        f"Focus: {case.focus}",
                        "",
                        "Status: **FAIL**",
                        f"Elapsed seconds: `{elapsed:.2f}`",
                        "",
                        "### Error",
                        "",
                        "```text",
                        str(e),
                        "```",
                        "",
                    ]
                )

        summary_df = pd.DataFrame(summary_rows)

        report_lines.insert(6, "## Summary")
        report_lines.insert(7, "")
        report_lines.insert(8, "```text")
        report_lines.insert(9, summary_df.to_string(index=False))
        report_lines.insert(10, "```")
        report_lines.insert(11, "")

        report_path.write_text("\n".join(report_lines), encoding="utf-8")

        print()
        print("Evaluation complete.")
        print(f"Report written to: {report_path}")
        print()
        print(summary_df.to_string(index=False))

    finally:
        conn.close()


if __name__ == "__main__":
    main()