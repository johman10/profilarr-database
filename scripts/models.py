from enum import StrEnum
from typing import TypedDict


class ServiceKey(StrEnum):
    SONARR = "sonarr"
    RADARR = "radarr"

    @classmethod
    def all(cls) -> tuple["ServiceKey", ...]:
        return tuple(cls)


type ByServiceEntry[T] = dict[ServiceKey, T]


class RegexEntry(TypedDict):
    name: str
    pattern: str
    tags: set[str]


class CustomFormatServiceEntry(TypedDict):
    trash_id: str
    trash_scores: dict[str, int]


type CustomFormatByServiceEntry = ByServiceEntry[CustomFormatServiceEntry]


class CustomFormatConditionEntry(TypedDict):
    name: str
    type: str
    arr_type: ServiceKey
    negate: bool
    required: bool
    value: str | None
    except_value: bool


class CustomFormatEntry(TypedDict):
    name: str
    description: str | None
    include_in_rename: bool
    tags: set[str]
    conditions: list[CustomFormatConditionEntry]
    by_service: CustomFormatByServiceEntry


class QualityProfileByServiceEntry(TypedDict):
    format_items: dict[str, str]
    trash_score_set: str


class QualityProfileQualityEntry(TypedDict):
    quality_name: str | None
    quality_group_name: str | None
    position: int
    enabled: bool
    upgrade_until: bool


class QualityProfileEntry(TypedDict):
    name: str
    description: str | None
    upgrades_allowed: int
    minimum_custom_format_score: int
    upgrade_until_score: int
    upgrade_score_increment: int
    tags: set[str]
    quality_groups: dict[str, set[str]]
    qualities: list[QualityProfileQualityEntry]
    by_service: ByServiceEntry[QualityProfileByServiceEntry]


class QualityDefinitionEntry(TypedDict):
    name: str
    quality_name: str
    min_size: int
    max_size: int
    preferred_size: int


class RadarrNamingEntry(TypedDict):
    name: str
    movie_format: str
    movie_folder_format: str


class SonarrNamingEntry(TypedDict):
    name: str
    standard_episode_format: str
    daily_episode_format: str
    anime_episode_format: str
    series_folder_format: str
    season_folder_format: str
