import hashlib
import os
import sys

from utils.cf_groups import collect_cf_groups
from utils.custom_formats import collect_custom_formats
from utils.media_management import collect_media_management
from utils.pcd_metadata import (
    generate_pcd_metadata,
    get_next_sql_filename,
    is_first_generation,
)
from utils.profiles import collect_profiles
from utils.regex_patterns import collect_regex_patterns
from utils.sql_generator import SQLBuffer


def setup_pcd_structure(output_dir):
    """Create PCD directory structure."""
    ops_dir = os.path.join(output_dir, "ops")
    deps_dir = os.path.join(output_dir, "deps")
    tweaks_dir = os.path.join(output_dir, "tweaks")
    media_management_dir = os.path.join(output_dir, "media_management")

    os.makedirs(ops_dir, exist_ok=True)
    os.makedirs(deps_dir, exist_ok=True)
    os.makedirs(tweaks_dir, exist_ok=True)
    os.makedirs(media_management_dir, exist_ok=True)

    if not os.path.exists(os.path.join(deps_dir, ".gitkeep")):
        open(os.path.join(deps_dir, ".gitkeep"), "w", encoding="utf-8").close()

    if not os.path.exists(os.path.join(tweaks_dir, ".gitkeep")):
        open(os.path.join(tweaks_dir, ".gitkeep"), "w", encoding="utf-8").close()

    return ops_dir, media_management_dir


def sql_content_hash(content):
    """Generate hash of SQL content for change detection."""
    return hashlib.sha256(content.encode()).hexdigest()


def detect_changes(new_content, ops_dir):
    """
    Detect if SQL content has changed compared to all existing SQL files.

    Returns:
        bool: True if there are changes, False if identical to existing content
    """
    if not os.path.exists(ops_dir):
        return True

    new_hash = sql_content_hash(new_content)

    for filename in os.listdir(ops_dir):
        if filename.endswith(".sql"):
            file_path = os.path.join(ops_dir, filename)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    existing_content = f.read()
                    if sql_content_hash(existing_content) == new_hash:
                        return False
            except (IOError, OSError):
                continue

    return True


def main():
    if len(sys.argv) != 3:
        print("Usage: python generate.py <input_dir> <output_dir>")
        sys.exit(1)

    input_dir = sys.argv[1]
    output_dir = sys.argv[2]

    ops_dir, media_management_dir = setup_pcd_structure(output_dir)

    sql_buffer = SQLBuffer()

    all_regex_patterns = {}

    for service in ["radarr", "sonarr"]:
        trash_custom_formats_dir = os.path.join(input_dir, f"{service}/cf")
        if not os.path.exists(trash_custom_formats_dir):
            print(
                f"Custom format directory {trash_custom_formats_dir} does not exist, skipping."
            )
            continue

        regex_patterns = collect_regex_patterns(service, trash_custom_formats_dir)
        all_regex_patterns[service] = regex_patterns

    sql_buffer.add_section_header("TAGS")
    for service in ["radarr", "sonarr"]:
        sql_buffer.add_insert("tags", ["name"], [service.capitalize()], section="TAGS")

    for service in ["radarr", "sonarr"]:
        trash_custom_formats_dir = os.path.join(input_dir, f"{service}/cf")
        if not os.path.exists(trash_custom_formats_dir):
            continue

        regex_patterns = all_regex_patterns.get(service, {})
        collect_regex_patterns(
            service, trash_custom_formats_dir, sql_buffer=sql_buffer
        )

    for service in ["radarr", "sonarr"]:
        trash_custom_formats_dir = os.path.join(input_dir, f"{service}/cf")
        if not os.path.exists(trash_custom_formats_dir):
            continue

        regex_patterns = all_regex_patterns.get(service, {})
        trash_id_to_scoring_mapping, trash_id_to_name_mapping = collect_custom_formats(
            service, trash_custom_formats_dir, regex_patterns, sql_buffer=sql_buffer
        )

        trash_profiles_dir = os.path.join(input_dir, f"{service}/quality-profiles")
        if not os.path.exists(trash_profiles_dir):
            print(
                f"Profiles directory {trash_profiles_dir} does not exist, skipping."
            )
            continue

        cf_groups_dir = os.path.join(input_dir, f"{service}/cf-groups")
        cf_group_additions = collect_cf_groups(service, cf_groups_dir)

        collect_profiles(
            service,
            trash_profiles_dir,
            trash_id_to_scoring_mapping,
            trash_id_to_name_mapping,
            sql_buffer=sql_buffer,
            cf_group_additions=cf_group_additions,
        )

    sql_content = sql_buffer.render(include_header=True)

    first_generation = is_first_generation(ops_dir)

    if first_generation:
        sql_filename = "1.initial.sql"
        write_file = True
        print("First generation detected - creating 1.initial.sql")
    else:
        if detect_changes(sql_content, ops_dir):
            sql_filename, _ = get_next_sql_filename(ops_dir)
            write_file = True
            print(f"Changes detected - creating {sql_filename}")
        else:
            sql_filename = None
            write_file = False
            print("No changes detected - skipping SQL file generation")

    if write_file:
        ops_path = os.path.join(ops_dir, sql_filename)
        with open(ops_path, "w", encoding="utf-8") as f:
            f.write(sql_content)
        print(f"Generated: {ops_path}")

    collect_media_management(input_dir, media_management_dir)

    generate_pcd_metadata(output_dir)
    print("PCD format generation complete!")


if __name__ == "__main__":
    main()
