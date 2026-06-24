import os
import re
import time
from dataclasses import dataclass
from datetime import datetime

import pandas as pd
from dotenv import load_dotenv

from nfl_analytics.data.database import DB_PATH, get_connection
from nfl_analytics.data.query_runner import QueryRunner
from nfl_analytics.data.schema import SchemaService
from nfl_analytics.llm.sql_generator import OllamaSQLGenerator
from nfl_analytics.validation.sql_validator import SQLValidator


@dataclass(frozen=True)
class EvalCase:
    case_id: str
    question: str
    focus: str


@dataclass(frozen=True)
class ValidationFailure(Exception):
    message: str
    sql: str


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
    "efficiency",
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


def contains_phrase(text: str, phrase: str) -> bool:
    escaped = re.escape(phrase.lower())
    return re.search(rf"\b{escaped}\b", text.lower()) is not None


def contains_any_phrase(text: str, phrases: set[str]) -> bool:
    return any(contains_phrase(text, phrase) for phrase in phrases)


def has_count_threshold(sql: str) -> bool:
    normalized = normalize_sql(sql)
    return "having" in normalized and "count" in normalized


def has_play_type_value(sql: str, value: str) -> bool:
    s = normalize_sql(sql)
    return (
        f"play_type = '{value}'" in s
        or f'play_type = "{value}"' in s
        or f"play_type='{value}'" in s
        or f'play_type="{value}"' in s
    )


def has_personnel_pattern(sql: str, pattern: str) -> bool:
    return pattern.lower() in normalize_sql(sql)


def get_database_summary(conn) -> str:
    overview = conn.execute(
        """
        SELECT
            MIN(season) AS min_season,
            MAX(season) AS max_season,
            COUNT(*) AS total_rows,
            SUM(CASE WHEN season = 2024 THEN 1 ELSE 0 END) AS rows_2024,
            SUM(CASE WHEN season = 2025 THEN 1 ELSE 0 END) AS rows_2025
        FROM pbp
        """
    ).fetchdf()

    rows_by_season = conn.execute(
        """
        SELECT
            season,
            COUNT(*) AS rows
        FROM pbp
        GROUP BY season
        ORDER BY season
        """
    ).fetchdf()

    play_type_counts = conn.execute(
        """
        SELECT
            play_type,
            COUNT(*) AS rows
        FROM pbp
        GROUP BY play_type
        ORDER BY rows DESC
        LIMIT 20
        """
    ).fetchdf()

    return (
        "Database path:\n"
        f"{DB_PATH.resolve()}\n\n"
        "Overview:\n"
        + overview.to_string(index=False)
        + "\n\nRows by season:\n"
        + rows_by_season.to_string(index=False)
        + "\n\nTop play_type values:\n"
        + play_type_counts.to_string(index=False)
    )


def lint_sql(question: str, sql: str, row_count: int) -> list[str]:
    warnings = []

    q = question.lower()
    s = normalize_sql(sql)
    limit = extract_limit(sql)

    is_ranking_question = contains_any_phrase(q, RANKING_WORDS)

    qb_terms = {"quarterback", "quarterbacks", "qb", "qbs", "passer", "passers"}
    rb_terms = {
        "running back",
        "running backs",
        "rb",
        "rbs",
        "rusher",
        "rushers",
        "rushing",
    }
    receiver_terms = {"receiver", "receivers", "target", "targets"}

    if "pbp_data" in s:
        warnings.append("Uses hallucinated table name pbp_data.")

    if "play_by_play" in s or "nfl_data" in s:
        warnings.append("Uses likely hallucinated table name.")

    if "play_type_nfl" in s:
        warnings.append("Uses play_type_nfl. Prefer play_type for basic pass/run filtering.")

    if "series_success" in s:
        warnings.append("Uses series_success. Prefer success for play-level success rate.")

    if "series_result" in s:
        warnings.append("Uses series_result. Prefer down for down-based filtering.")

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

    if contains_any_phrase(q, qb_terms):
        if "passer_player_name" not in s:
            warnings.append("QB/passer question should use passer_player_name.")
        if not has_play_type_value(sql, "pass"):
            warnings.append("QB/passer ranking should filter play_type = 'pass'.")
        if "count(" not in s and "count(*)" not in s:
            warnings.append("QB/passer ranking should include COUNT(*) as attempts.")
        if is_ranking_question and not has_count_threshold(sql):
            warnings.append("QB/passer ranking should include HAVING COUNT(*) threshold.")
        if "avg(epa)" not in s and "epa" in q:
            warnings.append("QB EPA question should include AVG(epa).")
        if "best quarterback" in q and "avg(epa)" not in s and "success rate" not in q:
            warnings.append("Best QB question should usually include AVG(epa).")

    if contains_any_phrase(q, rb_terms):
        if "rusher_player_name" not in s and "posteam" not in s:
            warnings.append("Rushing player question should use rusher_player_name.")
        if not has_play_type_value(sql, "run"):
            warnings.append("Rushing question should filter play_type = 'run'.")
        if "rushing_yards" in s:
            warnings.append("Uses rushing_yards. Prefer SUM(yards_gained) with play_type = 'run'.")
        if "most rushing yards" in q and "sum(yards_gained)" not in s:
            warnings.append("Most rushing yards should usually use SUM(yards_gained).")
        if "best running back" in q and "epa" not in s:
            warnings.append("Best RB query should include EPA context, not only yards.")
        if is_ranking_question and "count(" not in s and "count(*)" not in s:
            warnings.append("RB/rushing rankings should include COUNT(*) as carries.")

    if contains_any_phrase(q, receiver_terms):
        if "receiver_player_name" not in s:
            warnings.append("Receiver question should use receiver_player_name.")
        if "receiver is not null" in s and "receiver_player_name is not null" not in s:
            warnings.append(
                "Receiver query filters receiver but should filter receiver_player_name IS NOT NULL."
            )
        if "receiver_player_name" in s and "receiver_player_name is not null" not in s:
            warnings.append("Receiver query should include receiver_player_name IS NOT NULL.")
        if "best receivers" in q and "epa" not in s:
            warnings.append("Best receiver by EPA question should include epa.")

    if "red zone" in q:
        if "yardline_100 <= 20" not in s and "yardline_100<=20" not in s:
            warnings.append("Red zone question should use yardline_100 <= 20.")

    if "third down" in q:
        if "down = 3" not in s and "down=3" not in s:
            warnings.append("Third down question should use down = 3.")

    if "second down" in q:
        if "down = 2" not in s and "down=2" not in s:
            warnings.append("Second down question should use down = 2.")

    if "first down" in q:
        if "down = 1" not in s and "down=1" not in s:
            warnings.append("First down question should use down = 1.")

    if "third and long" in q:
        if "ydstogo" not in s:
            warnings.append("Third-and-long question should include a ydstogo filter.")

    if "13 personnel" in q:
        expected_patterns = ["1 rb", "3 te", "1 wr"]
        for pattern in expected_patterns:
            if not has_personnel_pattern(sql, pattern):
                warnings.append(
                    f"13 personnel query missing offense_personnel pattern: {pattern}."
                )

        bad_patterns = ["%13%", "%wr13%", "%1 rb, 3 wr%"]
        for pattern in bad_patterns:
            if pattern in s:
                warnings.append(f"13 personnel query uses bad shorthand/pattern: {pattern}.")

    if "12 personnel" in q:
        expected_patterns = ["1 rb", "2 te", "2 wr"]
        for pattern in expected_patterns:
            if not has_personnel_pattern(sql, pattern):
                warnings.append(
                    f"12 personnel query missing offense_personnel pattern: {pattern}."
                )

        if "%12%" in s:
            warnings.append("12 personnel query uses bad shorthand pattern '%12%'.")

    if "11 personnel" in q:
        expected_patterns = ["1 rb", "1 te", "3 wr"]
        for pattern in expected_patterns:
            if not has_personnel_pattern(sql, pattern):
                warnings.append(
                    f"11 personnel query missing offense_personnel pattern: {pattern}."
                )

        if "%11%" in s:
            warnings.append("11 personnel query uses bad shorthand pattern '%11%'.")

    if "offense" in q or "offenses" in q:
        if "posteam" not in s:
            warnings.append("Offense/team offense question should usually use posteam.")

    if "defense" in q or "defenses" in q:
        if "defteam" not in s:
            warnings.append("Defense question should usually use defteam.")
        if "defense_personnel" in s and "personnel" not in q:
            warnings.append(
                "Defense question used defense_personnel, but should usually group by defteam."
            )

    if "success rate" in q:
        uses_success_rate = (
            "avg(success)" in s
            or "sum(success)" in s
            or "case when success" in s
        )
        if not uses_success_rate:
            warnings.append(
                "Success rate question should use AVG(success), SUM(success)/COUNT(*), "
                "or CASE WHEN success."
            )

    if "epa" in q or "effective" in q or "efficient" in q:
        if "epa" not in s:
            warnings.append("EPA/effectiveness question should include epa.")

    if "explosive pass" in q:
        if not has_play_type_value(sql, "pass"):
            warnings.append("Explosive pass query should filter play_type = 'pass'.")
        if "yards_gained" not in s and "air_yards" not in s:
            warnings.append(
                "Explosive pass query should include yards_gained or air_yards threshold."
            )

    if "trailing by 7" in q:
        if "score_differential" not in s:
            warnings.append("Trailing/leading question should use score_differential.")

    return warnings


def preview_dataframe(df: pd.DataFrame, max_rows: int = 10) -> str:
    if df.empty:
        return "Empty DataFrame"

    return df.head(max_rows).to_string(index=False)


def generate_valid_sql(
    question: str,
    schema_summary: str,
    sql_generator: OllamaSQLGenerator,
    sql_validator: SQLValidator,
    max_attempts: int = 3,
) -> str:
    sql = sql_generator.generate_sql(
        question=question,
        schema_summary=schema_summary,
    )

    last_validation_message = ""

    for attempt in range(max_attempts):
        validation = sql_validator.validate(sql)

        if validation.is_valid:
            return sql

        last_validation_message = validation.message

        sql = sql_generator.repair_sql(
            question=question,
            schema_summary=schema_summary,
            rejected_sql=sql,
            validation_error=validation.message,
        )

    raise ValidationFailure(
        message=(
            f"Generated SQL was rejected after {max_attempts} attempts: "
            f"{last_validation_message}"
        ),
        sql=sql,
    )


def add_case_report(
    report_lines: list[str],
    case: EvalCase,
    status: str,
    elapsed: float,
    warnings: list[str] | None = None,
    sql: str | None = None,
    data: pd.DataFrame | None = None,
    error: str | None = None,
) -> None:
    report_lines.extend(
        [
            f"## {case.case_id}: {case.question}",
            "",
            f"Focus: {case.focus}",
            "",
            f"Status: **{status}**",
            f"Elapsed seconds: `{elapsed:.2f}`",
            "",
        ]
    )

    if error:
        report_lines.extend(
            [
                "### Error",
                "",
                "```text",
                error,
                "```",
                "",
            ]
        )

    if warnings is not None:
        report_lines.extend(
            [
                "### Warnings",
                "",
            ]
        )

        if warnings:
            for warning in warnings:
                report_lines.append(f"- {warning}")
        else:
            report_lines.append("- None")

        report_lines.append("")

    if sql:
        report_lines.extend(
            [
                "### Generated SQL",
                "",
                "```sql",
                sql,
                "```",
                "",
            ]
        )

    if data is not None:
        report_lines.extend(
            [
                "### Result Preview",
                "",
                "```text",
                preview_dataframe(data),
                "```",
                "",
            ]
        )


def main() -> None:
    load_dotenv()

    model = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:14b")

    conn = get_connection()

    project_root = DB_PATH.parent.parent
    report_dir = project_root / "eval_reports"
    report_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = report_dir / f"eval_{timestamp}.md"

    summary_rows = []
    case_report_lines = []

    try:
        schema_service = SchemaService(conn)
        allowed_tables = set(schema_service.get_tables())

        if "pbp" not in allowed_tables:
            raise RuntimeError(
                "Could not find required table 'pbp'. "
                f"Connected tables: {sorted(allowed_tables)}. "
                f"Database path: {DB_PATH.resolve()}"
            )

        database_summary = get_database_summary(conn)

        schema_summary = schema_service.build_schema_summary()

        sql_generator = OllamaSQLGenerator(model=model)

        sql_validator = SQLValidator(
            allowed_tables=allowed_tables,
            max_limit=100,
        )

        query_runner = QueryRunner(conn)

        for case in EVAL_CASES:
            print(f"Running {case.case_id}: {case.question}")

            start_time = time.perf_counter()

            try:
                sql = generate_valid_sql(
                    question=case.question,
                    schema_summary=schema_summary,
                    sql_generator=sql_generator,
                    sql_validator=sql_validator,
                    max_attempts=3,
                )

                try:
                    data = query_runner.run(sql)
                    elapsed = time.perf_counter() - start_time

                    row_count = len(data)
                    warnings = lint_sql(
                        question=case.question,
                        sql=sql,
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

                    add_case_report(
                        report_lines=case_report_lines,
                        case=case,
                        status=status,
                        elapsed=elapsed,
                        warnings=warnings,
                        sql=sql,
                        data=data,
                    )

                except Exception as execution_error:
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

                    add_case_report(
                        report_lines=case_report_lines,
                        case=case,
                        status="FAIL",
                        elapsed=elapsed,
                        sql=sql,
                        error=str(execution_error),
                    )

            except ValidationFailure as validation_error:
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

                add_case_report(
                    report_lines=case_report_lines,
                    case=case,
                    status="FAIL",
                    elapsed=elapsed,
                    sql=validation_error.sql,
                    error=validation_error.message,
                )

            except Exception as unexpected_error:
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

                add_case_report(
                    report_lines=case_report_lines,
                    case=case,
                    status="FAIL",
                    elapsed=elapsed,
                    error=str(unexpected_error),
                )

        summary_df = pd.DataFrame(summary_rows)

        report_lines = [
            "# NFL Analytics LLM Evaluation Report",
            "",
            f"Model: `{model}`",
            f"Generated at: `{timestamp}`",
            "",
            "## Database Summary",
            "",
            "```text",
            database_summary,
            "```",
            "",
            "## Summary",
            "",
            "```text",
            summary_df.to_string(index=False),
            "```",
            "",
            *case_report_lines,
        ]

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

