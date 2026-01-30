from typing import Dict, List

from .common import (
    normalize_value,
    numeric_field_match,
    parse_comparison_conditions,
    compare_numeric,
)


def filter_rental_cars(
    options: List[Dict[str, object]],
    args: Dict[str, str],
) -> List[Dict[str, object]]:
    if not args:
        return options

    filtered: List[Dict[str, object]] = []
    for option in options:
        if _rental_car_matches(option, args):
            filtered.append(option)
    return filtered


def _rental_car_matches(option: Dict[str, object], args: Dict[str, str]) -> bool:
    if "brand" in args and not _string_field_match(option, "brand", args["brand"]):
        return False
    if "model" in args and not _string_field_match(option, "model", args["model"]):
        return False
    if "categories" in args and not _string_field_match(option, "categories", args["categories"]):
        return False
    if "seats" in args and not numeric_field_match(option, "seats", args["seats"]):
        return False
    if "cost" in args and not numeric_field_match(option, "cost", args["cost"]):
        return False
    if "insurance" in args and not _insurance_match(option, args["insurance"]):
        return False
    if "service" in args and not _service_match(option, args["service"]):
        return False
    return True


def _string_field_match(option: Dict[str, object], key: str, value: str) -> bool:
    if key not in option:
        return False
    return normalize_value(str(option[key])) == normalize_value(value)


def _insurance_match(option: Dict[str, object], filter_value: str) -> bool:
    insurance = option.get("insurance")
    if not isinstance(insurance, dict):
        return False
    conditions = parse_comparison_conditions(filter_value)
    for key, operator, target in conditions:
        if key not in insurance:
            return False
        try:
            actual = float(insurance[key])
        except (TypeError, ValueError):
            return False
        if not compare_numeric(actual, operator, target):
            return False
    return True


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
