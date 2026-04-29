import os
import sys

import yaml
from utils.cf_groups import collect_cf_groups
from utils.custom_formats import collect_custom_formats
from utils.media_management import collect_media_management
from utils.profiles import collect_profiles
from utils.regex_patterns import collect_regex_patterns


# Prevent aliases from showing up
yaml.Dumper.ignore_aliases = lambda *args: True


def clear_output_dir(output_dir):
    if not os.path.exists(output_dir):
        print("Output directory does not exist, skipping clearing")
    else:
        for filename in os.listdir(output_dir):
            file_path = os.path.join(output_dir, filename)
            os.remove(file_path)
        print(f"Cleared output directory: {output_dir}")


def main():
    if len(sys.argv) != 3:
        print("Usage: python generate.py <input_dir> <output_dir>")
        sys.exit(1)
    input_dir = sys.argv[1]
    output_dir = sys.argv[2]

    regex_patterns_dir = os.path.join(output_dir, "regex_patterns")
    os.makedirs(regex_patterns_dir, exist_ok=True)
    clear_output_dir(regex_patterns_dir)

    custom_formats_dir = os.path.join(output_dir, "custom_formats")
    os.makedirs(custom_formats_dir, exist_ok=True)
    clear_output_dir(custom_formats_dir)

    profiles_dir = os.path.join(output_dir, "profiles")
    os.makedirs(profiles_dir, exist_ok=True)
    clear_output_dir(profiles_dir)

    media_management_dir = os.path.join(output_dir, "media_management")
    os.makedirs(media_management_dir, exist_ok=True)
    clear_output_dir(media_management_dir)

    for service in ["radarr", "sonarr"]:
        trash_custom_formats_dir = os.path.join(input_dir, f"{service}/cf")
        if not os.path.exists(trash_custom_formats_dir):
            print(
                f"Custom format directory {trash_custom_formats_dir} does not exist, skipping."
            )
            continue
        regex_patterns = collect_regex_patterns(
            service,
            trash_custom_formats_dir,
            regex_patterns_dir,
        )

    for service in ["radarr", "sonarr"]:
        trash_custom_formats_dir = os.path.join(input_dir, f"{service}/cf")
        if not os.path.exists(trash_custom_formats_dir):
            print(
                f"Custom format directory {trash_custom_formats_dir} does not exist, skipping."
            )
            continue

        trash_profiles_dir = os.path.join(input_dir, f"{service}/quality-profiles")
        if not os.path.exists(trash_profiles_dir):
            print(
                f"Custom format directory {trash_profiles_dir} does not exist, skipping."
            )
            continue
        trash_id_to_scoring_mapping, trash_id_to_name_mapping = collect_custom_formats(
            service, trash_custom_formats_dir, custom_formats_dir, regex_patterns
        )

        # Collect cf-groups with default flag
        cf_groups_dir = os.path.join(input_dir, f"{service}/cf-groups")
        cf_group_additions = collect_cf_groups(service, cf_groups_dir)

        collect_profiles(
            service,
            trash_profiles_dir,
            profiles_dir,
            trash_id_to_scoring_mapping,
            trash_id_to_name_mapping,
            cf_group_additions=cf_group_additions,
        )

    collect_media_management(input_dir, media_management_dir)


if __name__ == "__main__":
    main()
