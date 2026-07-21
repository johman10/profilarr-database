"""PCD metadata generation for Profilarr 2.x format."""

import json
import os
import re
import subprocess
from datetime import datetime


def get_last_sql_file_number(ops_dir):
    """
    Get the last SQL file number in ops directory.

    Returns:
        int: Highest numbered file (e.g., 2 for "2.update-*.sql"), or 0 if no files exist
    """
    if not os.path.exists(ops_dir):
        return 0

    highest = 0
    for filename in os.listdir(ops_dir):
        match = re.match(r"^(\d+)(?:\.initial|\.update)", filename)
        if match:
            num = int(match.group(1))
            highest = max(highest, num)

    return highest


def get_next_sql_filename(ops_dir):
    """
    Generate the next SQL filename.

    Returns:
        tuple: (filename, is_initial) where filename is like "1.initial.sql" or "2.update-20260720.sql"
    """
    last_num = get_last_sql_file_number(ops_dir)

    if last_num == 0:
        return "1.initial.sql", True
    else:
        date_str = datetime.now().strftime("%Y%m%d")
        return f"{last_num + 1}.update-{date_str}.sql", False


def is_first_generation(ops_dir):
    """Check if this is the first generation (no SQL files exist yet)."""
    return get_last_sql_file_number(ops_dir) == 0


def get_git_changes(output_dir):
    """
    Check if there are git changes in the output directory.

    Returns:
        bool: True if there are changes, False otherwise
    """
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain", output_dir],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return bool(result.stdout.strip())
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def get_current_version(output_dir):
    """
    Read the current version from pcd.json if it exists.

    Returns:
        str: Current version or "1.0.0" if file doesn't exist
    """
    pcd_path = os.path.join(output_dir, "pcd.json")
    if os.path.exists(pcd_path):
        try:
            with open(pcd_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("version", "1.0.0")
        except (json.JSONDecodeError, IOError):
            return "1.0.0"
    return "1.0.0"


def increment_patch_version(version_str):
    """
    Increment the patch version (e.g., 1.0.0 -> 1.0.1).

    Args:
        version_str: Version string in semver format

    Returns:
        str: Incremented version
    """
    try:
        parts = version_str.split(".")
        if len(parts) >= 3:
            patch = int(parts[2])
            parts[2] = str(patch + 1)
            return ".".join(parts[:3])
    except (ValueError, IndexError):
        pass
    return "1.0.0"


def generate_pcd_metadata(output_dir):
    """
    Generate pcd.json metadata file.

    Args:
        output_dir: Output directory where pcd.json will be written

    Returns:
        dict: The generated metadata
    """
    os.makedirs(output_dir, exist_ok=True)

    current_version = get_current_version(output_dir)

    if get_git_changes(output_dir):
        version = increment_patch_version(current_version)
    else:
        version = current_version

    metadata = {
        "name": "trash-pcd",
        "version": version,
        "description": "TRaSH Guides converted to PCD format for Profilarr",
        "arr_types": ["radarr", "sonarr"],
        "dependencies": {"https://github.com/Dictionarry-Hub/schema": "1.1.0"},
        "authors": [{"name": "TRaSH"}, {"name": "Dictionarry Team"}],
        "license": "MIT",
        "repository": "https://github.com/dictionarry-hub/trash-pcd",
        "tags": ["trash", "guides", "quality", "custom-formats", "profiles"],
        "links": {
            "homepage": "https://trash-guides.info",
            "issues": "https://github.com/dictionarry-hub/trash-pcd/issues",
        },
        "profilarr": {"minimum_version": "2.0.0"},
    }

    pcd_path = os.path.join(output_dir, "pcd.json")
    with open(pcd_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print(f"Generated: {pcd_path}")
    return metadata
