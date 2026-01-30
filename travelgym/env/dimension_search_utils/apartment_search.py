import re
from typing import Dict, List, Tuple

from .common import (
    compare_numeric,
    normalize_value,
    numeric_field_match,
    parse_comparison_conditions,
    parse_numeric_filter,
    tags_partial_match,
)


def filter_apartments(
    options: List[Dict[str, object]],
    args: Dict[str, str],
) -> List[Dict[str, object]]:
    if not args:
        return options

    filtered: List[Dict[str, object]] = []
    for option in options:
        if _apartment_matches(option, args):
            filtered.append(option)
    return filtered


def _apartment_matches(option: Dict[str, object], args: Dict[str, str]) -> bool:
    if "name" in args and not _string_field_match(option, "name", args["name"]):
        return False
    if "num_bedrooms" in args and not _room_match(option, "bedrooms", args["num_bedrooms"]):
        return False
    if "num_bathrooms" in args and not _room_match(option, "bathrooms", args["num_bathrooms"]):
        return False
    if "capacity" in args and not numeric_field_match(option, "capacity", args["capacity"]):
        return False
    if "cost" in args and not numeric_field_match(option, "cost", args["cost"]):
        return False
    if "rating" in args and not numeric_field_match(option, "rating", args["rating"]):
        return False
    if "amenities" in args and not _amenities_match(option, args["amenities"]):
        return False
    if "service" in args and not _service_match(option, args["service"]):
        return False
    return True


def _string_field_match(option: Dict[str, object], key: str, value: str) -> bool:
    if key not in option:
        return False
    return normalize_value(str(option[key])) == normalize_value(value)


def _room_match(option: Dict[str, object], field: str, filter_value: str) -> bool:
    if "room" not in option:
        return False
    room = str(option["room"])
    bedrooms, bathrooms = _parse_room(room)
    if field == "bedrooms":
        actual = bedrooms
    else:
        actual = bathrooms
    if actual is None:
        return False
    operator, target = parse_numeric_filter(filter_value)
    return compare_numeric(actual, operator, target)


def _parse_room(room: str) -> Tuple[float | None, float | None]:
    match = re.match(r"^\s*(\d+)\s*B\s*(\d+)\s*B\s*$", room, re.IGNORECASE)
    if match:
        return float(match.group(1)), float(match.group(2))
    return None, None


def _amenities_match(option: Dict[str, object], filter_value: str) -> bool:
    amenities = option.get("amenities")
    if not isinstance(amenities, list):
        return False
    return tags_partial_match(amenities, filter_value)


def _service_match(option: Dict[str, object], filter_value: str) -> bool:
    service = option.get("service")
    if not isinstance(service, dict):
        return False
    conditions = parse_comparison_conditions(filter_value)
    for key, operator, target in conditions:
        if key not in service:
            return False
        try:
            actual = float(service[key])
        except (TypeError, ValueError):
            return False
        if not compare_numeric(actual, operator, target):
            return False
    return True
