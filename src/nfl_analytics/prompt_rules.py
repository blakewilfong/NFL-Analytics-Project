OUTPUT_RULES = """
Critical output rules:
- Your entire response must be only one SQL query.
- The first word of your response must be SELECT or WITH.
- Do not include explanations.
- Do not include markdown.
- Do not include code fences.
- Do not include comments.
- Write exactly one read-only query.
- Always include a LIMIT.
- Never use LIMIT 1.
- Never use SELECT *.
- Use only the provided schema.
- The only valid table name is pbp.
- Never use pbp_data, play_by_play, nfl_data, games, teams, players, or any table not shown in the schema.
""".strip()


RANKING_RULES = """
Ranking rules:
- For best, top, highest, most, worst, efficient, effective, or ranking questions, use LIMIT 10 by default.
- If the user asks for one result, still use LIMIT 5 unless they explicitly say "only one row" or "exactly one row".
- Analytics answers should show context around the top result.
- Always include sample size using COUNT(*) for rankings.
- For player rankings, use a HAVING COUNT(*) threshold.
- For team rankings, use a HAVING COUNT(*) threshold when appropriate.
- Include volume as context, but do not sort by volume unless the user asks who used something most often.
""".strip()


PERSONNEL_RULES = """
Personnel hard rules:
- For 11 personnel, the SQL must include all three predicates:
  offense_personnel LIKE '%1 RB%'
  offense_personnel LIKE '%1 TE%'
  offense_personnel LIKE '%3 WR%'
- For 12 personnel, the SQL must include all three predicates:
  offense_personnel LIKE '%1 RB%'
  offense_personnel LIKE '%2 TE%'
  offense_personnel LIKE '%2 WR%'
- For 13 personnel, the SQL must include all three predicates:
  offense_personnel LIKE '%1 RB%'
  offense_personnel LIKE '%3 TE%'
  offense_personnel LIKE '%1 WR%'
- Never use offense_personnel LIKE '%11%', '%12%', '%13%', '%WR13%', or similar shorthand.
""".strip()


QB_RULES = """
Quarterback query rules:
- For quarterback or QB passing questions, group by passer_player_name.
- For QB rankings, always filter play_type = 'pass'.
- For QB rankings, always include passer_player_name IS NOT NULL.
- For QB EPA rankings, always include epa IS NOT NULL.
- For QB rankings, always include COUNT(*) AS attempts.
- For QB rankings, always include HAVING COUNT(*) >= 50 unless the user specifies a different threshold.
- passer_player_name can include non-QBs on trick plays, so do not rank passers without a sample-size threshold.
""".strip()


REPAIR_RULES = """
Repair rules:
- Preserve the user's original analytical intent.
- If the validation error says a LIMIT is missing, add a reasonable LIMIT.
- If generated SQL uses LIMIT 1, change it to LIMIT 5 or LIMIT 10.
- If the validation error says a table is disallowed, replace it with a valid table from the schema.
- Do not repair by removing important filters from the original question.
""".strip()


def build_generation_rules() -> str:
    return "\n\n".join(
        [
            OUTPUT_RULES,
            RANKING_RULES,
            PERSONNEL_RULES,
            QB_RULES,
        ]
    )


def build_repair_rules() -> str:
    return "\n\n".join(
        [
            OUTPUT_RULES,
            REPAIR_RULES,
            RANKING_RULES,
            PERSONNEL_RULES,
            QB_RULES,
        ]
    )