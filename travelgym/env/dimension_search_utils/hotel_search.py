from typing import Dict, List

from .common import (
    compare_numeric,
    normalize_value,
    parse_comparison_conditions,
    parse_numeric_filter,
    tags_partial_match,
)


def filter_hotels(
    options: List[Dict[str, object]],
    args: Dict[str, str],
) -> List[Dict[str, object]]:
    if not args:
        return options

    filtered: List[Dict[str, object]] = []
    for option in options:
        if _hotel_matches(option, args):
            filtered.append(option)
    return filtered


def _hotel_matches(option: Dict[str, object], args: Dict[str, str]) -> bool:
    if "name" in args and not _string_field_match(option, "name", args["name"]):
        return False
    if "amenities" in args and not _amenities_match(option, args["amenities"]):
        return False
    if "rating" in args and not _numeric_field_match(option, "rating", args["rating"]):
        return False
    if "cost" in args and not _cost_match(option, args["cost"]):
        return False
    if "room_capacity" in args and not _room_capacity_match(option, args["room_capacity"]):
        return False
    if "room_type" in args and not _room_type_match(option, args["room_type"]):
        return False
    if "service" in args and not _service_match(option, args["service"]):
        return False
    return True


def _string_field_match(option: Dict[str, object], key: str, value: str) -> bool:
    if key not in option:
        return False
    return normalize_value(str(option[key])) == normalize_value(value)


def _numeric_field_match(option: Dict[str, object], key: str, value: str) -> bool:
    if key not in option:
        return False
    try:
        option_value = float(option[key])
    except (TypeError, ValueError):
        return False
    operator, target_value = parse_numeric_filter(value)
    return compare_numeric(option_value, operator, target_value)


def _amenities_match(option: Dict[str, object], filter_value: str) -> bool:
    amenities = option.get("amenities")
    if not isinstance(amenities, list):
        return False
    return tags_partial_match(amenities, filter_value)


def _cost_match(option: Dict[str, object], filter_value: str) -> bool:
    costs = option.get("cost")
    if not isinstance(costs, list):
        return False
    operator, target = parse_numeric_filter(filter_value)
    for cost in costs:
        try:
            actual = float(cost)
        except (TypeError, ValueError):
            continue
        if compare_numeric(actual, operator, target):
            return True
    return False


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


def _room_capacity_match(option: Dict[str, object], filter_value: str) -> bool:
    rooms = option.get("room")
    if not isinstance(rooms, list):
        return False
    operator, target = parse_numeric_filter(filter_value)
    for room in rooms:
        if not isinstance(room, dict):
            continue
        if "capacity" not in room:
            continue
        try:
            actual = float(room["capacity"])
        except (TypeError, ValueError):
            continue
        if compare_numeric(actual, operator, target):
            return True
    return False


def _room_type_match(option: Dict[str, object], filter_value: str) -> bool:
    rooms = option.get("room")
    if not isinstance(rooms, list):
        return False
    desired = normalize_value(filter_value)
    for room in rooms:
        if not isinstance(room, dict):
            continue
        if "type" not in room:
            continue
        if normalize_value(str(room["type"])) == desired:
            return True
    return False
