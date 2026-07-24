import os
import json
from typing import cast

from common import normalize_name
from models import QualityProfileByServiceEntry, QualityProfileEntry, QualityProfileQualityEntry, ServiceKey
from parsing import load_json_object


def collect_quality_profile_groups(input_dir: str) -> dict[str, set[str]]:
    trash_id_to_groups: dict[str, set[str]] = {}

    for service_key in ServiceKey.all():
        groups_file = os.path.join(
            input_dir, service_key, "quality-profile-groups", "groups.json"
        )
        if not os.path.isfile(groups_file):
            continue

        with open(groups_file, "r", encoding="utf-8") as f:
            groups_raw = json.load(f)
        groups = cast(list[object], groups_raw) if isinstance(groups_raw, list) else []

        for group_obj in groups:
            if not isinstance(group_obj, dict):
                continue
            group = cast(dict[str, object], group_obj)
            group_name = group.get("name")
            if not group_name:
                continue

            profiles = group.get("profiles", {})
            profiles_dict = cast(dict[str, str], profiles) if isinstance(profiles, dict) else {}
            for trash_id in profiles_dict.values():
                if trash_id not in trash_id_to_groups:
                    trash_id_to_groups[trash_id] = set()
                trash_id_to_groups[trash_id].add(cast(str, group_name))

    return trash_id_to_groups


def collect_quality_profiles(input_dir: str) -> list[QualityProfileEntry]:
    quality_profiles_by_name: dict[str, QualityProfileEntry] = {}
    trash_id_to_groups = collect_quality_profile_groups(input_dir)

    for service_key in ServiceKey.all():
        qp_dir = os.path.join(input_dir, service_key, "quality-profiles")
        if not os.path.isdir(qp_dir):
            continue

        for filename in sorted(os.listdir(qp_dir)):
            if not filename.endswith(".json"):
                continue

            file_path = os.path.join(qp_dir, filename)
            payload = load_json_object(file_path)

            name = payload.get("name")
            if not name:
                continue

            description = payload.get("trash_description")
            upgrades_allowed = 1 if payload.get("upgradeAllowed", True) else 0
            minimum_custom_format_score = cast(int, payload.get("minFormatScore", 0))
            upgrade_until_score = cast(int, payload.get("cutoffFormatScore", 0))
            upgrade_score_increment = cast(int, payload.get("minUpgradeFormatScore", 1))
            trash_id = cast(str, payload.get("trash_id", ""))
            tags = trash_id_to_groups.get(trash_id, set()).copy()
            quality_groups: dict[str, set[str]] = {}
            qualities: list[QualityProfileQualityEntry] = []

            format_items = payload.get("formatItems", {})
            format_items_dict = cast(dict[str, str], format_items) if isinstance(format_items, dict) else {}
            trash_score_set = cast(str, payload.get("trash_score_set", "default"))

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
                        group_members: set[str] = set()
                        for group_item in group_items:
                            if isinstance(group_item, str):
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

            existing_entry = quality_profiles_by_name.get(cast(str, name))
            if existing_entry is not None:
                existing_entry["tags"].update(tags)
                for group_name, members in quality_groups.items():
                    if group_name not in existing_entry["quality_groups"]:
                        existing_entry["quality_groups"][group_name] = set()
                    existing_entry["quality_groups"][group_name].update(members)
                existing_entry["qualities"].extend(qualities)
                if existing_entry["description"] is None:
                    existing_entry["description"] = cast(str | None, description)
                by_service_value: QualityProfileByServiceEntry = {
                    "format_items": format_items_dict,
                    "trash_score_set": trash_score_set
                }
                existing_entry["by_service"][service_key] = by_service_value
                continue

            quality_profiles_by_name[cast(str, name)] = {
                "name": cast(str, name),
                "description": cast(str | None, description),
                "upgrades_allowed": upgrades_allowed,
                "minimum_custom_format_score": minimum_custom_format_score,
                "upgrade_until_score": upgrade_until_score,
                "upgrade_score_increment": upgrade_score_increment,
                "tags": tags,
                "quality_groups": quality_groups,
                "qualities": qualities,
                "by_service": {
                    service_key: {
                        "format_items": format_items_dict,
                        "trash_score_set": trash_score_set
                    }
                }
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
