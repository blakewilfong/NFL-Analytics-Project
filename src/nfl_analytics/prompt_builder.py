
class PromptBuilder:

    def build_sql_prompt(self, question: str, schema_summary: str) -> str:
        return f"""
                You are an assistant that converts NFL analytics questions into DuckDB SQL.
                
                Use only the provided schema.
                Return only SQL.
                Do not explain the SQL.
                Only write one SELECT query.
                Always include a LIMIT.
                Never use SELECT *.
                
                Schema:
                {schema_summary}
                
                Question:
                {question}
                
                SQL:
                """.strip()