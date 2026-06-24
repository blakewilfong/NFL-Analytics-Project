from dataclasses import dataclass


@dataclass(frozen=True)
class ColumnMetadata:
    name: str
    description: str
    use_when: str
    avoid_when: str = ""


PBP_COLUMN_METADATA = [
    ColumnMetadata(
        name="season",
        description="NFL season year.",
        use_when="Filtering or grouping by season, such as 2024 or 2025.",
    ),
    ColumnMetadata(
        name="week",
        description="NFL week number.",
        use_when="Filtering or grouping by week.",
    ),
    ColumnMetadata(
        name="game_id",
        description="Unique game identifier.",
        use_when="Grouping or filtering individual games.",
    ),
    ColumnMetadata(
        name="posteam",
        description="Team currently possessing the ball. This is the offense.",
        use_when="Offensive team rankings, offensive efficiency, usage, EPA, success rate.",
    ),
    ColumnMetadata(
        name="defteam",
        description="Team defending the play.",
        use_when="Defensive team rankings or defensive performance allowed.",
    ),
    ColumnMetadata(
        name="home_team",
        description="Home team abbreviation.",
        use_when="Home/away analysis.",
    ),
    ColumnMetadata(
        name="away_team",
        description="Away team abbreviation.",
        use_when="Home/away analysis.",
    ),
    ColumnMetadata(
        name="qtr",
        description="Game quarter.",
        use_when="Filtering by quarter, such as fourth quarter.",
    ),
    ColumnMetadata(
        name="down",
        description="Current down. First down is 1, second down is 2, third down is 3, fourth down is 4.",
        use_when="Questions about first down, second down, third down, or fourth down.",
    ),
    ColumnMetadata(
        name="ydstogo",
        description="Yards needed for a first down.",
        use_when="Short-yardage, medium-yardage, long-yardage, and distance-based analysis.",
    ),
    ColumnMetadata(
        name="yardline_100",
        description="Distance from the opponent's end zone. Lower means closer to scoring.",
        use_when="Red zone, goal-to-go, field position, backed-up offense.",
    ),
    ColumnMetadata(
        name="game_seconds_remaining",
        description="Seconds remaining in the game.",
        use_when="Two-minute drill, late-game, end-of-game analysis.",
    ),
    ColumnMetadata(
        name="half_seconds_remaining",
        description="Seconds remaining in the half.",
        use_when="End-of-half or two-minute situations.",
    ),
    ColumnMetadata(
        name="score_differential",
        description="Score margin from the possession team's perspective.",
        use_when="Garbage time filtering, close game filtering, comeback situations.",
    ),
    ColumnMetadata(
        name="play_type",
        description="Basic play type. For normal offensive plays, use values 'pass' and 'run'.",
        use_when="Filtering passing or rushing plays. Use play_type = 'pass' for passes and play_type = 'run' for rushes.",
        avoid_when="Do not use values like 'passing' or 'rushing'. Do not use play_type_nfl for basic pass/run filtering.",
    ),
    ColumnMetadata(
        name="passer_player_name",
        description="Name of the player credited as passer.",
        use_when="Quarterback or passer rankings.",
        avoid_when="Do not use without a sample-size threshold because non-QBs can appear on trick plays.",
    ),
    ColumnMetadata(
        name="rusher_player_name",
        description="Name of the player credited as rusher.",
        use_when="Running back or rushing player rankings.",
    ),
    ColumnMetadata(
        name="receiver_player_name",
        description="Name of the targeted receiver.",
        use_when="Receiver target, receiving EPA, receiving success analysis.",
    ),
    ColumnMetadata(
        name="epa",
        description="Expected Points Added for the play.",
        use_when="Efficiency, best, most effective, highest value, offensive or defensive performance.",
    ),
    ColumnMetadata(
        name="wpa",
        description="Win Probability Added for the play.",
        use_when="Clutch, win probability, high-leverage play analysis.",
    ),
    ColumnMetadata(
        name="success",
        description="Play-level success indicator. Usually 1 for successful play and 0 for unsuccessful play.",
        use_when="Success rate questions. Use AVG(success) for success rate.",
    ),
    ColumnMetadata(
        name="yards_gained",
        description="Yards gained on the play.",
        use_when="Yardage efficiency, explosive plays, rushing or passing yardage.",
    ),
    ColumnMetadata(
        name="touchdown",
        description="Whether the play resulted in a touchdown.",
        use_when="Touchdown rate or touchdown counts.",
    ),
    ColumnMetadata(
        name="interception",
        description="Whether the play resulted in an interception.",
        use_when="Interception rate or turnover analysis for passing plays.",
    ),
    ColumnMetadata(
        name="sack",
        description="Whether the play resulted in a sack.",
        use_when="Sack rate or pass protection analysis.",
    ),
    ColumnMetadata(
        name="complete_pass",
        description="Whether a pass was completed.",
        use_when="Completion rate analysis.",
    ),
    ColumnMetadata(
        name="air_yards",
        description="Depth of target on a pass before the catch.",
        use_when="Deep passing, average depth of target, downfield passing.",
    ),
    ColumnMetadata(
        name="yards_after_catch",
        description="Yards gained after the catch.",
        use_when="YAC analysis.",
    ),
    ColumnMetadata(
        name="offense_personnel",
        description="Offensive personnel grouping as a full text string, such as '1 RB, 3 TE, 1 WR' within a longer string.",
        use_when="11 personnel, 12 personnel, 13 personnel, formation/personnel usage.",
        avoid_when="Do not compare directly to '11', '12', or '13'. Use LIKE patterns.",
    ),
    ColumnMetadata(
        name="defense_personnel",
        description="Defensive personnel grouping as a full text string.",
        use_when="Defensive personnel analysis.",
    ),
]


DISCOURAGED_COLUMNS = [
    ColumnMetadata(
        name="play_type_nfl",
        description="NFL-specific play type field.",
        use_when="Only use if the user specifically asks for NFL's official play type labeling.",
        avoid_when="For basic pass/run filtering, use play_type instead.",
    ),
    ColumnMetadata(
        name="series_success",
        description="Series-level success indicator, not the preferred play-level success field.",
        use_when="Only use for drive or series success questions.",
        avoid_when="For play success rate, use success instead.",
    ),
]


def build_column_metadata_summary() -> str:
    lines = ["Preferred pbp columns:"]

    for column in PBP_COLUMN_METADATA:
        lines.append(f"- {column.name}: {column.description}")
        lines.append(f"  Use when: {column.use_when}")
        if column.avoid_when:
            lines.append(f"  Avoid when: {column.avoid_when}")

    lines.append("")
    lines.append("Discouraged or special-case columns:")

    for column in DISCOURAGED_COLUMNS:
        lines.append(f"- {column.name}: {column.description}")
        lines.append(f"  Use when: {column.use_when}")
        if column.avoid_when:
            lines.append(f"  Avoid when: {column.avoid_when}")

    return "\n".join(lines)