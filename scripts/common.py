import re
import sys
from typing import cast

from constants import (
    INDEXER_FLAG_MAPPING,
    LANGUAGE_MAPPING,
    QUALITY_MODIFIER_MAPPING,
    RELEASE_TYPE_MAPPING,
    SOURCE_MAPPING,
)
from models import CustomFormatConditionEntry, ServiceKey


def round_half_up(value: float | int) -> int:
    return int(float(value) + 0.5)


def sql_escape(value: str) -> str:
    return value.replace("'", "''")


def normalize_name(name: str) -> str:
    return " ".join(name.strip().split())


def map_numeric_value(implementation: str, service_key: ServiceKey, numeric_value: int) -> str:
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
    specification_dict: dict[str, object], implementation: str, service_key: ServiceKey
) -> tuple[str | None, bool]:
    fields_raw = specification_dict.get("fields")
    if not isinstance(fields_raw, dict):
        return None, False

    fields_dict = cast(dict[str, object], fields_raw)
    value = fields_dict.get("value")

    parsed_value: str | None = None
    if isinstance(value, int):
        parsed_value = map_numeric_value(implementation, service_key, value)
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
