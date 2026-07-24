import os
import json
from typing import cast

from common import ensure_unique_name, normalize_name
from constants import REGEX_SPECIFICATIONS
from models import RegexEntry, ServiceKey
from parsing import ParseError, load_json_object


def collect_regexes(input_dir: str) -> tuple[list[RegexEntry], dict[tuple[str, str], str]]:
    regex_by_pattern: dict[str, RegexEntry] = {}
    regex_name_by_service_and_pattern: dict[tuple[str, str], str] = {}
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
