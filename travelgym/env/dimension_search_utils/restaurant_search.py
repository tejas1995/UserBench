from typing import Dict, List

from .common import (
    numeric_field_match,
    parse_comparison_conditions,
    compare_numeric,
    string_field_match,
    tags_partial_match,
)


def filter_restaurants(
    options: List[Dict[str, object]],
    args: Dict[str, str],
) -> List[Dict[str, object]]:
    if not args:
        return options

    filtered: List[Dict[str, object]] = []
    for option in options:
        if _restaurant_matches(option, args):
            filtered.append(option)
    return filtered


def _restaurant_matches(option: Dict[str, object], args: Dict[str, str]) -> bool:
    if "name" in args and not string_field_match(option, "name", args["name"]):
        return False
    if "cuisine" in args and not string_field_match(option, "cuisine", args["cuisine"]):
        return False
    if "expectation" in args and not string_field_match(option, "expectation", args["expectation"]):
        return False
    if "rating" in args and not numeric_field_match(option, "rating", args["rating"]):
        return False
    if "reviews" in args and not _reviews_match(option, args["reviews"]):
        return False
    if "tags" in args and not _tags_match(option, args["tags"]):
        return False
    return True


def _reviews_match(option: Dict[str, object], filter_value: str) -> bool:
    reviews = option.get("reviews")
    if not isinstance(reviews, dict):
        return False

    conditions = parse_comparison_conditions(filter_value)
    for key, operator, target in conditions:
        if key not in reviews:
            return False
        try:
            actual = float(reviews[key])
        except (TypeError, ValueError):
            return False
        if not compare_numeric(actual, operator, target):
            return False
    return True


def _tags_match(option: Dict[str, object], filter_value: str) -> bool:
    tags = option.get("tags")
    if not isinstance(tags, list):
        return False
    return tags_partial_match(tags, filter_value)
