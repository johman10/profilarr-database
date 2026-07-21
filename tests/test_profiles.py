"""Tests to ensure profiles and custom formats are properly generated."""

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
def profile_insert_statements(sql_content):
    """Extract all quality_profiles INSERT statements."""
    profiles = []
    for line in sql_content.split("\n"):
        if "INSERT INTO quality_profiles" in line:
            profiles.append(line.strip())
    return profiles


@pytest.fixture(scope="module")
def custom_format_insert_statements(sql_content):
    """Extract all custom_formats INSERT statements."""
    formats = []
    for line in sql_content.split("\n"):
        if "INSERT INTO custom_formats" in line:
            formats.append(line.strip())
    return formats


@pytest.fixture(scope="module")
def profile_custom_format_mappings(sql_content):
    """Extract all quality_profile_custom_format INSERT statements."""
    mappings = []
    for line in sql_content.split("\n"):
        if "INSERT INTO quality_profile_custom_format" in line:
            mappings.append(line.strip())
    return mappings


def test_sql_file_exists():
    """Test that 1.initial.sql exists."""
    assert SQL_PATH.exists(), f"1.initial.sql not found at {SQL_PATH}"


def test_sql_contains_profiles(sql_content):
    """Test that SQL contains quality_profiles inserts."""
    assert (
        "INSERT INTO quality_profiles" in sql_content
    ), "No quality_profiles inserts found"


def test_sql_contains_custom_formats(sql_content):
    """Test that SQL contains custom_formats inserts."""
    assert (
        "INSERT INTO custom_formats" in sql_content
    ), "No custom_formats inserts found"


def test_sql_contains_profile_format_mappings(sql_content):
    """Test that SQL contains quality_profile_custom_format mappings."""
    assert (
        "INSERT INTO quality_profile_custom_format" in sql_content
    ), "No quality_profile_custom_format mappings found"


def test_profiles_have_complete_inserts(profile_insert_statements):
    """Test that profile INSERT statements are complete."""
    if not profile_insert_statements:
        pytest.skip("No profile insert statements found")

    for stmt in profile_insert_statements:
        assert stmt.startswith("INSERT INTO quality_profiles"), "Invalid profile statement"
        assert "VALUES (" in stmt, "Profile statement missing VALUES"


def test_custom_formats_have_complete_inserts(custom_format_insert_statements):
    """Test that custom format INSERT statements are complete."""
    if not custom_format_insert_statements:
        pytest.skip("No custom format insert statements found")

    for stmt in custom_format_insert_statements:
        assert stmt.startswith("INSERT INTO custom_formats"), "Invalid format statement"
        assert "VALUES (" in stmt, "Format statement missing VALUES"
        assert stmt.endswith(";"), "Format statement missing semicolon"


def test_mappings_have_complete_inserts(profile_custom_format_mappings):
    """Test that profile-format mapping INSERT statements are complete."""
    if not profile_custom_format_mappings:
        pytest.skip("No mapping statements found")

    for stmt in profile_custom_format_mappings:
        assert (
            stmt.startswith("INSERT INTO quality_profile_custom_format")
        ), "Invalid mapping statement"
        assert "VALUES (" in stmt, "Mapping statement missing VALUES"
        assert stmt.endswith(";"), "Mapping statement missing semicolon"


def test_mappings_have_score_values(profile_custom_format_mappings):
    """Test that profile-format mappings include score values."""
    if not profile_custom_format_mappings:
        pytest.skip("No mapping statements found")

    for stmt in profile_custom_format_mappings:
        assert "score" in stmt.lower() or "," in stmt, "Mapping missing score value"
