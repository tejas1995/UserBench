import json
import re
from dataclasses import dataclass
from typing import Dict, List, Tuple

from .utils import OPTION_SCHEMAS
from .dimension_search_utils import (
    filter_flights,
    filter_restaurants,
    filter_rental_cars,
    filter_apartments,
    filter_hotels,
)


class ActionParseError(ValueError):
    pass


@dataclass(frozen=True)
class ParsedAction:
    name: str
    args: Dict[str, str]


ACTION_SPECS = {
    "search_flight": {
        "dimension": "flight",
        "required_args": [],
        "allowed_args": [
            "origin",
            "destination",
            "num_layovers",
            "company",
            "cost",
            "time",
            "amenities",
            "service",
        ],
    },
    "search_restaurant": {
        "dimension": "restaurant",
        "required_args": [],
        "allowed_args": [
            "name",
            "cuisine",
            "expectation",
            "rating",
            "reviews",
            "tags",
        ],
    },
    "search_apartment": {
        "dimension": "apartment",
        "required_args": [],
        "allowed_args": [
            "name",
            "num_bedrooms",
            "num_bathrooms",
            "capacity",
            "cost",
            "rating",
            "amenities",
            "service",
        ],
    },
    "search_hotel": {
        "dimension": "hotel",
        "required_args": [],
        "allowed_args": [
            "name",
            "amenities",
            "rating",
            "cost",
            "service",
            "room_capacity",
            "room_type",
        ],
    },
    "search_car_rental": {
        "dimension": "rental_car",
        "required_args": [],
        "allowed_args": [
            "brand",
            "model",
            "categories",
            "seats",
            "cost",
            "insurance",
            "service",
        ],
    },
}


def parse_action(action_str: str) -> ParsedAction | None:
    action_str = action_str.strip()
    for name in ACTION_SPECS:
        if action_str.startswith(name):
            remainder = action_str[len(name):].strip()
            args = _parse_args(remainder)
            _validate_required_args(name, args)
            return ParsedAction(name=name, args=args)
    return None


def build_search_feedback(
    dimension: str,
    options: List[Dict[str, object]],
    args: Dict[str, str],
    unknown_args: List[str],
) -> str:
    warning = ""
    if unknown_args:
        warning = f"Ignored unsupported arguments: {', '.join(unknown_args)}.\n\n"
    if args:
        conditions = ", ".join(f"{key}={value}" for key, value in args.items())
        if options:
            header = f"Here are the {len(options)} {dimension}s that match the conditions {conditions}:\n"
        else:
            header = f"No {dimension}s matching the conditions {conditions} were found."
    else:
        header = f"Here are all {len(options)} {dimension} options:\n"
    feedback = warning + header
    for option in options:
        feedback += f"{json.dumps(option)}\n"
    return feedback.strip()


def perform_search(task: Dict[str, object], parsed_action: ParsedAction) -> Tuple[str, List[Dict[str, object]]]:
    spec = ACTION_SPECS[parsed_action.name]
    dimension = spec["dimension"]
    allowed_args = set(spec.get("allowed_args", []))
    unknown_args = [key for key in parsed_action.args.keys() if key not in allowed_args]

    options = task.get("all_options", {}).get(dimension, [])
    if dimension == "flight":
        options = filter_flights(options, parsed_action.args)
    elif dimension == "restaurant":
        options = filter_restaurants(options, parsed_action.args)
    elif dimension == "apartment":
        options = filter_apartments(options, parsed_action.args)
    elif dimension == "hotel":
        options = filter_hotels(options, parsed_action.args)
    elif dimension == "rental_car":
        options = filter_rental_cars(options, parsed_action.args)

    return dimension, options, unknown_args


def _parse_args(remainder: str) -> Dict[str, str]:
    if not remainder:
        raise ActionParseError("Missing arguments.")

    if remainder.startswith("(") and remainder.endswith(")"):
        inner = remainder[1:-1].strip()
        if not inner:
            raise ActionParseError("Empty argument list.")
        return _parse_key_value_pairs(inner)

    raise ActionParseError("Arguments must be provided in parentheses.")


def _parse_key_value_pairs(inner: str) -> Dict[str, str]:
    parts = _split_args(inner)
    args: Dict[str, str] = {}
    for part in parts:
        match = re.match(r"^(?P<key>[A-Za-z_]\w*)\s*(>=|<=|=|>|<)\s*(?P<value>.+)$", part)
        if not match:
            raise ActionParseError(f"Invalid argument '{part}'. Expected key=value or key>=value.")
        key = match.group("key").strip()
        operator = match.group(2)
        value = match.group("value").strip()
        if not key:
            raise ActionParseError(f"Invalid argument '{part}'. Empty key.")
        if not value:
            raise ActionParseError(f"Invalid argument '{part}'. Empty value.")
        value = _strip_quotes(value)
        if operator != "=":
            value = f"{operator}{value}"
        args[key] = value
    return args


def _strip_quotes(value: str) -> str:
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    return value


def _split_args(text: str) -> List[str]:
    parts: List[str] = []
    current: List[str] = []
    in_single = False
    in_double = False
    for char in text:
        if char == "'" and not in_double:
            in_single = not in_single
            current.append(char)
            continue
        if char == '"' and not in_single:
            in_double = not in_double
            current.append(char)
            continue
        if char == "," and not in_single and not in_double:
            part = "".join(current).strip()
            if part:
                parts.append(part)
            current = []
            continue
        current.append(char)
    part = "".join(current).strip()
    if part:
        parts.append(part)
    return parts


def _validate_required_args(action_name: str, args: Dict[str, str]) -> None:
    required = ACTION_SPECS[action_name]["required_args"]
    missing = [key for key in required if key not in args]
    if missing:
        raise ActionParseError(f"Missing required arguments: {', '.join(missing)}")
