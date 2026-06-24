import os
from dotenv import load_dotenv

from nfl_analytics.data.database import get_connection
from nfl_analytics.data.query_runner import QueryRunner
from nfl_analytics.llm.question_engine import QuestionEngine
from nfl_analytics.data.schema import SchemaService
from nfl_analytics.llm.sql_generator import OllamaSQLGenerator
from nfl_analytics.validation.sql_validator import SQLValidator


def main() -> None:
    load_dotenv()

    model = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b")

    conn = get_connection()

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

        print("NFL Analytics Question Console")
        print(f"Using Ollama model: {model}")
        print("Ask a question. Type 'exit' to quit.")
        print()

        while True:
            question = input("question> ").strip()

            if question.lower() in {"exit", "quit"}:
                break

            if not question:
                continue

            try:
                result = question_engine.answer(question)

                print("\nGenerated SQL:")
                print(result.sql)

                print("\nResult:")
                print(result.data)

            except Exception as e:
                print(f"\nError: {e}")

            print()

    finally:
        conn.close()


if __name__ == "__main__":
    main()