
from nfl_analytics.column_metadata import build_column_metadata_summary
from nfl_analytics.domain_knowledge import DOMAIN_KNOWLEDGE

SQL_EXAMPLES = """
Example 1:
Question: best quarterback on second down in 2025
SQL:
SELECT
    passer_player_name AS quarterback,
    COUNT(*) AS attempts,
    ROUND(AVG(epa), 3) AS avg_epa,
    ROUND(SUM(epa), 3) AS total_epa
FROM pbp
WHERE
    season = 2025
    AND down = 2
    AND play_type = 'pass'
    AND passer_player_name IS NOT NULL
    AND epa IS NOT NULL
GROUP BY passer_player_name
HAVING COUNT(*) >= 50
ORDER BY avg_epa DESC
LIMIT 10

Example 2:
Question: who were the best quarterbacks by average EPA on third down in 2024
SQL:
SELECT
    passer_player_name AS quarterback,
    COUNT(*) AS attempts,
    ROUND(AVG(epa), 3) AS avg_epa,
    ROUND(SUM(epa), 3) AS total_epa
FROM pbp
WHERE
    season = 2024
    AND down = 3
    AND play_type = 'pass'
    AND passer_player_name IS NOT NULL
    AND epa IS NOT NULL
GROUP BY passer_player_name
HAVING COUNT(*) >= 50
ORDER BY avg_epa DESC
LIMIT 10

Example 3:
Question: which teams used 13 personnel the most in 2025
SQL:
SELECT
    posteam,
    COUNT(*) AS plays
FROM pbp
WHERE
    season = 2025
    AND offense_personnel LIKE '%1 RB%'
    AND offense_personnel LIKE '%3 TE%'
    AND offense_personnel LIKE '%1 WR%'
    AND posteam IS NOT NULL
GROUP BY posteam
ORDER BY plays DESC
LIMIT 10

Example 4:
Question: which teams were most effective using 13 personnel in 2025
SQL:
SELECT
    posteam,
    COUNT(*) AS plays,
    ROUND(AVG(epa), 3) AS avg_epa,
    ROUND(SUM(epa), 3) AS total_epa,
    ROUND(AVG(success), 3) AS success_rate
FROM pbp
WHERE
    season = 2025
    AND offense_personnel LIKE '%1 RB%'
    AND offense_personnel LIKE '%3 TE%'
    AND offense_personnel LIKE '%1 WR%'
    AND play_type IN ('run', 'pass')
    AND posteam IS NOT NULL
    AND epa IS NOT NULL
GROUP BY posteam
HAVING COUNT(*) >= 20
ORDER BY avg_epa DESC
LIMIT 10

Example 5:
Question: which offenses had the highest success rate in the red zone in 2024
SQL:
SELECT
    posteam AS offense,
    COUNT(*) AS plays,
    ROUND(AVG(success), 3) AS success_rate,
    ROUND(AVG(epa), 3) AS avg_epa
FROM pbp
WHERE
    season = 2024
    AND yardline_100 <= 20
    AND play_type IN ('run', 'pass')
    AND posteam IS NOT NULL
    AND success IS NOT NULL
GROUP BY posteam
HAVING COUNT(*) >= 50
ORDER BY success_rate DESC
LIMIT 10
""".strip()

COLUMN_METADATA_SUMMARY = build_column_metadata_summary()

class PromptBuilder:
    def build_sql_prompt(self, question: str, schema_summary: str) -> str:
        return f"""
You convert NFL analytics questions into DuckDB SQL.

Critical output rules:
- Your entire response must be only one SQL query.
- The first word of your response must be SELECT or WITH.
- Do not include explanations.
- Do not include markdown.
- Do not include code fences.
- Do not include comments.
- Write exactly one read-only query.
- Always include a LIMIT.
- Never use SELECT *.
- Use only the provided schema.
- The only valid table name is pbp.
- Never use pbp_data, play_by_play, nfl_data, games, teams, players, or any table not shown in the schema.

Interpretation rules:
- Prioritize the main analytical intent of the question.
- If the question asks who was best, most effective, or most successful, rank by an effectiveness metric, not just volume.
- Include volume as context using COUNT(*), but do not sort by volume unless the user asks who used something most often.
- For EPA questions, include AVG(epa), SUM(epa), and COUNT(*).
- For success rate questions, use AVG(success).
- For rankings, always include sample size using COUNT(*).
- For player rankings, use a HAVING COUNT(*) threshold.
- For team rankings, use a HAVING COUNT(*) threshold when appropriate.
- Never use LIMIT 1.
- If the user asks for "best", "top", "highest", "most", or a ranking, return at least 5 rows.
- Use LIMIT 10 by default for rankings.
- If the user explicitly asks for one result, still return LIMIT 5 unless they say "only one row" or "exactly one".

Quarterback query rules:
- For quarterback or QB passing questions, group by passer_player_name.
- For QB rankings, always filter play_type = 'pass'.
- For QB rankings, always include passer_player_name IS NOT NULL.
- For QB EPA rankings, always include epa IS NOT NULL.
- For QB rankings, always include COUNT(*) AS attempts.
- For QB rankings, always include HAVING COUNT(*) >= 50 unless the user specifies a different threshold.
- passer_player_name can include non-QBs on trick plays, so do not rank passers without a sample-size threshold.

Column metadata:
{COLUMN_METADATA_SUMMARY}

Domain knowledge:
{DOMAIN_KNOWLEDGE}

Examples:
{SQL_EXAMPLES}

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

Critical output rules:
- Return only one corrected SQL query.
- The first word of your response must be SELECT or WITH.
- Do not include explanations.
- Do not include markdown.
- Do not include code fences.
- Do not include comments.
- Always include a LIMIT.
- Never use LIMIT 1. Use LIMIT 10 for ranking questions.
- Use explicit seasons from the user when provided. Do not replace explicit years with YEAR(CURRENT_DATE).
- For pass/run filtering, only use play_type = 'pass' or play_type = 'run'.
- Never use play_type = 'passing' or play_type = 'rushing'.
- If rejected or generated SQL uses LIMIT 1, change it to LIMIT 5 or LIMIT 10.
- Never use SELECT *.
- Use only the provided schema.
- The only valid table name is pbp.
- Never use pbp_data, play_by_play, nfl_data, games, teams, players, or any table not shown in the schema.

Interpretation rules:
- Preserve the user's original analytical intent.
- If the validation error says a LIMIT is missing, add a reasonable LIMIT.
- If the validation error says a table is disallowed, replace it with a valid table from the schema.
- For rankings, include sample size using COUNT(*).
- For QB rankings, include a HAVING COUNT(*) threshold.
- Do not repair by removing important filters from the original question.

Column metadata:
{COLUMN_METADATA_SUMMARY}

Domain knowledge:
{DOMAIN_KNOWLEDGE}

Examples:
{SQL_EXAMPLES}

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