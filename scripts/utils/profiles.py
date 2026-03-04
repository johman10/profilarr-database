import os

import yaml
from markdownify import markdownify

from utils.file_utils import iterate_json_files
from utils.mappings.qualities import QUALITIES, SERVICE_QUALITY_TO_PROFILARR_QUALITY
from utils.strings import get_name


def _collect_profile_formats(
    service, trash_score_name, format_items, trash_id_to_scoring_mapping
):
    profile_formats = []
    for name, trash_id in format_items.items():
        scoring = trash_id_to_scoring_mapping[trash_id]
        score = scoring.get(trash_score_name, scoring.get("default", 0))
        if score == 0:
            continue

        profile_formats.append({"name": get_name(service, name), "score": score})
    return sorted(
        profile_formats,
        key=lambda profile_format: (
            -profile_format["score"],
            profile_format["name"].lower(),
        ),
        reverse=False,
    )


def _get_quality_id(service, quality_name):
    safe_quality_name = SERVICE_QUALITY_TO_PROFILARR_QUALITY[service].get(
        quality_name, quality_name
    )
    return next(
        (
            quality["id"]
            for quality in QUALITIES
            if quality["name"] == safe_quality_name
        )
    )


def _collect_qualities(service, items):
    qualities = []
    quality_collection_id = -1
    for item in items:
        if item.get("allowed", False) is False:
            continue

        quality_id = (
            _get_quality_id(service, item.get("name", ""))
            if item.get("items") is None
            else quality_collection_id
        )
        quality = {
            "id": quality_id,
            "name": item.get("name", ""),
        }
        if item.get("items") is not None:
            quality_collection_id -= 1
            quality["description"] = ""
            quality["qualities"] = []
            for sub_item in item["items"]:
                quality["qualities"].append(
                    {"id": _get_quality_id(service, sub_item), "name": sub_item}
                )
        qualities.append(quality)

    return list(qualities)


def _get_upgrade_until(quality_name, profile_qualities):
    found_quality = next(
        quality for quality in profile_qualities if quality["name"] == quality_name
    )
    if found_quality:
        found_quality = found_quality.copy()
        if found_quality.get("description", "") == "":
            found_quality.pop("description", None)
        found_quality.pop("qualities", None)
    return found_quality


def _collect_profile(service, input_json, output_dir, trash_id_to_scoring_mapping):
    # Compose YAML structure
    name = input_json.get("name", "")
    profile_qualities = _collect_qualities(service, input_json.get("items", []))
    yml_data = {
        "name": get_name(service, name),
        "description": f"""[Profile from TRaSH-Guides.](https://trash-guides.info/{service.capitalize()}/{service}-setup-quality-profiles)

{markdownify(input_json.get('trash_description', ''))}""".strip(),
        "tags": [service.capitalize()],
        "upgradesAllowed": input_json.get("upgradeAllowed", True),
        "minCustomFormatScore": input_json.get("minFormatScore", 0),
        "upgradeUntilScore": input_json.get("cutoffFormatScore", 0),
        "minScoreIncrement": input_json.get("minUpgradeFormatScore", 0),
        "custom_formats": _collect_profile_formats(
            service,
            input_json.get("trash_score_set"),
            input_json.get("formatItems", {}),
            trash_id_to_scoring_mapping,
        ),
        "qualities": profile_qualities,
        "upgrade_until": _get_upgrade_until(input_json.get("cutoff"), profile_qualities),
        "language": input_json.get("language", "any").lower(),
    }

    # Output path
    output_path = os.path.join(output_dir, f"{get_name(service, name)}.yml")
    with open(output_path, "w", encoding="utf-8") as f:
        yaml.dump(yml_data, f, sort_keys=False, allow_unicode=True)
    print(f"Generated: {output_path}")


def collect_profiles(
    service,
    input_dir,
    output_dir,
    trash_id_to_scoring_mapping,
):
    for _, _, data in iterate_json_files(input_dir):
        _collect_profile(service, data, output_dir, trash_id_to_scoring_mapping)
