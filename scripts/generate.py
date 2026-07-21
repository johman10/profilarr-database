import os
import sys
import json
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


class RegexEntry(TypedDict):
    name: str
    pattern: str
    tags: set[str]


class CustomFormatEntry(TypedDict):
    name: str
    description: str | None
    include_in_rename: bool
    tags: set[str]


def sql_escape(value: str) -> str:
    return value.replace("'", "''")


def normalize_name(name: str) -> str:
    return " ".join(name.strip().split())


def ensure_unique_name(base_name: str, used_names: set[str]) -> str:
    candidate = base_name
    index = 2
    while candidate in used_names:
        candidate = f"{base_name} ({index})"
        index += 1
    return candidate


def collect_regexes(input_dir: str) -> list[RegexEntry]:
    regex_by_pattern: dict[str, RegexEntry] = {}
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

    return sorted(regex_by_pattern.values(), key=lambda item: item["name"].lower())


def collect_custom_formats(input_dir: str) -> list[CustomFormatEntry]:
    custom_formats_by_name: dict[str, CustomFormatEntry] = {}

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

            name = normalize_name(f"{tag_name} - {name_raw}")
            description_raw = payload.get("description")
            description = description_raw if isinstance(description_raw, str) and description_raw.strip() else None
            include_in_rename_raw = payload.get("includeCustomFormatWhenRenaming")
            include_in_rename = bool(include_in_rename_raw) if isinstance(include_in_rename_raw, bool) else False

            specification_tags: set[str] = set()
            specifications_raw = payload.get("specifications")
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

            existing_entry = custom_formats_by_name.get(name)
            if existing_entry:
                print(f"Duplicate custom format found {existing_entry} {name}")
                sys.exit(1)
                # existing_entry["tags"].add(tag_name)
                # existing_entry["tags"].update(specification_tags)
                # existing_entry["include_in_rename"] = (
                #     existing_entry["include_in_rename"] or include_in_rename
                # )
                # if existing_entry["description"] is None and description is not None:
                #     existing_entry["description"] = description
                # continue

            custom_formats_by_name[name] = {
                "name": name,
                "description": description,
                "include_in_rename": include_in_rename,
                "tags": {tag_name, *specification_tags},
            }

    return sorted(custom_formats_by_name.values(), key=lambda item: item["name"].lower())

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
        ]:
            f.write(f"INSERT INTO tags (name) VALUES ('{tag_name}');\n")

        regex_entries = collect_regexes(input_dir)
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

        custom_format_entries = collect_custom_formats(input_dir)
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
            escaped_name = sql_escape(entry["name"])
            for tag_name in sorted(entry["tags"]):
                f.write(
                    "INSERT INTO custom_format_tags "
                    "(custom_format_name, tag_name) "
                    f"VALUES ('{escaped_name}', '{tag_name}');\n"
                )


if __name__ == "__main__":
    main()
