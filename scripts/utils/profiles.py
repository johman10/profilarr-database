import os

import yaml
from markdownify import markdownify

from utils.file_utils import iterate_json_files
from utils.mappings.qualities import QUALITIES, SERVICE_QUALITY_TO_PROFILARR_QUALITY
from utils.strings import get_name


def _collect_profile_formats(
    service, trash_score_name, format_items, trash_id_to_scoring_mapping, trash_id_to_name_mapping
):
    profile_formats = []
    for _name, trash_id in format_items.items():
        scoring = trash_id_to_scoring_mapping[trash_id]
        score = scoring.get(trash_score_name, scoring.get("default", 0))
        if score == 0:
            continue

        cf_name = trash_id_to_name_mapping[trash_id]
        profile_formats.append({"name": get_name(service, cf_name), "score": score})
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


def _merge_cf_group_additions(
    service, profile_score_set, profile_formats, cf_trash_ids, *,
    trash_id_to_scoring_mapping, trash_id_to_name_mapping
):
    """Merge CF group additions into profile formats list."""
    existing_cf_names = {fmt["name"] for fmt in profile_formats}
    additional_formats = []

    for cf_trash_id in cf_trash_ids:
        if cf_trash_id not in trash_id_to_name_mapping:
            continue

        cf_name = get_name(service, trash_id_to_name_mapping[cf_trash_id])
        if cf_name in existing_cf_names:
            continue

        scoring = trash_id_to_scoring_mapping.get(cf_trash_id, {})
        score = scoring.get(profile_score_set, scoring.get("default", 0))
        if score == 0:
            continue

        additional_formats.append({"name": cf_name, "score": score})

    return sorted(
        profile_formats + additional_formats,
        key=lambda fmt: (-fmt["score"], fmt["name"].lower()),
        reverse=False,
    )


def _build_profile_yaml_data(service, input_json, profile_formats, profile_qualities):
    """Build the YAML data structure for a profile."""
    return {
        "name": get_name(service, input_json.get("name", "")),
        "description": f"""[Profile from TRaSH-Guides.](https://trash-guides.info/{service.capitalize()}/{service}-setup-quality-profiles)

{markdownify(input_json.get('trash_description', ''))}""".strip(),
        "tags": [service.capitalize()],
        "upgradesAllowed": input_json.get("upgradeAllowed", True),
        "minCustomFormatScore": input_json.get("minFormatScore", 0),
        "upgradeUntilScore": input_json.get("cutoffFormatScore", 0),
        "minScoreIncrement": input_json.get("minUpgradeFormatScore", 0),
        "custom_formats": profile_formats,
        "qualities": profile_qualities,
        "upgrade_until": _get_upgrade_until(input_json.get("cutoff"), profile_qualities),
        "language": input_json.get("language", "any").lower(),
    }


def _collect_profile(
    service, input_json, output_dir, trash_id_to_scoring_mapping, trash_id_to_name_mapping, *, cf_group_additions=None
):
    profile_trash_id = input_json.get("trash_id")
    profile_score_set = input_json.get("trash_score_set")
    profile_qualities = _collect_qualities(service, input_json.get("items", []))

    profile_formats = _collect_profile_formats(
        service,
        profile_score_set,
        input_json.get("formatItems", {}),
        trash_id_to_scoring_mapping,
        trash_id_to_name_mapping,
    )

    if cf_group_additions and profile_trash_id in cf_group_additions:
        profile_formats = _merge_cf_group_additions(
            service, profile_score_set, profile_formats, cf_group_additions[profile_trash_id],
            trash_id_to_scoring_mapping=trash_id_to_scoring_mapping,
            trash_id_to_name_mapping=trash_id_to_name_mapping
        )

    yml_data = _build_profile_yaml_data(service, input_json, profile_formats, profile_qualities)

    output_path = os.path.join(output_dir, f"{get_name(service, input_json.get('name', ''))}.yml")
    with open(output_path, "w", encoding="utf-8") as f:
        yaml.dump(yml_data, f, sort_keys=False, allow_unicode=True)
    print(f"Generated: {output_path}")


def collect_profiles(
    service,
    input_dir,
    output_dir,
    trash_id_to_scoring_mapping,
    trash_id_to_name_mapping,
    *,
    cf_group_additions=None,
):
    for _, _, data in iterate_json_files(input_dir):
        _collect_profile(
            service, data, output_dir, trash_id_to_scoring_mapping, trash_id_to_name_mapping,
            cf_group_additions=cf_group_additions
        )
