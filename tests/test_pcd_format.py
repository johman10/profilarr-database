"""Tests to validate PCD format structure and integrity."""

import json
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).parent.parent
PCD_JSON_PATH = PROJECT_ROOT / "pcd.json"
OPS_DIR = PROJECT_ROOT / "ops"


def test_pcd_json_exists():
    """Test that pcd.json file exists."""
    assert PCD_JSON_PATH.exists(), f"pcd.json not found at {PCD_JSON_PATH}"


def test_pcd_json_valid_format():
    """Test that pcd.json is valid JSON."""
    with open(PCD_JSON_PATH, encoding="utf-8") as f:
        data = json.load(f)
    assert data is not None


def test_pcd_json_required_fields():
    """Test that pcd.json contains all required fields."""
    with open(PCD_JSON_PATH, encoding="utf-8") as f:
        data = json.load(f)

    required_fields = [
        "name",
        "version",
        "description",
        "arr_types",
        "dependencies",
        "authors",
        "license",
        "repository",
    ]

    for field in required_fields:
        assert field in data, f"Missing required field: {field}"


def test_pcd_json_arr_types():
    """Test that arr_types contains expected values."""
    with open(PCD_JSON_PATH, encoding="utf-8") as f:
        data = json.load(f)

    assert data["arr_types"] == ["radarr", "sonarr"]


def test_pcd_json_profilarr_minimum_version():
    """Test that profilarr minimum version is 2.0.0."""
    with open(PCD_JSON_PATH, encoding="utf-8") as f:
        data = json.load(f)

    assert data["profilarr"]["minimum_version"] == "2.0.0"


def test_ops_directory_exists():
    """Test that ops directory exists."""
    assert OPS_DIR.exists(), f"ops directory not found at {OPS_DIR}"


def test_sql_files_exist():
    """Test that at least one SQL file exists in ops/ directory."""
    assert OPS_DIR.exists(), f"ops directory not found at {OPS_DIR}"

    sql_files = list(OPS_DIR.glob("*.sql"))
    assert len(sql_files) > 0, "No SQL files found in ops/ directory"


def test_initial_sql_exists():
    """Test that 1.initial.sql exists (for first generation)."""
    sql_path = OPS_DIR / "1.initial.sql"
    if sql_path.exists():
        assert True
    else:
        update_files = list(OPS_DIR.glob("*.update*.sql"))
        assert len(update_files) > 0, "Neither 1.initial.sql nor update files found"


def get_all_sql_files():
    """Get all SQL files from ops directory."""
    if not OPS_DIR.exists():
        return []
    return sorted(OPS_DIR.glob("*.sql"))


def test_sql_files_not_empty():
    """Test that SQL files are not empty."""
    sql_files = get_all_sql_files()
    assert len(sql_files) > 0, "No SQL files found"

    for sql_file in sql_files:
        content = sql_file.read_text(encoding="utf-8")
        assert len(content) > 0, f"{sql_file.name} is empty"


def test_sql_has_insert_statements():
    """Test that SQL files contain INSERT statements."""
    sql_files = get_all_sql_files()
    assert len(sql_files) > 0, "No SQL files to check"

    all_content = ""
    for sql_file in sql_files:
        all_content += sql_file.read_text(encoding="utf-8")

    assert "INSERT INTO" in all_content, "No INSERT statements found in SQL files"


def test_sql_has_tags():
    """Test that SQL files include TAG inserts."""
    sql_files = get_all_sql_files()
    all_content = ""
    for sql_file in sql_files:
        all_content += sql_file.read_text(encoding="utf-8")

    assert "INSERT INTO tags" in all_content, "No tag inserts found in SQL files"


def test_sql_has_regular_expressions():
    """Test that SQL files include regular_expressions inserts."""
    sql_files = get_all_sql_files()
    all_content = ""
    for sql_file in sql_files:
        all_content += sql_file.read_text(encoding="utf-8")

    assert (
        "INSERT INTO regular_expressions" in all_content
    ), "No regex inserts found in SQL files"


def test_sql_has_custom_formats():
    """Test that SQL files include custom_formats inserts."""
    sql_files = get_all_sql_files()
    all_content = ""
    for sql_file in sql_files:
        all_content += sql_file.read_text(encoding="utf-8")

    assert (
        "INSERT INTO custom_formats" in all_content
    ), "No custom format inserts found in SQL files"


def test_sql_has_quality_profiles():
    """Test that SQL files include quality_profiles inserts."""
    sql_files = get_all_sql_files()
    all_content = ""
    for sql_file in sql_files:
        all_content += sql_file.read_text(encoding="utf-8")

    assert (
        "INSERT INTO quality_profiles" in all_content
    ), "No quality profile inserts found in SQL files"


def test_sql_has_proper_syntax():
    """Test that all INSERT statements have proper SQL syntax."""
    sql_files = get_all_sql_files()
    all_content = ""
    for sql_file in sql_files:
        all_content += sql_file.read_text(encoding="utf-8")

    insert_count = all_content.count("INSERT INTO")
    assert insert_count > 0, "No INSERT statements found in SQL files"

    semicolon_count = all_content.count(";")
    assert (
        semicolon_count >= insert_count * 0.9
    ), "Missing semicolons - expected roughly 1 per INSERT statement"

    assert (
        "VALUES (" in all_content
    ), "No VALUES clause found in INSERT statements"


def test_sql_no_syntax_errors():
    """Basic validation that SQL doesn't have obvious syntax errors."""
    sql_files = get_all_sql_files()

    for sql_file in sql_files:
        all_content = sql_file.read_text(encoding="utf-8")
        insert_count = all_content.count("INSERT INTO")
        values_count = all_content.count("VALUES (")
        semicolon_count = all_content.count(";")

        assert insert_count > 0, f"No INSERT statements in {sql_file.name}"
        assert values_count == insert_count, f"VALUES clause count mismatch in {sql_file.name}"
        assert (
            semicolon_count >= insert_count * 0.9
        ), f"Missing semicolons in {sql_file.name}"


@pytest.mark.parametrize(
    "required_sections",
    [
        ("TAGS", "-- TAGS"),
        ("REGULAR EXPRESSIONS", "-- REGULAR EXPRESSIONS"),
        ("CUSTOM FORMATS", "-- CUSTOM FORMATS"),
        ("QUALITY PROFILES", "-- QUALITY PROFILES"),
    ],
)
def test_sql_sections_exist(required_sections):
    """Test that all required SQL sections exist."""
    sql_path = OPS_DIR / "1.initial.sql"
    content = sql_path.read_text(encoding="utf-8")
    section_name, section_marker = required_sections
    assert section_marker in content, f"Missing section marker for {section_name}"
