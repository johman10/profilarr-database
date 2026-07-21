import os
import sys
import json
import re
from typing import TypedDict, cast


REGEX_SPECIFICATIONS = {
    "ReleaseTitleSpecification",
    "ReleaseGroupSpecification",
}

IMPLEMENTATION_TO_TAG_MAPPING = {
    "ReleaseTitleSpecification": "Release Title",
    "ResolutionSpecification": "Resolution",
    "SourceSpecification": "Source",
    "LanguageSpecification": "Language",
    "ReleaseGroupSpecification": "Release Group",
    "IndexerFlagSpecification": "Indexer Flag",
    "QualityModifierSpecification": "Quality Modifier",
    "ReleaseTypeSpecification": "Release Type",
}

IMPLEMENTATION_TO_CONDITION_TYPE = {
    "ReleaseTitleSpecification": "release_title",
    "ResolutionSpecification": "resolution",
    "SourceSpecification": "source",
    "LanguageSpecification": "language",
    "ReleaseGroupSpecification": "release_group",
    "IndexerFlagSpecification": "indexer_flag",
    "QualityModifierSpecification": "quality_modifier",
    "ReleaseTypeSpecification": "release_type",
}

LANGUAGE_MAPPING = {
    "radarr": {
        -1: "Any",
        -2: "Original",
        0: "Unknown",
        1: "English",
        2: "French",
        3: "Spanish",
        4: "German",
        5: "Italian",
        6: "Danish",
        7: "Dutch",
        8: "Japanese",
        9: "Icelandic",
        10: "Chinese",
        11: "Russian",
        12: "Polish",
        13: "Vietnamese",
        14: "Swedish",
        15: "Norwegian",
        16: "Finnish",
        17: "Turkish",
        18: "Portuguese",
        19: "Flemish",
        20: "Greek",
        21: "Korean",
        22: "Hungarian",
        23: "Hebrew",
        24: "Lithuanian",
        25: "Czech",
        26: "Hindi",
        27: "Romanian",
        28: "Thai",
        29: "Bulgarian",
        30: "Portuguese_br",
        31: "Arabic",
        32: "Ukrainian",
        33: "Persian",
        34: "Bengali",
        35: "Slovak",
        36: "Latvian",
        37: "Spanish_latino",
        38: "Catalan",
        39: "Croatian",
        40: "Serbian",
        41: "Bosnian",
        42: "Estonian",
        43: "Tamil",
        44: "Indonesian",
        45: "Telugu",
        46: "Macedonian",
        47: "Slovenian",
        48: "Malayalam",
        49: "Kannada",
        50: "Albanian",
        51: "Afrikaans",
    },
    "sonarr": {
        0: "Unknown",
        1: "English",
        2: "French",
        3: "Spanish",
        4: "German",
        5: "Italian",
        6: "Danish",
        7: "Dutch",
        8: "Japanese",
        9: "Icelandic",
        10: "Chinese",
        11: "Russian",
        12: "Polish",
        13: "Vietnamese",
        14: "Swedish",
        15: "Norwegian",
        16: "Finnish",
        17: "Turkish",
        18: "Portuguese",
        19: "Flemish",
        20: "Greek",
        21: "Korean",
        22: "Hungarian",
        23: "Hebrew",
        24: "Lithuanian",
        25: "Czech",
        26: "Arabic",
        27: "Hindi",
        28: "Bulgarian",
        29: "Malayalam",
        30: "Ukrainian",
        31: "Slovak",
        32: "Thai",
        33: "Portuguese_br",
        34: "Spanish_latino",
        35: "Romanian",
        36: "Latvian",
        37: "Persian",
        38: "Catalan",
        39: "Croatian",
        40: "Serbian",
        41: "Bosnian",
        42: "Estonian",
        43: "Tamil",
        44: "Indonesian",
        45: "Macedonian",
        46: "Slovenian",
        -2: "Original",
    },
}

INDEXER_FLAG_MAPPING = {
    "radarr": {
        1: "freeleech",
        2: "halfleech",
        4: "double_upload",
        32: "internal",
        128: "scene",
        256: "freeleech_75",
        512: "freeleech_25",
        2048: "nuked",
        8: "ptp_golden",
        16: "ptp_approved",
    },
    "sonarr": {
        1: "freeleech",
        2: "halfleech",
        4: "double_upload",
        8: "internal",
        16: "scene",
        32: "freeleech_75",
        64: "freeleech_25",
        128: "nuked",
    },
}

RELEASE_TYPE_MAPPING = {
    "sonarr": {
        0: "none",
        1: "single_episode",
        2: "multi_episode",
        3: "season_pack",
    }
}

SOURCE_MAPPING = {
    "radarr": {
        1: "cam",
        2: "telesync",
        3: "telecine",
        4: "workprint",
        5: "dvd",
        6: "tv",
        7: "web_dl",
        8: "webrip",
        9: "bluray",
    },
    "sonarr": {
        1: "television",
        2: "television_raw",
        3: "web_dl",
        4: "webrip",
        5: "dvd",
        6: "bluray",
        7: "bluray_raw",
    },
}

QUALITY_MODIFIER_MAPPING = {
    "radarr": {
        0: "none",
        1: "regional",
        2: "screener",
        3: "rawhd",
        4: "brdisk",
        5: "remux",
    }
}


class RegexEntry(TypedDict):
    name: str
    pattern: str
    tags: set[str]


class CustomFormatEntry(TypedDict):
    name: str
    description: str | None
    include_in_rename: bool
    tags: set[str]
    conditions: list["CustomFormatConditionEntry"]


class CustomFormatConditionEntry(TypedDict):
    name: str
    type: str
    arr_type: str
    negate: bool
    required: bool
    value: str | None  # Used for non-regex specifications
    except_value: bool  # Used for language specifications


class QualityProfileEntry(TypedDict):
    name: str
    description: str | None
    upgrades_allowed: int
    minimum_custom_format_score: int
    upgrade_until_score: int
    upgrade_score_increment: int
    tags: set[str]
    quality_groups: dict[str, set[str]]  # Maps group_name -> set of quality_names
    qualities: list["QualityProfileQualityEntry"]


class QualityProfileQualityEntry(TypedDict):
    quality_name: str | None
    quality_group_name: str | None
    position: int
    enabled: bool
    upgrade_until: bool


def sql_escape(value: str) -> str:
    return value.replace("'", "''")


def normalize_name(name: str) -> str:
    return " ".join(name.strip().split())


def _map_numeric_value(implementation: str, service_key: str, numeric_value: int) -> str:
    if implementation == "LanguageSpecification":
        return LANGUAGE_MAPPING[service_key][numeric_value]
    if implementation == "IndexerFlagSpecification":
        return INDEXER_FLAG_MAPPING[service_key][numeric_value]
    if implementation == "SourceSpecification":
        return SOURCE_MAPPING[service_key][numeric_value]
    if implementation == "ReleaseTypeSpecification":
        return RELEASE_TYPE_MAPPING[service_key][numeric_value]
    if implementation == "QualityModifierSpecification":
        return QUALITY_MODIFIER_MAPPING[service_key][numeric_value]
    if implementation == "ResolutionSpecification":
        return f"{numeric_value}p"

    print(f"ERROR: unrecongized implementation type: {implementation}")
    sys.exit(1)


def extract_specification_value(
    specification_dict: dict[str, object], implementation: str, service_key: str
) -> tuple[str | None, bool]:
    """Extract the value and except flag from a specification.

    Returns a tuple of (value, except_flag).
    For most specifications, except_flag is False.
    For LanguageSpecification, except_flag comes from exceptLanguage field.
    """
    fields_raw = specification_dict.get("fields")
    if not isinstance(fields_raw, dict):
        return None, False

    fields_dict = cast(dict[str, object], fields_raw)
    value = fields_dict.get("value")

    parsed_value: str | None = None
    if isinstance(value, int):
        parsed_value = _map_numeric_value(implementation, service_key, value)
    else:
        print(f"ERROR: unable to parse value for implementation {implementation}, service: {service_key}, value: {value}")
        sys.exit(1)

    except_value = False
    except_language_raw = fields_dict.get("exceptLanguage")
    if isinstance(except_language_raw, bool):
        except_value = except_language_raw

    return parsed_value, except_value


def ensure_unique_name(base_name: str, used_names: set[str]) -> str:
    candidate = base_name
    index = 2
    while candidate in used_names:
        candidate = f"{base_name} ({index})"
        index += 1
    return candidate


def get_condition_signature(condition: CustomFormatConditionEntry) -> tuple[object, ...]:
    return (
        condition["name"],
        condition["type"],
        condition["negate"],
        condition["required"],
        condition["value"],
        condition["except_value"],
    )


def conditions_match(
    left_conditions: list[CustomFormatConditionEntry],
    right_conditions: list[CustomFormatConditionEntry],
) -> bool:
    return sorted(get_condition_signature(condition) for condition in left_conditions) == sorted(
        get_condition_signature(condition) for condition in right_conditions
    )


def remove_markdown_comments(text: str) -> str:
    return re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL).strip()


def collect_regexes(input_dir: str) -> tuple[list[RegexEntry], dict[tuple[str, str], str]]:
    regex_by_pattern: dict[str, RegexEntry] = {}
    regex_name_by_service_and_pattern: dict[tuple[str, str], str] = {}
    used_names: set[str] = set()

    for service_key, tag_name in (("sonarr", "Sonarr"), ("radarr", "Radarr")):
        cf_dir = os.path.join(input_dir, service_key, "cf")
        if not os.path.isdir(cf_dir):
            continue

        for filename in sorted(os.listdir(cf_dir)):
            if not filename.endswith(".json"):
                continue

            file_path = os.path.join(cf_dir, filename)
            with open(file_path, "r", encoding="utf-8") as f:
                try:
                    payload = json.load(f)
                except json.JSONDecodeError:
                    print(f"Warning: Skipping invalid JSON file: {file_path}")
                    continue

            specifications_raw = payload.get("specifications")
            if not isinstance(specifications_raw, list):
                continue

            specifications = cast(list[object], specifications_raw)

            for specification_obj in specifications:
                if not isinstance(specification_obj, dict):
                    continue

                specification_dict = cast(dict[str, object], specification_obj)

                implementation = specification_dict.get("implementation")
                if implementation not in REGEX_SPECIFICATIONS:
                    continue

                fields_raw = specification_dict.get("fields")
                if not isinstance(fields_raw, dict):
                    continue

                fields_dict = cast(dict[str, object], fields_raw)

                pattern = fields_dict.get("value")
                if not isinstance(pattern, str) or not pattern.strip():
                    continue

                normalized_pattern = pattern.strip()
                existing_entry = regex_by_pattern.get(normalized_pattern)
                if existing_entry:
                    existing_entry["tags"].add(tag_name)
                    regex_name_by_service_and_pattern[(service_key, normalized_pattern)] = existing_entry["name"]
                    continue

                specification_name = cast(str, specification_dict.get("name"))
                base_name = normalize_name(specification_name)
                unique_name = ensure_unique_name(base_name, used_names)
                used_names.add(unique_name)

                regex_by_pattern[normalized_pattern] = {
                    "name": unique_name,
                    "pattern": normalized_pattern,
                    "tags": {tag_name},
                }

                regex_name_by_service_and_pattern[(service_key, normalized_pattern)] = unique_name

    return (
        sorted(regex_by_pattern.values(), key=lambda item: item["name"].lower()),
        regex_name_by_service_and_pattern,
    )


def collect_custom_formats(
    input_dir: str,
    regex_name_by_service_and_pattern: dict[tuple[str, str], str],
) -> list[CustomFormatEntry]:
    custom_formats_by_name: dict[str, CustomFormatEntry] = {}
    custom_format_names_by_raw_name: dict[str, list[str]] = {}
    used_names: set[str] = set()

    for service_key, tag_name in (("sonarr", "Sonarr"), ("radarr", "Radarr")):
        cf_dir = os.path.join(input_dir, service_key, "cf")
        if not os.path.isdir(cf_dir):
            continue

        for filename in sorted(os.listdir(cf_dir)):
            if not filename.endswith(".json"):
                continue

            file_path = os.path.join(cf_dir, filename)
            with open(file_path, "r", encoding="utf-8") as f:
                try:
                    payload = json.load(f)
                except json.JSONDecodeError:
                    print(f"Warning: Skipping invalid JSON file: {file_path}")
                    continue

            name_raw = payload.get("name")
            if not isinstance(name_raw, str) or not name_raw.strip():
                continue

            raw_name = normalize_name(name_raw)
            name = normalize_name(f"{tag_name} - {name_raw}")
            description = None
            cf_desc_filename = name_raw.lower().replace(" ", "-") + ".md"
            # Move to root of TRaSH-Guides and dive into includes for descriptions
            cf_desc_path = os.path.join(input_dir, "..", "..", "includes", "cf-descriptions", cf_desc_filename)
            if os.path.isfile(cf_desc_path):
                try:
                    with open(cf_desc_path, "r", encoding="utf-8") as desc_file:
                        description = remove_markdown_comments(desc_file.read())
                except (IOError, OSError):
                    pass
            include_in_rename_raw = payload.get("includeCustomFormatWhenRenaming")
            include_in_rename = bool(include_in_rename_raw) if isinstance(include_in_rename_raw, bool) else False

            specification_tags: set[str] = set()
            conditions: list[CustomFormatConditionEntry] = []
            specifications_raw = payload.get("specifications")
            seen_condition_names: set[str] = set()
            if isinstance(specifications_raw, list):
                specifications = cast(list[object], specifications_raw)
                for specification_obj in specifications:
                    if not isinstance(specification_obj, dict):
                        continue

                    specification_dict = cast(dict[str, object], specification_obj)
                    implementation = specification_dict.get("implementation")
                    if isinstance(implementation, str):
                        mapped_tag = IMPLEMENTATION_TO_TAG_MAPPING.get(implementation)
                        if mapped_tag:
                            specification_tags.add(mapped_tag)

                        condition_type = IMPLEMENTATION_TO_CONDITION_TYPE.get(implementation)
                        if condition_type is None:
                            print(f"Unsupported specification implementation in {file_path}: {implementation}")
                            sys.exit(1)

                        specification_name = specification_dict.get("name")
                        if not isinstance(specification_name, str) or not specification_name.strip():
                            print(f"Invalid specification name in {file_path}: {specification_name}")
                            sys.exit(1)

                        condition_name = normalize_name(specification_name)
                        if implementation in REGEX_SPECIFICATIONS:
                            fields_raw = specification_dict.get("fields")
                            if not isinstance(fields_raw, dict):
                                print(f"Missing fields for regex specification in {file_path}: {specification_name}")
                                sys.exit(1)

                            fields_dict = cast(dict[str, object], fields_raw)
                            pattern = fields_dict.get("value")
                            if not isinstance(pattern, str) or not pattern.strip():
                                print(f"Missing regex pattern in {file_path}: {specification_name}")
                                sys.exit(1)

                            regex_name = regex_name_by_service_and_pattern.get((service_key, pattern.strip()))
                            if regex_name is None:
                                print(
                                    "Regex specification missing generated regular expression "
                                    f"in {file_path}: {specification_name}"
                                )
                                sys.exit(1)
                            condition_name = regex_name

                        if condition_name in seen_condition_names:
                            print(
                                "Warning: Duplicate specification name found. "
                                f"Skipping duplicate in {file_path}: {condition_name}"
                            )
                            continue
                        seen_condition_names.add(condition_name)

                        negate_raw = specification_dict.get("negate")
                        required_raw = specification_dict.get("required")
                        negate = bool(negate_raw) if isinstance(negate_raw, bool) else False
                        required = bool(required_raw) if isinstance(required_raw, bool) else False

                        # Extract specification value for non-regex types
                        spec_value = None
                        except_value = False
                        if implementation not in REGEX_SPECIFICATIONS:
                            spec_value, except_value = extract_specification_value(
                                specification_dict, implementation, service_key
                            )

                        conditions.append(
                            {
                                "name": condition_name,
                                "type": condition_type,
                                "arr_type": service_key,
                                "negate": negate,
                                "required": required,
                                "value": spec_value,
                                "except_value": except_value,
                            }
                        )

            matching_entry_name = None
            for existing_name in custom_format_names_by_raw_name.get(raw_name, []):
                existing_entry = custom_formats_by_name[existing_name]
                if conditions_match(existing_entry["conditions"], conditions):
                    matching_entry_name = existing_name
                    break

            if matching_entry_name is not None:
                existing_entry = custom_formats_by_name[matching_entry_name]
                existing_entry["tags"].update({tag_name, *specification_tags})
                existing_entry["include_in_rename"] = existing_entry["include_in_rename"] or include_in_rename
                if existing_entry["description"] is None:
                    existing_entry["description"] = description

                merged_name = raw_name
                if existing_entry["name"] != merged_name and (
                    merged_name not in custom_formats_by_name
                    or custom_formats_by_name[merged_name] is existing_entry
                ):
                    del custom_formats_by_name[matching_entry_name]
                    used_names.discard(existing_entry["name"])
                    existing_entry["name"] = merged_name
                    custom_formats_by_name[merged_name] = existing_entry
                    used_names.add(merged_name)
                    raw_names = custom_format_names_by_raw_name.get(raw_name, [])
                    custom_format_names_by_raw_name[raw_name] = [
                        merged_name if existing_name == matching_entry_name else existing_name
                        for existing_name in raw_names
                    ]

                continue

            name = ensure_unique_name(name, used_names)
            used_names.add(name)
            custom_formats_by_name[name] = {
                "name": name,
                "description": description,
                "include_in_rename": include_in_rename,
                "tags": {tag_name, *specification_tags},
                "conditions": conditions,
            }
            custom_format_names_by_raw_name.setdefault(raw_name, []).append(name)

    return sorted(custom_formats_by_name.values(), key=lambda item: item["name"].lower())


def collect_quality_profile_groups(input_dir: str) -> dict[str, set[str]]:
    """Collect quality profile groups and return mapping of trash_id to group names."""
    trash_id_to_groups: dict[str, set[str]] = {}

    for service_key in ("sonarr", "radarr"):
        groups_file = os.path.join(
            input_dir, service_key, "quality-profile-groups", "groups.json"
        )
        if not os.path.isfile(groups_file):
            continue

        with open(groups_file, "r", encoding="utf-8") as f:
            groups = json.load(f)

        for group in groups:
            group_name = group.get("name")
            if not group_name:
                continue

            profiles = group.get("profiles", {})
            for trash_id in profiles.values():
                if trash_id not in trash_id_to_groups:
                    trash_id_to_groups[trash_id] = set()
                trash_id_to_groups[trash_id].add(group_name)

    return trash_id_to_groups


def collect_quality_profiles(input_dir: str) -> list[QualityProfileEntry]:
    quality_profiles_by_name: dict[str, QualityProfileEntry] = {}
    trash_id_to_groups = collect_quality_profile_groups(input_dir)

    for service_key in ("sonarr", "radarr"):
        qp_dir = os.path.join(input_dir, service_key, "quality-profiles")
        if not os.path.isdir(qp_dir):
            continue

        for filename in sorted(os.listdir(qp_dir)):
            if not filename.endswith(".json"):
                continue

            file_path = os.path.join(qp_dir, filename)
            with open(file_path, "r", encoding="utf-8") as f:
                payload = json.load(f)

            name = payload.get("name")
            if not name:
                continue

            description = payload.get("trash_description")
            upgrades_allowed = 1 if payload.get("upgradeAllowed", True) else 0
            minimum_custom_format_score = payload.get("minFormatScore", 0)
            upgrade_until_score = payload.get("cutoffFormatScore", 0)
            upgrade_score_increment = payload.get("minUpgradeFormatScore", 1)
            trash_id = payload.get("trash_id", "")
            tags = trash_id_to_groups.get(trash_id, set()).copy()
            quality_groups: dict[str, set[str]] = {}
            qualities: list[QualityProfileQualityEntry] = []

            items_raw = payload.get("items")
            if isinstance(items_raw, list):
                items = cast(list[object], items_raw)
                cutoff_raw = payload.get("cutoff")
                cutoff_name = normalize_name(cutoff_raw) if isinstance(cutoff_raw, str) else None

                for position, item_obj in enumerate(items):
                    if not isinstance(item_obj, dict):
                        continue

                    item_dict = cast(dict[str, object], item_obj)
                    group_name_raw = item_dict.get("name")
                    if not isinstance(group_name_raw, str) or not group_name_raw.strip():
                        continue

                    group_name = normalize_name(group_name_raw)
                    allowed_raw = item_dict.get("allowed")
                    enabled = bool(allowed_raw) if isinstance(allowed_raw, bool) else False
                    upgrade_until = cutoff_name is not None and group_name == cutoff_name

                    group_items = item_dict.get("items")
                    if isinstance(group_items, list) and group_items:
                        group_items = cast(list[str], group_items)

                        # Extract quality names from the group items
                        group_members: set[str] = set()
                        for group_item in group_items:
                            group_members.add(group_item.strip())

                        if group_members:
                            quality_groups[group_name] = group_members
                            qualities.append(
                                {
                                    "quality_name": None,
                                    "quality_group_name": group_name,
                                    "position": position,
                                    "enabled": enabled,
                                    "upgrade_until": upgrade_until,
                                }
                            )
                        continue

                    qualities.append(
                        {
                            "quality_name": group_name,
                            "quality_group_name": None,
                            "position": position,
                            "enabled": enabled,
                            "upgrade_until": upgrade_until,
                        }
                    )

            existing_entry = quality_profiles_by_name.get(name)
            if existing_entry is not None:
                existing_entry["tags"].update(tags)
                for group_name, members in quality_groups.items():
                    if group_name not in existing_entry["quality_groups"]:
                        existing_entry["quality_groups"][group_name] = set()
                    existing_entry["quality_groups"][group_name].update(members)
                existing_entry["qualities"].extend(qualities)
                if existing_entry["description"] is None:
                    existing_entry["description"] = description
                continue

            quality_profiles_by_name[name] = {
                "name": name,
                "description": description,
                "upgrades_allowed": upgrades_allowed,
                "minimum_custom_format_score": minimum_custom_format_score,
                "upgrade_until_score": upgrade_until_score,
                "upgrade_score_increment": upgrade_score_increment,
                "tags": tags,
                "quality_groups": quality_groups,
                "qualities": qualities,
            }

    for entry in quality_profiles_by_name.values():
        deduped_qualities: list[QualityProfileQualityEntry] = []
        seen_quality_keys: set[tuple[object, ...]] = set()
        for quality in sorted(entry["qualities"], key=lambda item: item["position"]):
            quality_key = (
                quality["quality_name"],
                quality["quality_group_name"],
                quality["position"],
            )
            if quality_key in seen_quality_keys:
                continue

            seen_quality_keys.add(quality_key)
            deduped_qualities.append(quality)

        entry["qualities"] = deduped_qualities

    return sorted(quality_profiles_by_name.values(), key=lambda item: item["name"].lower())


def main():
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

    with open(initial_sql_file, "w", encoding="utf-8") as f:
        for tag_name in [
            "Sonarr",
            "Radarr",
            "Release Title",
            "Resolution",
            "Source",
            "Language",
            "Release Group",
            "Indexer Flag",
            "Quality Modifier",
            "Release Type",
            "French",
            "German",
            "Default",
            "SQP",
            "Anime"
        ]:
            f.write(f"INSERT INTO tags (name) VALUES ('{tag_name}');\n")

        regex_entries, regex_name_by_service_and_pattern = collect_regexes(input_dir)
        for entry in regex_entries:
            escaped_name = sql_escape(entry["name"])
            escaped_pattern = sql_escape(entry["pattern"])
            f.write(
                "INSERT INTO regular_expressions (name, pattern) "
                f"VALUES ('{escaped_name}', '{escaped_pattern}');\n"
            )

        for entry in regex_entries:
            escaped_name = sql_escape(entry["name"])
            for tag_name in sorted(entry["tags"]):
                f.write(
                    "INSERT INTO regular_expression_tags "
                    "(regular_expression_name, tag_name) "
                    f"VALUES ('{escaped_name}', '{tag_name}');\n"
                )

        custom_format_entries = collect_custom_formats(input_dir, regex_name_by_service_and_pattern)
        for entry in custom_format_entries:
            escaped_name = sql_escape(entry["name"])
            escaped_description = (
                f"'{sql_escape(entry['description'])}'"
                if entry["description"] is not None
                else "NULL"
            )
            include_in_rename = 1 if entry["include_in_rename"] else 0
            f.write(
                "INSERT INTO custom_formats (name, description, include_in_rename) "
                f"VALUES ('{escaped_name}', {escaped_description}, {include_in_rename});\n"
            )

        for entry in custom_format_entries:
            escaped_custom_format_name = sql_escape(entry["name"])
            for condition in entry["conditions"]:
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

        # Insert records into condition type-specific tables
        for entry in custom_format_entries:
            escaped_custom_format_name = sql_escape(entry["name"])
            for condition in entry["conditions"]:
                escaped_condition_name = sql_escape(condition["name"])
                condition_type = condition["type"]

                # Insert into appropriate condition type table based on type
                if condition_type in ("release_title", "release_group"):
                    # Pattern-based conditions - use condition name as regex name
                    escaped_regex_name = sql_escape(condition["name"])
                    f.write(
                        "INSERT INTO condition_patterns "
                        "(custom_format_name, condition_name, regular_expression_name) "
                        f"VALUES ('{escaped_custom_format_name}', '{escaped_condition_name}', "
                        f"'{escaped_regex_name}');\n"
                    )
                elif condition_type == "language":
                    # Language-based conditions
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
                    # Indexer flag conditions
                    if condition["value"] is not None:
                        escaped_flag = sql_escape(condition["value"])
                        f.write(
                            "INSERT INTO condition_indexer_flags "
                            "(custom_format_name, condition_name, flag) "
                            f"VALUES ('{escaped_custom_format_name}', '{escaped_condition_name}', "
                            f"'{escaped_flag}');\n"
                        )
                elif condition_type == "source":
                    # Source conditions
                    if condition["value"] is not None:
                        escaped_source = sql_escape(condition["value"])
                        f.write(
                            "INSERT INTO condition_sources "
                            "(custom_format_name, condition_name, source) "
                            f"VALUES ('{escaped_custom_format_name}', '{escaped_condition_name}', "
                            f"'{escaped_source}');\n"
                        )
                elif condition_type == "resolution":
                    # Resolution conditions
                    if condition["value"] is not None:
                        escaped_resolution = sql_escape(condition["value"])
                        f.write(
                            "INSERT INTO condition_resolutions "
                            "(custom_format_name, condition_name, resolution) "
                            f"VALUES ('{escaped_custom_format_name}', '{escaped_condition_name}', "
                            f"'{escaped_resolution}');\n"
                        )
                elif condition_type == "quality_modifier":
                    # Quality modifier conditions
                    if condition["value"] is not None:
                        escaped_quality_modifier = sql_escape(condition["value"])
                        f.write(
                            "INSERT INTO condition_quality_modifiers "
                            "(custom_format_name, condition_name, quality_modifier) "
                            f"VALUES ('{escaped_custom_format_name}', '{escaped_condition_name}', "
                            f"'{escaped_quality_modifier}');\n"
                        )
                elif condition_type == "release_type":
                    # Release type conditions
                    if condition["value"] is not None:
                        escaped_release_type = sql_escape(condition["value"])
                        f.write(
                            "INSERT INTO condition_release_types "
                            "(custom_format_name, condition_name, release_type) "
                            f"VALUES ('{escaped_custom_format_name}', '{escaped_condition_name}', "
                            f"'{escaped_release_type}');\n"
                        )

        for entry in custom_format_entries:
            escaped_name = sql_escape(entry["name"])
            for tag_name in sorted(entry["tags"]):
                f.write(
                    "INSERT INTO custom_format_tags "
                    "(custom_format_name, tag_name) "
                    f"VALUES ('{escaped_name}', '{tag_name}');\n"
                )

        quality_profile_entries = collect_quality_profiles(input_dir)
        for entry in quality_profile_entries:
            escaped_name = sql_escape(entry["name"])
            escaped_description = (
                f"'{sql_escape(entry['description'])}'"
                if entry["description"] is not None
                else "NULL"
            )
            upgrades_allowed = entry["upgrades_allowed"]
            minimum_custom_format_score = entry["minimum_custom_format_score"]
            upgrade_until_score = entry["upgrade_until_score"]
            upgrade_score_increment = entry["upgrade_score_increment"]
            f.write(
                "INSERT INTO quality_profiles "
                "(name, description, upgrades_allowed, minimum_custom_format_score, "
                "upgrade_until_score, upgrade_score_increment) "
                f"VALUES ('{escaped_name}', {escaped_description}, {upgrades_allowed}, "
                f"{minimum_custom_format_score}, {upgrade_until_score}, {upgrade_score_increment});\n"
            )

        for entry in quality_profile_entries:
            escaped_quality_profile_name = sql_escape(entry["name"])
            for tag_name in sorted(entry["tags"]):
                f.write(
                    "INSERT INTO quality_profile_tags "
                    "(quality_profile_name, tag_name) "
                    f"VALUES ('{escaped_quality_profile_name}', '{tag_name}');\n"
                )

        for entry in quality_profile_entries:
            escaped_quality_profile_name = sql_escape(entry["name"])
            for group_name in sorted(entry["quality_groups"].keys()):
                escaped_group_name = sql_escape(group_name)
                f.write(
                    "INSERT INTO quality_groups "
                    "(quality_profile_name, name) "
                    f"VALUES ('{escaped_quality_profile_name}', '{escaped_group_name}');\n"
                )

        for entry in quality_profile_entries:
            escaped_quality_profile_name = sql_escape(entry["name"])
            for group_name in sorted(entry["quality_groups"].keys()):
                escaped_group_name = sql_escape(group_name)
                for quality_name in sorted(entry["quality_groups"][group_name]):
                    escaped_quality_name = sql_escape(quality_name)
                    f.write(
                        "INSERT INTO quality_group_members "
                        "(quality_profile_name, quality_group_name, quality_name) "
                        f"VALUES ('{escaped_quality_profile_name}', '{escaped_group_name}', "
                        f"'{escaped_quality_name}');\n"
                    )

        for entry in quality_profile_entries:
            escaped_quality_profile_name = sql_escape(entry["name"])
            for quality in sorted(entry["qualities"], key=lambda item: item["position"]):
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

if __name__ == "__main__":
    main()
