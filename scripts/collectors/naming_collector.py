import os
from typing import cast

from models import RadarrNamingEntry, SonarrNamingEntry
from parsing import load_json_object


def collect_radarr_naming_patterns(input_dir: str) -> list[RadarrNamingEntry]:
    naming_entries: list[RadarrNamingEntry] = []

    naming_file = os.path.join(input_dir, "radarr", "naming", "radarr-naming.json")
    if not os.path.isfile(naming_file):
        return naming_entries

    payload = load_json_object(naming_file)

    folder_formats = cast(dict[str, str], payload.get("folder", {})) if isinstance(payload.get("folder"), dict) else {}
    file_formats = cast(dict[str, str], payload.get("file", {})) if isinstance(payload.get("file"), dict) else {}

    default_folder_format = folder_formats.get("default", "")

    for file_name, file_format in sorted(file_formats.items()):
        folder_format = folder_formats.get(file_name, None)

        if folder_format is None:
            base_name = file_name.split("-")[0]
            for folder_key in sorted(folder_formats.keys()):
                if folder_key.startswith(base_name) and folder_key != "default":
                    folder_format = folder_formats[folder_key]
                    break

        if folder_format is None:
            folder_format = default_folder_format

        naming_entries.append({
            "name": file_name,
            "movie_format": file_format,
            "movie_folder_format": folder_format,
        })

    return naming_entries


def collect_sonarr_naming_patterns(input_dir: str) -> list[SonarrNamingEntry]:
    naming_entries: list[SonarrNamingEntry] = []

    naming_file = os.path.join(input_dir, "sonarr", "naming", "sonarr-naming.json")
    if not os.path.isfile(naming_file):
        return naming_entries

    payload = load_json_object(naming_file)

    season_formats = cast(dict[str, str], payload.get("season", {})) if isinstance(payload.get("season"), dict) else {}
    series_formats = cast(dict[str, str], payload.get("series", {})) if isinstance(payload.get("series"), dict) else {}
    episodes_data = payload.get("episodes", {})

    default_season_format = season_formats.get("default", "Season {season:00}")
    if not isinstance(episodes_data, dict):
        return naming_entries

    episodes_dict = cast(dict[str, object], episodes_data)

    episode_formats_by_type: dict[str, dict[str, str]] = {}

    for episode_type_name, episode_formats_raw in episodes_dict.items():
        if not isinstance(episode_formats_raw, dict):
            continue

        episode_formats = cast(dict[str, str], episode_formats_raw)
        episode_formats_by_type[episode_type_name] = episode_formats

    def resolve_format(formats: dict[str, str], format_name: str, default_value: str) -> str:
        format_value = formats.get(format_name)
        if format_value is not None:
            return format_value

        base_name = format_name.split("-")[0]
        for format_key in sorted(formats.keys()):
            if format_key.startswith(base_name) and format_key != "default":
                return formats[format_key]

        return default_value

    for format_name, series_format in sorted(series_formats.items()):
        standard_episode_format = resolve_format(
            episode_formats_by_type.get("standard", {}),
            format_name,
            episode_formats_by_type.get("standard", {}).get("default", ""),
        )
        daily_episode_format = resolve_format(
            episode_formats_by_type.get("daily", {}),
            format_name,
            episode_formats_by_type.get("daily", {}).get("default", ""),
        )
        anime_episode_format = resolve_format(
            episode_formats_by_type.get("anime", {}),
            format_name,
            episode_formats_by_type.get("anime", {}).get("default", ""),
        )
        season_folder_format = resolve_format(season_formats, format_name, default_season_format)

        naming_entries.append({
            "name": format_name,
            "standard_episode_format": standard_episode_format,
            "daily_episode_format": daily_episode_format,
            "anime_episode_format": anime_episode_format,
            "series_folder_format": series_format,
            "season_folder_format": season_folder_format,
        })

    return naming_entries
