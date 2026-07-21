import os

from utils.file_utils import iterate_json_files
from utils.sql_generator import SQLBuffer
from utils.strings import get_name


regex_patterns = {
    "by_name": {},
    "by_pattern": {},
}


def _update_existing_pattern_for_service(existing_data, service):
    """Update existing pattern tracking for multiple services."""
    if service.capitalize() not in existing_data.get("services", []):
        existing_data["services"].append(service.capitalize())


def _generate_unique_pattern_name(initial_name, pattern):
    """Generate a unique pattern name if there are collisions."""
    final_name = initial_name
    counter = 1
    normalized_key = final_name.lower()

    while normalized_key in regex_patterns["by_name"]:
        existing_pattern_data = regex_patterns["by_name"][normalized_key]
        if existing_pattern_data["pattern"] == pattern:
            return None
        final_name = f"{initial_name} ({counter})"
        normalized_key = final_name.lower()
        counter += 1

    return final_name


def _add_new_pattern(service, pattern, final_name):
    """Add new pattern to tracking."""
    pattern_data = {
        "name": final_name,
        "pattern": pattern,
        "services": [service.capitalize()],
    }
    regex_patterns["by_name"][final_name.lower()] = pattern_data
    regex_patterns["by_pattern"][pattern] = pattern_data
    return True


def _collect_regex_pattern(service, file_name, input_json):
    """Extract and collect regex patterns from specifications."""
    for spec in input_json.get("specifications", []):
        implementation = spec.get("implementation")
        if implementation not in [
            "ReleaseTitleSpecification",
            "ReleaseGroupSpecification",
        ]:
            continue

        pattern = spec.get("fields", {}).get("value")
        if not pattern:
            continue

        spec_name = spec.get("name", "")

        if pattern in regex_patterns["by_pattern"]:
            existing_data = regex_patterns["by_pattern"][pattern]
            if service.capitalize() not in existing_data.get("services", []):
                _update_existing_pattern_for_service(existing_data, service)
            continue

        initial_name = get_name(service, spec_name, remove_not=True, skip_service_prefix=True)
        final_name = _generate_unique_pattern_name(initial_name, pattern)

        if final_name:
            _add_new_pattern(service, pattern, final_name)


def collect_regex_patterns(service, input_dir, sql_buffer=None):
    """
    Collect regex patterns and add to SQL buffer.

    Args:
        service: Service name (radarr/sonarr)
        input_dir: Input directory with pattern specs
        sql_buffer: SQLBuffer instance to collect SQL statements

    Returns:
        dict: Collected regex patterns
    """
    for _, file_stem, data in iterate_json_files(input_dir):
        _collect_regex_pattern(service, file_stem, data)

    if sql_buffer:
        for pattern_data in sorted(
            regex_patterns["by_pattern"].values(),
            key=lambda x: x["name"].lower(),
        ):
            sql_buffer.add_insert(
                "regular_expressions",
                ["name", "pattern", "regex101_id", "description"],
                [
                    pattern_data["name"],
                    pattern_data["pattern"],
                    None,
                    None,
                ],
                section="REGULAR EXPRESSIONS",
            )

    return regex_patterns
