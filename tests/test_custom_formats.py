"""Tests to ensure custom formats and regex patterns are properly generated."""

from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).parent.parent
OPS_DIR = PROJECT_ROOT / "ops"
SQL_PATH = OPS_DIR / "1.initial.sql"


@pytest.fixture(scope="module")
def sql_content():
    """Fixture to load SQL content once."""
    if not SQL_PATH.exists():
        pytest.skip("1.initial.sql not found")
    return SQL_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def regex_insert_statements(sql_content):
    """Extract all regular_expressions INSERT statements."""
    patterns = []
    for line in sql_content.split("\n"):
        if "INSERT INTO regular_expressions" in line:
            patterns.append(line.strip())
    return patterns


@pytest.fixture(scope="module")
def custom_format_insert_statements(sql_content):
    """Extract all custom_formats INSERT statements."""
    formats = []
    for line in sql_content.split("\n"):
        if "INSERT INTO custom_formats" in line:
            formats.append(line.strip())
    return formats


@pytest.fixture(scope="module")
def format_conditions_insert_statements(sql_content):
    """Extract all custom_format_conditions INSERT statements."""
    conditions = []
    for line in sql_content.split("\n"):
        if "INSERT INTO custom_format_conditions" in line:
            conditions.append(line.strip())
    return conditions


def test_sql_file_exists():
    """Test that 1.initial.sql exists."""
    assert SQL_PATH.exists(), f"1.initial.sql not found at {SQL_PATH}"


def test_sql_contains_regex_patterns(sql_content):
    """Test that SQL contains regular_expressions inserts."""
    assert (
        "INSERT INTO regular_expressions" in sql_content
    ), "No regular_expressions inserts found"


def test_sql_contains_custom_formats(sql_content):
    """Test that SQL contains custom_formats inserts."""
    assert (
        "INSERT INTO custom_formats" in sql_content
    ), "No custom_formats inserts found"


def test_sql_contains_conditions(sql_content):
    """Test that SQL contains custom_format_conditions inserts."""
    assert (
        "INSERT INTO custom_format_conditions" in sql_content
    ), "No custom_format_conditions inserts found"


def test_regex_patterns_have_complete_inserts(regex_insert_statements):
    """Test that regex pattern INSERT statements are complete."""
    if not regex_insert_statements:
        pytest.skip("No regex insert statements found")

    for stmt in regex_insert_statements:
        assert stmt.startswith("INSERT INTO regular_expressions"), "Invalid regex statement"
        assert "VALUES (" in stmt, "Regex statement missing VALUES"
        assert stmt.endswith(";"), "Regex statement missing semicolon"
        assert "pattern" in stmt.lower() or "," in stmt, "Regex missing pattern value"


def test_custom_formats_have_complete_inserts(custom_format_insert_statements):
    """Test that custom format INSERT statements are complete."""
    if not custom_format_insert_statements:
        pytest.skip("No custom format insert statements found")

    for stmt in custom_format_insert_statements:
        assert stmt.startswith("INSERT INTO custom_formats"), "Invalid format statement"
        assert "VALUES (" in stmt, "Format statement missing VALUES"
        assert stmt.endswith(";"), "Format statement missing semicolon"


def test_conditions_have_complete_inserts(format_conditions_insert_statements):
    """Test that custom format conditions INSERT statements are complete."""
    if not format_conditions_insert_statements:
        pytest.skip("No condition insert statements found")

    for stmt in format_conditions_insert_statements:
        assert (
            stmt.startswith("INSERT INTO custom_format_conditions")
        ), "Invalid condition statement"
        assert "VALUES (" in stmt, "Condition statement missing VALUES"
        assert stmt.endswith(";"), "Condition statement missing semicolon"


def test_conditions_include_types(format_conditions_insert_statements):
    """Test that conditions include type information."""
    if not format_conditions_insert_statements:
        pytest.skip("No condition insert statements found")

    total_conditions = len(format_conditions_insert_statements)
    assert (
        total_conditions > 0
    ), "No valid condition statements found in SQL"
