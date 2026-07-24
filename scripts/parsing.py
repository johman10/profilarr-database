import json
from dataclasses import dataclass
from typing import Callable, TypeVar, cast


class ParseError(Exception):
    pass


@dataclass(frozen=True)
class ParseContext:
    file_path: str

    def at(self, key: str) -> str:
        return f"{self.file_path}:{key}"


def load_json_object(file_path: str) -> dict[str, object]:
    with open(file_path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    if not isinstance(payload, dict):
        raise ParseError(f"ERROR: expected JSON object at root in {file_path}")

    return cast(dict[str, object], payload)


T = TypeVar("T")


def require_type(ctx: ParseContext, obj: dict[str, object], key: str, expected_type: type[T]) -> T:
    value = obj.get(key)
    if not isinstance(value, expected_type):
        raise ParseError(
            f"ERROR: expected {key} to be {expected_type.__name__} at {ctx.at(key)}"
        )
    return value


def optional_type(
    obj: dict[str, object],
    key: str,
    expected_type: type[T],
    default: T,
) -> T:
    value = obj.get(key)
    if value is None:
        return default
    if not isinstance(value, expected_type):
        return default
    return value


def parse_list_items(
    value: object,
    item_parser: Callable[[dict[str, object], int], T],
) -> list[T]:
    if not isinstance(value, list):
        return []

    entries: list[T] = []
    for idx, item in enumerate(value):
        if not isinstance(item, dict):
            continue
        entries.append(item_parser(cast(dict[str, object], item), idx))

    return entries


def maybe_dict(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        return {}
    return cast(dict[str, object], value)
