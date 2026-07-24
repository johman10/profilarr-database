import os
import sys

from collectors.custom_format_collector import collect_custom_formats
from collectors.naming_collector import (
    collect_radarr_naming_patterns,
    collect_sonarr_naming_patterns,
)
from collectors.quality_definition_collector import collect_quality_definitions
from collectors.quality_profile_collector import collect_quality_profiles
from collectors.regex_collector import collect_regexes
from sql_writer import write_initial_sql


def main() -> None:
    if len(sys.argv) != 3:
        print("Usage: python generate.py <input_dir> <output_dir>")
        sys.exit(1)

    input_dir = sys.argv[1]
    output_dir = sys.argv[2]

    ops_dir = os.path.normpath(os.path.join(output_dir, "ops"))
    has_files = any(
        os.path.isfile(os.path.join(root, name))
        for root, _, files in os.walk(ops_dir)
        for name in files
        if name != ".gitkeep"
    )
    if has_files:
        print(f"Error: {ops_dir} is not empty. Not supported for now.")
        sys.exit(1)

    initial_sql_file = os.path.join(ops_dir, "1.initial.sql")

    regex_entries, regex_name_by_service_and_pattern = collect_regexes(input_dir)
    custom_format_entries = collect_custom_formats(input_dir, regex_name_by_service_and_pattern)
    quality_profile_entries = collect_quality_profiles(input_dir)
    quality_definition_entries = collect_quality_definitions(input_dir)
    radarr_naming_entries = collect_radarr_naming_patterns(input_dir)
    sonarr_naming_entries = collect_sonarr_naming_patterns(input_dir)

    write_initial_sql(
        initial_sql_file,
        regex_entries,
        custom_format_entries,
        quality_profile_entries,
        quality_definition_entries,
        radarr_naming_entries,
        sonarr_naming_entries,
    )


if __name__ == "__main__":
    main()
