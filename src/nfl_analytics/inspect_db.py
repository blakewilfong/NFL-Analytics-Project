from nfl_analytics.database import get_connection


def main() -> None:
    conn = get_connection()

    df = conn.execute("SELECT * FROM pbp").fetchdf()

    before_gb = df.memory_usage(deep=True).sum() / (1024 ** 3)
    print(f"Before conversion: {before_gb:.2f} GB")

    df = df.convert_dtypes(dtype_backend="pyarrow")

    after_gb = df.memory_usage(deep=True).sum() / (1024 ** 3)
    print(f"After conversion: {after_gb:.2f} GB")

if __name__ == "__main__":
    main()