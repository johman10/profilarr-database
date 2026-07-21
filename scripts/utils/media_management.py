import json
import os

import yaml

from utils.mappings.misc_media_management import MISC_MEDIA_MANAGEMENT
from utils.sql_generator import SQLBuffer


BASE_NAMING_CONFIG = {
    "radarr": {
        "rename": True,
        "movieFormat": "",
        "movieFolderFormat": "",
        "replaceIllegalCharacters": False,
        "colonReplacementFormat": "smart",
    },
    "sonarr": {
        "rename": True,
        "standardEpisodeFormat": "",
        "dailyEpisodeFormat": "",
        "animeEpisodeFormat": "",
        "seriesFolderFormat": "",
        "seasonFolderFormat": "",
        "replaceIllegalCharacters": False,
        "colonReplacementFormat": 4,
        "customColonReplacementFormat": "",
        "multiEpisodeStyle": 5,
    },
}
BASE_QUALITY_DEFINITIONS = {"qualityDefinitions": {"radarr": {}, "sonarr": {}}}


def _collect_misc_config(output_dir):
    output_file = os.path.join(output_dir, "misc.yml")

    with open(output_file, "w", encoding="utf-8") as f:
        yaml.dump(MISC_MEDIA_MANAGEMENT, f, sort_keys=False, allow_unicode=True)

    print(f"Generated: {output_file}")


def _collect_naming_formats(input_dir, output_dir):
    output_file = os.path.join(output_dir, "naming.yml")
    new_config = BASE_NAMING_CONFIG.copy()

    radarr_input_file_path = os.path.join(
        input_dir, "radarr", "naming", "radarr-naming.json"
    )
    with open(radarr_input_file_path, encoding="utf-8") as f:
        input_json = json.load(f)
        new_config["radarr"]["movieFormat"] = input_json["file"]["standard"]
        new_config["radarr"]["movieFolderFormat"] = input_json["folder"]["default"]

    sonarr_input_file_path = os.path.join(
        input_dir, "sonarr", "naming", "sonarr-naming.json"
    )
    with open(sonarr_input_file_path, encoding="utf-8") as f:
        input_json = json.load(f)
        standard_episode_format = input_json["episodes"]["standard"]["default"]
        daily_episode_format = input_json["episodes"]["daily"]["default"]
        anime_episode_format = input_json["episodes"]["anime"]["default"]
        new_config["sonarr"]["standardEpisodeFormat"] = standard_episode_format
        new_config["sonarr"]["dailyEpisodeFormat"] = daily_episode_format
        new_config["sonarr"]["animeEpisodeFormat"] = anime_episode_format
        new_config["sonarr"]["seriesFolderFormat"] = input_json["series"]["default"]
        new_config["sonarr"]["seasonFolderFormat"] = input_json["season"]["default"]

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(
            yaml.dump(new_config, sort_keys=False, allow_unicode=True, width=1000000)
        )

    print(f"Generated: {output_file}")


def _collect_quality_definitions(input_dir, output_dir):
    output_structure = BASE_QUALITY_DEFINITIONS.copy()
    output_file = os.path.join(output_dir, "quality_definitions.yml")

    radarr_input_file_path = os.path.join(
        input_dir, "radarr", "quality-size", "movie.json"
    )
    with open(radarr_input_file_path, encoding="utf-8") as f:
        radarr_data = json.load(f)
        for quality in reversed(radarr_data["qualities"]):
            profilarr_quality = {
                "max": quality["max"],
                "min": quality["min"],
                "preferred": quality["preferred"],
            }
            output_structure["qualityDefinitions"]["radarr"][
                quality["quality"]
            ] = profilarr_quality

    sonarr_input_file_path = os.path.join(
        input_dir, "sonarr", "quality-size", "series.json"
    )
    with open(sonarr_input_file_path, encoding="utf-8") as f:
        sonarr_data = json.load(f)
        for quality in reversed(sonarr_data["qualities"]):
            profilarr_quality = {
                "max": quality["max"],
                "min": quality["min"],
                "preferred": quality["preferred"],
            }
            output_structure["qualityDefinitions"]["sonarr"][
                quality["quality"]
            ] = profilarr_quality

    with open(output_file, "w", encoding="utf-8") as f:
        yaml.dump(output_structure, f, sort_keys=False, allow_unicode=True)

    print(f"Generated: {output_file}")


def collect_media_management(input_dir, output_dir, sql_buffer=None):
    """
    Collect media management settings.

    For now, media management is kept as YAML output files
    since Profilarr PCD format details for media settings need clarification.

    Args:
        input_dir: Input directory with media management specs
        output_dir: Output directory for YAML files
        sql_buffer: SQLBuffer instance (currently unused for media management)
    """
    _collect_misc_config(output_dir)
    _collect_naming_formats(input_dir, output_dir)
    _collect_quality_definitions(input_dir, output_dir)
