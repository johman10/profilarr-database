import os

import yaml
from markdownify import markdownify

from utils.file_utils import iterate_json_files
from utils.mappings.indexer_flags import INDEXER_FLAG_MAPPING
from utils.mappings.languages import LANGUAGE_MAPPING
from utils.mappings.quality_modifiers import QUALITY_MODIFIER_MAPPING
from utils.mappings.release_type import RELEASE_TYPE_MAPPING
from utils.mappings.source import SOURCE_MAPPING
from utils.strings import get_name


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

IMPLEMENTATION_TO_TYPE_MAPPING = {
    "ReleaseTitleSpecification": "release_title",
    "ResolutionSpecification": "resolution",
    "SourceSpecification": "source",
    "LanguageSpecification": "language",
    "ReleaseGroupSpecification": "release_group",
    "IndexerFlagSpecification": "indexer_flag",
    "QualityModifierSpecification": "quality_modifier",
    "ReleaseTypeSpecification": "release_type",
}

SERVICE_TO_TRASH_GUIDES_URL = {
    "radarr": "https://trash-guides.info/Radarr/Radarr-collection-of-custom-formats",
    "sonarr": "https://trash-guides.info/Sonarr/sonarr-collection-of-custom-formats",
}


def _create_condition_base(service, spec):
    """Create base condition structure from specification."""
    return {
        "name": get_name(service, spec.get("name", "")),
        "negate": spec.get("negate", False),
        "required": spec.get("required", False),
        "type": IMPLEMENTATION_TO_TYPE_MAPPING.get(
            spec.get("implementation"), "unknown"
        ),
    }


def _add_condition_value(
    condition, implementation, spec, *, service, regex_patterns, file_name
):
    """Add implementation-specific value to condition."""
    fields = spec.get("fields", {})
    value = fields.get("value")

    if implementation in ["ReleaseTitleSpecification", "ReleaseGroupSpecification"]:
        pattern_name = regex_patterns["by_pattern"].get(value)["name"]
        if not pattern_name:
            raise ValueError(
                f"Pattern '{value}' not found in collected regex patterns "
                f"for {service} in custom format {file_name}."
            )
        condition["pattern"] = pattern_name
    elif implementation == "ResolutionSpecification":
        condition["resolution"] = f"{value}p"
    elif implementation == "SourceSpecification":
        condition["source"] = SOURCE_MAPPING[service][value]
    elif implementation == "LanguageSpecification":
        condition["language"] = LANGUAGE_MAPPING[service][value]
    elif implementation == "IndexerFlagSpecification":
        condition["flag"] = INDEXER_FLAG_MAPPING[service][value]
    elif implementation == "QualityModifierSpecification":
        condition["qualityModifier"] = QUALITY_MODIFIER_MAPPING[service][value]
    elif implementation == "ReleaseTypeSpecification":
        condition["releaseType"] = RELEASE_TYPE_MAPPING[service][value]
    else:
        return False
    return True


def _collect_custom_format(
    service, file_name, input_json, output_dir, regex_patterns
):
    conditions = []
    implementation_tags = set()
    for spec in input_json.get("specifications", []):
        implementation = spec.get("implementation")
        implementation_tags.add(IMPLEMENTATION_TO_TAG_MAPPING[implementation])

        condition = _create_condition_base(service, spec)
        if not _add_condition_value(
            condition,
            implementation,
            spec,
            service=service,
            regex_patterns=regex_patterns,
            file_name=file_name,
        ):
            print(f"Unrecognised implementation ({implementation}), skipping for now.")
            continue

        conditions.append(condition)

    # Compose YAML structure
    name = input_json.get("name", "")
    yml_data = {
        "name": get_name(service, name),
        "description": f"""[Custom format from TRaSH-Guides.]({SERVICE_TO_TRASH_GUIDES_URL[service]}#{file_name})

{markdownify(input_json.get('description', ''))}""".strip(),
        "tags": [service.capitalize(), *sorted(implementation_tags)],
        "conditions": conditions,
        "tests": [],
    }

    # Include in rename is currently not supported from the file system
    # It would require inserting into the DB
    # TODO: Write a script that can do this?
    # include_in_rename = input_json.get("includeCustomFormatWhenRenaming", False)
    # if include_in_rename:
    #     yml_data["metadata"] = {"includeInRename": include_in_rename}

    # Output path
    output_path = os.path.join(output_dir, f"{get_name(service, name)}.yml")
    with open(output_path, "w", encoding="utf-8") as f:
        yaml.dump(yml_data, f, sort_keys=False, allow_unicode=True)
    print(f"Generated: {output_path}")


def collect_custom_formats(service, input_dir, output_dir, custom_regex_patterns):
    trash_id_to_scoring_mapping = {}
    trash_id_to_name_mapping = {}
    for _, file_stem, data in iterate_json_files(input_dir):
        trash_id = data.get("trash_id")
        name = data.get("name")
        trash_scores = data.get("trash_scores", {})
        if trash_id:
            trash_id_to_scoring_mapping[trash_id] = trash_scores
            trash_id_to_name_mapping[trash_id] = name

        _collect_custom_format(
            service, file_stem, data, output_dir, custom_regex_patterns
        )

    return trash_id_to_scoring_mapping, trash_id_to_name_mapping
