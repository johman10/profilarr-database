import os
import json
from typing import cast

from common import normalize_name, round_half_up
from constants import QUALITY_SIZE_NAME_MAPPING
from models import QualityDefinitionEntry, ServiceKey
from parsing import ParseError, load_json_object


def collect_quality_definitions(input_dir: str) -> dict[ServiceKey, list[QualityDefinitionEntry]]:
    quality_definitions_by_service: dict[ServiceKey, list[QualityDefinitionEntry]] = {
        ServiceKey.SONARR: [],
        ServiceKey.RADARR: [],
    }

    for service_key in ServiceKey.all():
        quality_size_dir = os.path.join(input_dir, service_key, "quality-size")
        if not os.path.isdir(quality_size_dir):
            continue

        for filename in sorted(os.listdir(quality_size_dir)):
            if not filename.endswith(".json"):
                continue

            file_path = os.path.join(quality_size_dir, filename)
            try:
                payload_dict = load_json_object(file_path)
            except (json.JSONDecodeError, OSError, ParseError):
                print(f"Warning: Skipping invalid JSON file: {file_path}")
                continue

            definition_type_raw = payload_dict.get("type")
            if not isinstance(definition_type_raw, str) or not definition_type_raw.strip():
                continue

            definition_name = QUALITY_SIZE_NAME_MAPPING.get(
                definition_type_raw,
                normalize_name(definition_type_raw.replace("-", " ")),
            )

            qualities_raw = payload_dict.get("qualities")
            if not isinstance(qualities_raw, list):
                continue

            qualities = cast(list[object], qualities_raw)
            for quality_obj in qualities:
                if not isinstance(quality_obj, dict):
                    continue

                quality_dict = cast(dict[str, object], quality_obj)
                quality_name_raw = quality_dict.get("quality")
                min_size_raw = quality_dict.get("min")
                max_size_raw = quality_dict.get("max")
                preferred_size_raw = quality_dict.get("preferred")

                if not isinstance(quality_name_raw, str) or not quality_name_raw.strip():
                    continue
                if not isinstance(min_size_raw, (int, float)):
                    continue
                if not isinstance(max_size_raw, (int, float)):
                    continue
                if not isinstance(preferred_size_raw, (int, float)):
                    continue

                quality_definitions_by_service[service_key].append(
                    {
                        "name": definition_name,
                        "quality_name": quality_name_raw.strip(),
                        "min_size": round_half_up(min_size_raw),
                        "max_size": round_half_up(max_size_raw),
                        "preferred_size": round_half_up(preferred_size_raw),
                    }
                )

    for service_key, entries in quality_definitions_by_service.items():
        quality_definitions_by_service[service_key] = sorted(
            entries,
            key=lambda item: (item["name"].lower(), item["quality_name"].lower()),
        )

    return quality_definitions_by_service
