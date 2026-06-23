from nfl_analytics.sql_validator import SQLValidator


def make_validator() -> SQLValidator:
    return SQLValidator(
        allowed_tables={"pbp"},
        max_limit=100,
    )


def test_allows_valid_select_query():
    validator = make_validator()

    sql = """
        SELECT
            season,
            COUNT(*) AS rows
        FROM pbp
        GROUP BY season
        ORDER BY season
        LIMIT 100
    """

    result = validator.validate(sql)

    assert result.is_valid is True


def test_rejects_drop_table():
    validator = make_validator()

    sql = "DROP TABLE pbp"

    result = validator.validate(sql)

    assert result.is_valid is False
    assert "Only SELECT" in result.message


def test_rejects_multiple_statements():
    validator = make_validator()

    sql = """
        SELECT season FROM pbp LIMIT 10;
        DROP TABLE pbp;
    """

    result = validator.validate(sql)

    assert result.is_valid is False
    assert "Only one SQL statement" in result.message


def test_rejects_unknown_table():
    validator = make_validator()

    sql = """
        SELECT
            *
        FROM secret_table
        LIMIT 10
    """

    result = validator.validate(sql)

    assert result.is_valid is False
    assert "disallowed tables" in result.message


def test_rejects_select_star():
    validator = make_validator()

    sql = """
        SELECT *
        FROM pbp
        LIMIT 10
    """

    result = validator.validate(sql)

    assert result.is_valid is False
    assert "SELECT *" in result.message


def test_rejects_missing_limit():
    validator = make_validator()

    sql = """
        SELECT
            season,
            COUNT(*) AS rows
        FROM pbp
        GROUP BY season
    """

    result = validator.validate(sql)

    assert result.is_valid is False
    assert "LIMIT" in result.message


def test_rejects_limit_that_is_too_large():
    validator = make_validator()

    sql = """
        SELECT
            season
        FROM pbp
        LIMIT 1000
    """

    result = validator.validate(sql)

    assert result.is_valid is False
    assert "LIMIT cannot be greater" in result.message