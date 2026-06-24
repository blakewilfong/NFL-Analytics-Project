from dataclasses import dataclass
from textwrap import dedent


@dataclass(frozen=True)
class SQLExample:
    question: str
    sql: str


SQL_EXAMPLES = [
    SQLExample(
        question="best quarterback on second down in 2025",
        sql="""
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
        """,
    ),
    SQLExample(
        question="who were the best quarterbacks by average EPA on third down in 2024",
        sql="""
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
        """,
    ),
    SQLExample(
        question="which teams used 13 personnel the most in 2025",
        sql="""
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
        """,
    ),
    SQLExample(
        question="which teams were most effective using 13 personnel in 2025",
        sql="""
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
        """,
    ),
    SQLExample(
        question="which offenses had the highest success rate in the red zone in 2024",
        sql="""
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
        """,
    ),
    SQLExample(
        question="who had the most rushing yards in 2025",
        sql="""
        SELECT
            rusher_player_name AS running_back,
            COUNT(*) AS carries,
            ROUND(SUM(yards_gained), 0) AS rushing_yards
        FROM pbp
        WHERE
            season = 2025
            AND play_type = 'run'
            AND rusher_player_name IS NOT NULL
            AND yards_gained IS NOT NULL
        GROUP BY rusher_player_name
        HAVING COUNT(*) >= 100
        ORDER BY rushing_yards DESC
        LIMIT 10
        """,
    ),
    SQLExample(
        question="best running back in 2025",
        sql="""
        SELECT
            rusher_player_name AS running_back,
            COUNT(*) AS carries,
            ROUND(SUM(yards_gained), 0) AS rushing_yards,
            ROUND(AVG(yards_gained), 2) AS yards_per_carry,
            ROUND(AVG(epa), 3) AS avg_epa,
            ROUND(SUM(epa), 3) AS total_epa,
            ROUND(AVG(success), 3) AS success_rate
        FROM pbp
        WHERE
            season = 2025
            AND play_type = 'run'
            AND rusher_player_name IS NOT NULL
            AND yards_gained IS NOT NULL
            AND epa IS NOT NULL
        GROUP BY rusher_player_name
        HAVING COUNT(*) >= 100
        ORDER BY total_epa DESC
        LIMIT 10
        """,
    ),
]


def clean_sql(sql: str) -> str:
    return dedent(sql).strip()


def build_sql_examples() -> str:
    sections = []

    for index, example in enumerate(SQL_EXAMPLES, start=1):
        sections.append(
            "\n".join(
                [
                    f"Example {index}:",
                    f"Question: {example.question}",
                    "SQL:",
                    clean_sql(example.sql),
                ]
            )
        )

    return "\n\n".join(sections)