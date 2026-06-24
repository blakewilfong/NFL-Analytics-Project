DOMAIN_KNOWLEDGE = """
Database facts:
- The only valid table name is pbp.
- Do not use pbp_data, play_by_play, nfl_data, games, teams, players, or any table not shown in the schema.

Preferred columns:
- Use play_type for basic pass/run filtering.
- Do not use play_type_nfl for basic pass/run filtering.
- Use success as the play-level success indicator.
- Do not use series_success for play-level success rate unless the user specifically asks about drive or series success.
- Use epa for Expected Points Added.
- Use posteam for offensive team queries.
- Use defteam for defensive team queries.
- Use passer_player_name for QB/passer queries.
- Use rusher_player_name for rushing player queries.
- Use receiver_player_name for receiving player queries.

Football concept mappings:
- "third down" means down = 3.
- "fourth down" means down = 4.
- "second down" means down = 2.
- "red zone" means yardline_100 <= 20.
- "offense" or "offensive team" means posteam.
- "defense" or "defensive team" means defteam.
- "passing plays" means play_type = 'pass', passer_player_name IS NOT NULL, and epa IS NOT NULL.
- "rushing plays" means play_type = 'run', rusher_player_name IS NOT NULL, and epa IS NOT NULL.
- "normal offensive plays" usually means play_type IN ('run', 'pass').

Personnel mappings:
- "11 personnel" means offense_personnel contains '1 RB', '1 TE', and '3 WR'.
- "12 personnel" means offense_personnel contains '1 RB', '2 TE', and '2 WR'.
- "13 personnel" means offense_personnel contains '1 RB', '3 TE', and '1 WR'.
- Do not compare offense_personnel directly to values like '11', '12', or '13'.

Ranking and sample size rules:
- "used the most" means rank by COUNT(*) DESC.
- "best", "most effective", or "highest EPA" usually means rank by AVG(epa) DESC.
- "most successful" usually means rank by AVG(success) DESC.
- "highest total value" means rank by SUM(epa) DESC.
- Always include COUNT(*) as attempts, plays, or sample_size when ranking.
- For player rankings, include a HAVING COUNT(*) threshold.
- For QB/passer rankings, use HAVING COUNT(*) >= 50 unless the user specifies otherwise.
- For team rankings, use HAVING COUNT(*) >= 50 unless the user specifies otherwise.
- Do not use LIMIT 1 for "best" questions unless the user explicitly asks for exactly one result.
- Use LIMIT 10 by default for rankings unless the user specifies another number.

Quarterback and passer rules:
- QB or quarterback passing questions should group by passer_player_name.
- passer_player_name can include non-QBs on trick plays.
- To avoid tiny-sample trick-play passers, QB rankings must include COUNT(*) and a HAVING COUNT(*) threshold.
- For "best quarterback" questions, rank by AVG(epa) unless the user specifically asks for success rate.
- For QB EPA rankings, include AVG(epa), SUM(epa), and COUNT(*).
- For QB rankings, filter play_type = 'pass'.
- For QB rankings, include passer_player_name IS NOT NULL.
- For QB rankings, include epa IS NOT NULL when using EPA.
- For QB rankings, do not use LIMIT 1 unless the user explicitly asks for only one result.

Running back and rushing rules:
- For "running back", "RB", "rusher", or rushing player questions, group by rusher_player_name.
- For rushing plays, always use play_type = 'run'. Never use play_type = 'rushing'.
- For rushing yards, prefer SUM(yards_gained) on rows where play_type = 'run'.
- For RB rankings, include COUNT(*) AS carries.
- For RB rankings, include SUM(yards_gained), AVG(yards_gained), AVG(epa), SUM(epa), and AVG(success) when useful.
- For RB rankings, use HAVING COUNT(*) >= 100 unless the user specifies otherwise.
- For "most rushing yards", rank by SUM(yards_gained) DESC.
- For "best running back" without a specific metric, rank by SUM(epa) DESC and include efficiency context.
"""
