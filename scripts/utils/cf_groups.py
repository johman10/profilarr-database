import os

from utils.file_utils import iterate_json_files


def collect_cf_groups(service, cf_groups_dir):
    """
    Collect default CF-groups and map to quality profiles.

    Returns:
        dict[profile_trash_id, list[cf_trash_id]]: Mapping of profiles to additional CFs
    """
    if not os.path.exists(cf_groups_dir):
        print(f"CF-groups directory {cf_groups_dir} does not exist, skipping.")
        return {}

    profile_to_cfs = {}  # {profile_trash_id: [cf_trash_id, ...]}

    for _, _, data in iterate_json_files(cf_groups_dir):
        # Check group-level default
        if data.get("default") != "true":
            continue

        # Collect CFs with CF-level default
        default_cf_ids = []
        for cf in data.get("custom_formats", []):
            if cf.get("default") is True:  # Note: boolean, not string
                default_cf_ids.append(cf["trash_id"])

        if not default_cf_ids:
            continue  # No default CFs in this group

        # Map to quality profiles
        for _profile_name, profile_trash_id in data.get("quality_profiles", {}).get("include", {}).items():
            if profile_trash_id not in profile_to_cfs:
                profile_to_cfs[profile_trash_id] = []
            profile_to_cfs[profile_trash_id].extend(default_cf_ids)

    # Deduplicate CF lists per profile
    for profile_id in profile_to_cfs:
        profile_to_cfs[profile_id] = list(set(profile_to_cfs[profile_id]))

    print(f"Collected {len(profile_to_cfs)} profiles with default CF-groups for {service}")
    return profile_to_cfs
