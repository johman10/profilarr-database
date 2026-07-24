import sys

from common import sql_escape
from constants import DEFAULT_TAGS
from models import (
    CustomFormatEntry,
    QualityDefinitionEntry,
    QualityProfileEntry,
    RadarrNamingEntry,
    RegexEntry,
    ServiceKey,
    SonarrNamingEntry,
)


def write_initial_sql(
    initial_sql_file: str,
    regex_entries: list[RegexEntry],
    custom_format_entries: list[CustomFormatEntry],
    quality_profile_entries: list[QualityProfileEntry],
    quality_definition_entries: dict[ServiceKey, list[QualityDefinitionEntry]],
    radarr_naming_entries: list[RadarrNamingEntry],
    sonarr_naming_entries: list[SonarrNamingEntry],
) -> None:
    custom_format_by_service_and_trash_id: dict[tuple[ServiceKey, str], tuple[str, dict[str, int]]] = {}
    for custom_format_entry in custom_format_entries:
        for service_key, service_entry in custom_format_entry["by_service"].items():
            trash_id = service_entry["trash_id"]
            if not trash_id:
                continue

            lookup_key = (service_key, trash_id)
            if lookup_key in custom_format_by_service_and_trash_id:
                print(
                    "ERROR: duplicate custom format for "
                    f"service={service_key.value}, trash_id={trash_id}"
                )
                sys.exit(1)

            custom_format_by_service_and_trash_id[lookup_key] = (
                custom_format_entry["name"],
                service_entry["trash_scores"],
            )

    with open(initial_sql_file, "w", encoding="utf-8") as f:
        for tag_name in DEFAULT_TAGS:
            f.write(f"INSERT INTO tags (name) VALUES ('{tag_name}');\n")

        for regex_entry in regex_entries:
            escaped_name = sql_escape(regex_entry["name"])
            escaped_pattern = sql_escape(regex_entry["pattern"])
            f.write(
                "INSERT INTO regular_expressions (name, pattern) "
                f"VALUES ('{escaped_name}', '{escaped_pattern}');\n"
            )

        for regex_entry in regex_entries:
            escaped_name = sql_escape(regex_entry["name"])
            for tag_name in sorted(regex_entry["tags"]):
                f.write(
                    "INSERT INTO regular_expression_tags "
                    "(regular_expression_name, tag_name) "
                    f"VALUES ('{escaped_name}', '{tag_name}');\n"
                )

        for custom_format_entry in custom_format_entries:
            escaped_name = sql_escape(custom_format_entry["name"])
            escaped_description = (
                f"'{sql_escape(custom_format_entry['description'])}'"
                if custom_format_entry["description"] is not None
                else "NULL"
            )
            include_in_rename = 1 if custom_format_entry["include_in_rename"] else 0
            f.write(
                "INSERT INTO custom_formats (name, description, include_in_rename) "
                f"VALUES ('{escaped_name}', {escaped_description}, {include_in_rename});\n"
            )

        for custom_format_entry in custom_format_entries:
            escaped_custom_format_name = sql_escape(custom_format_entry["name"])
            for condition in custom_format_entry["conditions"]:
                escaped_condition_name = sql_escape(condition["name"])
                escaped_condition_type = sql_escape(condition["type"])
                escaped_arr_type = sql_escape(condition["arr_type"])
                negate = 1 if condition["negate"] else 0
                required = 1 if condition["required"] else 0
                f.write(
                    "INSERT INTO custom_format_conditions "
                    "(custom_format_name, name, type, arr_type, negate, required) "
                    f"VALUES ('{escaped_custom_format_name}', '{escaped_condition_name}', "
                    f"'{escaped_condition_type}', '{escaped_arr_type}', {negate}, {required});\n"
                )

        for custom_format_entry in custom_format_entries:
            escaped_custom_format_name = sql_escape(custom_format_entry["name"])
            for condition in custom_format_entry["conditions"]:
                escaped_condition_name = sql_escape(condition["name"])
                condition_type = condition["type"]

                if condition_type in ("release_title", "release_group"):
                    escaped_regex_name = sql_escape(condition["name"])
                    f.write(
                        "INSERT INTO condition_patterns "
                        "(custom_format_name, condition_name, regular_expression_name) "
                        f"VALUES ('{escaped_custom_format_name}', '{escaped_condition_name}', "
                        f"'{escaped_regex_name}');\n"
                    )
                elif condition_type == "language":
                    if condition["value"] is not None:
                        escaped_language_name = sql_escape(condition["value"])
                        except_language = 1 if condition["except_value"] else 0
                        f.write(
                            "INSERT INTO condition_languages "
                            "(custom_format_name, condition_name, language_name, except_language) "
                            f"VALUES ('{escaped_custom_format_name}', '{escaped_condition_name}', "
                            f"'{escaped_language_name}', {except_language});\n"
                        )
                elif condition_type == "indexer_flag":
                    if condition["value"] is not None:
                        escaped_flag = sql_escape(condition["value"])
                        f.write(
                            "INSERT INTO condition_indexer_flags "
                            "(custom_format_name, condition_name, flag) "
                            f"VALUES ('{escaped_custom_format_name}', '{escaped_condition_name}', "
                            f"'{escaped_flag}');\n"
                        )
                elif condition_type == "source":
                    if condition["value"] is not None:
                        escaped_source = sql_escape(condition["value"])
                        f.write(
                            "INSERT INTO condition_sources "
                            "(custom_format_name, condition_name, source) "
                            f"VALUES ('{escaped_custom_format_name}', '{escaped_condition_name}', "
                            f"'{escaped_source}');\n"
                        )
                elif condition_type == "resolution":
                    if condition["value"] is not None:
                        escaped_resolution = sql_escape(condition["value"])
                        f.write(
                            "INSERT INTO condition_resolutions "
                            "(custom_format_name, condition_name, resolution) "
                            f"VALUES ('{escaped_custom_format_name}', '{escaped_condition_name}', "
                            f"'{escaped_resolution}');\n"
                        )
                elif condition_type == "quality_modifier":
                    if condition["value"] is not None:
                        escaped_quality_modifier = sql_escape(condition["value"])
                        f.write(
                            "INSERT INTO condition_quality_modifiers "
                            "(custom_format_name, condition_name, quality_modifier) "
                            f"VALUES ('{escaped_custom_format_name}', '{escaped_condition_name}', "
                            f"'{escaped_quality_modifier}');\n"
                        )
                elif condition_type == "release_type":
                    if condition["value"] is not None:
                        escaped_release_type = sql_escape(condition["value"])
                        f.write(
                            "INSERT INTO condition_release_types "
                            "(custom_format_name, condition_name, release_type) "
                            f"VALUES ('{escaped_custom_format_name}', '{escaped_condition_name}', "
                            f"'{escaped_release_type}');\n"
                        )

        for custom_format_entry in custom_format_entries:
            escaped_name = sql_escape(custom_format_entry["name"])
            for tag_name in sorted(custom_format_entry["tags"]):
                f.write(
                    "INSERT INTO custom_format_tags "
                    "(custom_format_name, tag_name) "
                    f"VALUES ('{escaped_name}', '{tag_name}');\n"
                )

        for quality_profile_entry in quality_profile_entries:
            escaped_name = sql_escape(quality_profile_entry["name"])
            escaped_description = (
                f"'{sql_escape(quality_profile_entry['description'])}'"
                if quality_profile_entry["description"] is not None
                else "NULL"
            )
            upgrades_allowed = quality_profile_entry["upgrades_allowed"]
            minimum_custom_format_score = quality_profile_entry["minimum_custom_format_score"]
            upgrade_until_score = quality_profile_entry["upgrade_until_score"]
            upgrade_score_increment = quality_profile_entry["upgrade_score_increment"]
            f.write(
                "INSERT INTO quality_profiles "
                "(name, description, upgrades_allowed, minimum_custom_format_score, "
                "upgrade_until_score, upgrade_score_increment) "
                f"VALUES ('{escaped_name}', {escaped_description}, {upgrades_allowed}, "
                f"{minimum_custom_format_score}, {upgrade_until_score}, {upgrade_score_increment});\n"
            )

        for quality_profile_entry in quality_profile_entries:
            escaped_quality_profile_name = sql_escape(quality_profile_entry["name"])
            for tag_name in sorted(quality_profile_entry["tags"]):
                f.write(
                    "INSERT INTO quality_profile_tags "
                    "(quality_profile_name, tag_name) "
                    f"VALUES ('{escaped_quality_profile_name}', '{tag_name}');\n"
                )

        for quality_profile_entry in quality_profile_entries:
            escaped_quality_profile_name = sql_escape(quality_profile_entry["name"])
            for group_name in sorted(quality_profile_entry["quality_groups"].keys()):
                escaped_group_name = sql_escape(group_name)
                f.write(
                    "INSERT INTO quality_groups "
                    "(quality_profile_name, name) "
                    f"VALUES ('{escaped_quality_profile_name}', '{escaped_group_name}');\n"
                )

        for quality_profile_entry in quality_profile_entries:
            escaped_quality_profile_name = sql_escape(quality_profile_entry["name"])
            for group_name in sorted(quality_profile_entry["quality_groups"].keys()):
                escaped_group_name = sql_escape(group_name)
                for quality_name in sorted(quality_profile_entry["quality_groups"][group_name]):
                    escaped_quality_name = sql_escape(quality_name)
                    f.write(
                        "INSERT INTO quality_group_members "
                        "(quality_profile_name, quality_group_name, quality_name) "
                        f"VALUES ('{escaped_quality_profile_name}', '{escaped_group_name}', "
                        f"'{escaped_quality_name}');\n"
                    )

        for quality_profile_entry in quality_profile_entries:
            escaped_quality_profile_name = sql_escape(quality_profile_entry["name"])
            for quality in sorted(quality_profile_entry["qualities"], key=lambda item: item["position"]):
                escaped_quality_name = (
                    f"'{sql_escape(quality['quality_name'])}'" if quality["quality_name"] is not None else "NULL"
                )
                escaped_quality_group_name = (
                    f"'{sql_escape(quality['quality_group_name'])}'"
                    if quality["quality_group_name"] is not None
                    else "NULL"
                )
                enabled = 1 if quality["enabled"] else 0
                upgrade_until = 1 if quality["upgrade_until"] else 0
                f.write(
                    "INSERT INTO quality_profile_qualities "
                    "(quality_profile_name, quality_name, quality_group_name, position, enabled, upgrade_until) "
                    f"VALUES ('{escaped_quality_profile_name}', {escaped_quality_name}, {escaped_quality_group_name}, "
                    f"{quality['position']}, {enabled}, {upgrade_until});\n"
                )

        for quality_profile_entry in quality_profile_entries:
            profile_name = quality_profile_entry["name"]
            escaped_qp_name = sql_escape(profile_name)

            for service_key, profile_service_entry in quality_profile_entry["by_service"].items():
                format_items = profile_service_entry["format_items"]
                trash_score_set = profile_service_entry["trash_score_set"]

                for cf_trash_id in format_items.values():
                    cf_lookup = custom_format_by_service_and_trash_id.get((service_key, cf_trash_id))
                    if cf_lookup is None:
                        print(
                            "ERROR: missing custom format for "
                            f"service={service_key.value}, trash_id={cf_trash_id}, "
                            f"quality_profile={profile_name}"
                        )
                        sys.exit(1)

                    cf_name, trash_scores = cf_lookup
                    cf_score = trash_scores.get(trash_score_set, trash_scores.get("default", 0))

                    escaped_cf_name = sql_escape(cf_name)
                    f.write(
                        "INSERT INTO quality_profile_custom_formats "
                        "(quality_profile_name, custom_format_name, arr_type, score) "
                        f"VALUES ('{escaped_qp_name}', '{escaped_cf_name}', '{service_key.value}', {cf_score});\n"
                    )

        for service_key in (ServiceKey.RADARR, ServiceKey.SONARR):
            table_name = f"{service_key.value}_quality_definitions"
            for quality_definition_entry in quality_definition_entries[service_key]:
                escaped_name = sql_escape(quality_definition_entry["name"])
                escaped_quality_name = sql_escape(quality_definition_entry["quality_name"])
                f.write(
                    f"INSERT INTO {table_name} "
                    "(name, quality_name, min_size, max_size, preferred_size) "
                    f"VALUES ('{escaped_name}', '{escaped_quality_name}', "
                    f"{quality_definition_entry['min_size']}, {quality_definition_entry['max_size']}, {quality_definition_entry['preferred_size']});\n"
                )

        for radarr_naming_entry in radarr_naming_entries:
            escaped_name = sql_escape(radarr_naming_entry["name"])
            escaped_movie_format = sql_escape(radarr_naming_entry["movie_format"])
            escaped_movie_folder_format = sql_escape(radarr_naming_entry["movie_folder_format"])
            f.write(
                "INSERT INTO radarr_naming "
                "(name, rename, movie_format, movie_folder_format, replace_illegal_characters, "
                "colon_replacement_format) "
                f"VALUES ('{escaped_name}', 1, '{escaped_movie_format}', '{escaped_movie_folder_format}', "
                "0, 'smart');\n"
            )

        for sonarr_naming_entry in sonarr_naming_entries:
            escaped_name = sql_escape(sonarr_naming_entry["name"])
            escaped_standard_episode_format = sql_escape(sonarr_naming_entry["standard_episode_format"])
            escaped_daily_episode_format = sql_escape(sonarr_naming_entry["daily_episode_format"])
            escaped_anime_episode_format = sql_escape(sonarr_naming_entry["anime_episode_format"])
            escaped_series_folder_format = sql_escape(sonarr_naming_entry["series_folder_format"])
            escaped_season_folder_format = sql_escape(sonarr_naming_entry["season_folder_format"])
            f.write(
                "INSERT INTO sonarr_naming "
                "(name, rename, standard_episode_format, daily_episode_format, anime_episode_format, "
                "series_folder_format, season_folder_format, replace_illegal_characters, "
                "colon_replacement_format, multi_episode_style) "
                f"VALUES ('{escaped_name}', 1, '{escaped_standard_episode_format}', "
                f"'{escaped_daily_episode_format}', '{escaped_anime_episode_format}', "
                f"'{escaped_series_folder_format}', '{escaped_season_folder_format}', 0, 4, 5);\n"
            )
