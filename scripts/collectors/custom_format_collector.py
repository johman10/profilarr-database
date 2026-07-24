import os
import sys
import json
from typing import cast

from common import (
    conditions_match,
    ensure_unique_name,
    extract_specification_value,
    normalize_name,
    remove_markdown_comments,
)
from constants import (
    IMPLEMENTATION_TO_CONDITION_TYPE,
    IMPLEMENTATION_TO_TAG_MAPPING,
    REGEX_SPECIFICATIONS,
)
from models import (
    CustomFormatConditionEntry,
    CustomFormatEntry,
    CustomFormatServiceEntry,
    ServiceKey,
)
from parsing import ParseContext, ParseError, load_json_object, optional_type, require_type


def _parse_condition(
    specification_dict: dict[str, object],
    file_path: str,
    service_key: ServiceKey,
    regex_name_by_service_and_pattern: dict[tuple[str, str], str],
) -> tuple[str, str, bool, bool, str | None, bool]:
    ctx = ParseContext(file_path)
    implementation = require_type(ctx, specification_dict, "implementation", str)

    condition_type = IMPLEMENTATION_TO_CONDITION_TYPE.get(implementation)
    if condition_type is None:
        raise ParseError(f"Unsupported specification implementation in {file_path}: {implementation}")

    specification_name = require_type(ctx, specification_dict, "name", str)
    if not specification_name.strip():
        raise ParseError(f"Invalid specification name in {file_path}: {specification_name}")

    condition_name = normalize_name(specification_name)
    if implementation in REGEX_SPECIFICATIONS:
        fields_dict = require_type(ctx, specification_dict, "fields", dict)
        pattern = require_type(ctx, cast(dict[str, object], fields_dict), "value", str)
        if not pattern.strip():
            raise ParseError(f"Missing regex pattern in {file_path}: {specification_name}")

        regex_name = regex_name_by_service_and_pattern.get((service_key, pattern.strip()))
        if regex_name is None:
            raise ParseError(
                "Regex specification missing generated regular expression "
                f"in {file_path}: {specification_name}"
            )
        condition_name = regex_name

    negate = optional_type(specification_dict, "negate", bool, False)
    required = optional_type(specification_dict, "required", bool, False)

    spec_value = None
    except_value = False
    if implementation not in REGEX_SPECIFICATIONS:
        spec_value, except_value = extract_specification_value(
            specification_dict, implementation, service_key
        )

    return condition_name, condition_type, negate, required, spec_value, except_value


def collect_custom_formats(
    input_dir: str,
    regex_name_by_service_and_pattern: dict[tuple[str, str], str],
) -> list[CustomFormatEntry]:
    custom_formats_by_name: dict[str, CustomFormatEntry] = {}
    custom_format_names_by_raw_name: dict[str, list[str]] = {}
    used_names: set[str] = set()

    for service_key, tag_name in ((ServiceKey.SONARR, "Sonarr"), (ServiceKey.RADARR, "Radarr")):
        cf_dir = os.path.join(input_dir, service_key, "cf")
        if not os.path.isdir(cf_dir):
            continue

        for filename in sorted(os.listdir(cf_dir)):
            if not filename.endswith(".json"):
                continue

            file_path = os.path.join(cf_dir, filename)
            try:
                payload = load_json_object(file_path)
            except (json.JSONDecodeError, OSError, ParseError):
                print(f"Warning: Skipping invalid JSON file: {file_path}")
                continue

            name_raw = payload.get("name")
            if not isinstance(name_raw, str) or not name_raw.strip():
                continue

            raw_name = normalize_name(name_raw)
            name = normalize_name(f"{tag_name} - {name_raw}")
            trash_id = cast(str, payload.get("trash_id", ""))
            trash_scores_raw = payload.get("trash_scores", {})
            trash_scores = cast(dict[str, int], trash_scores_raw) if isinstance(trash_scores_raw, dict) else {}
            description = None
            cf_desc_filename = name_raw.lower().replace(" ", "-") + ".md"
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

                    try:
                        (
                            condition_name,
                            condition_type,
                            negate,
                            required,
                            spec_value,
                            except_value,
                        ) = _parse_condition(
                            specification_dict,
                            file_path,
                            service_key,
                            regex_name_by_service_and_pattern,
                        )
                    except ParseError as exc:
                        print(str(exc))
                        sys.exit(1)

                    if condition_name in seen_condition_names:
                        print(
                            "Warning: Duplicate specification name found. "
                            f"Skipping duplicate in {file_path}: {condition_name}"
                        )
                        continue
                    seen_condition_names.add(condition_name)

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
                existing_entry["by_service"][service_key] = {
                    "trash_id": trash_id,
                    "trash_scores": trash_scores,
                }

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
            service_entry: CustomFormatServiceEntry = {
                "trash_id": trash_id,
                "trash_scores": trash_scores,
            }
            custom_formats_by_name[name] = {
                "name": name,
                "description": description,
                "include_in_rename": include_in_rename,
                "tags": {tag_name, *specification_tags},
                "conditions": conditions,
                "by_service": {
                    service_key: service_entry
                },
            }
            custom_format_names_by_raw_name.setdefault(raw_name, []).append(name)

    return sorted(custom_formats_by_name.values(), key=lambda item: item["name"].lower())
