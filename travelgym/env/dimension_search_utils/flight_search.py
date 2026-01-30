import json
import re
from typing import Dict, List

from .common import (
    compare_numeric,
    normalize_value,
    numeric_field_match,
    parse_comparison_conditions,
    parse_numeric_filter,
    tags_partial_match,
)


def filter_flights(
    options: List[Dict[str, object]],
    args: Dict[str, str],
) -> List[Dict[str, object]]:
    if not args:
        return options

    filtered: List[Dict[str, object]] = []
    for option in options:
        if _flight_matches(option, args):
            filtered.append(option)
    return filtered


def _flight_matches(option: Dict[str, object], args: Dict[str, str]) -> bool:
    if "origin" in args or "destination" in args:
        if not _path_match(option, args.get("origin"), args.get("destination")):
            return False
    if "num_layovers" in args and not _num_layovers_match(option, args["num_layovers"]):
        return False
    if "company" in args and not _company_match(option, args["company"]):
        return False
    if "cost" in args and not numeric_field_match(option, "cost", args["cost"]):
        return False
    if "time" in args and not _time_match(option, args["time"]):
        return False
    if "amenities" in args and not _amenities_match(option, args["amenities"]):
        return False
    if "service" in args and not _service_match(option, args["service"]):
        return False
    return True


def _path_match(option: Dict[str, object], origin: str | None, destination: str | None) -> bool:
    if "path" not in option:
        return False
    path = option["path"]
    if not path:
        return False
    if origin is not None and normalize_value(str(path[0])) != normalize_value(origin):
        return False
    if destination is not None and normalize_value(str(path[-1])) != normalize_value(destination):
        return False
    return True


def _num_layovers_match(option: Dict[str, object], filter_value: str) -> bool:
    if "path" not in option:
        return False
    path = option["path"]
    if not path:
        return False
    num_layovers = max(len(path) - 2, 0)
    operator, target = parse_numeric_filter(filter_value)
    return compare_numeric(float(num_layovers), operator, target)


def _company_match(option: Dict[str, object], filter_value: str) -> bool:
    if "company" not in option or not isinstance(option["company"], list):
        return False
    parts = filter_value.strip().split(None, 1)
    if len(parts) != 2:
        return False
    condition, airline = parts
    condition = normalize_value(condition)
    airline_norm = normalize_value(airline)
    companies = [normalize_value(str(name)) for name in option["company"]]
    if condition == "only":
        return all(name == airline_norm for name in companies)
    if condition == "has":
        return airline_norm in companies
    if condition == "no":
        return airline_norm not in companies
    return False


def _time_match(option: Dict[str, object], filter_value: str) -> bool:
    if "time" not in option or not isinstance(option["time"], list):
        return False

    time_list = option["time"]
    if not time_list:
        return False

    value = filter_value.strip()
    match = re.match(r"^(?P<type>\w+)\s*(?P<comparison>(>=|<=|=|>|<).+)$", value)
    if match:
        time_type = match.group("type")
        comparison = match.group("comparison").strip()
    else:
        parts = value.split(None, 1)
        if len(parts) != 2:
            return False
        time_type, comparison = parts
    time_type = normalize_value(time_type)
    operator, target = parse_numeric_filter(comparison)

    flights = [float(time_list[i]) for i in range(0, len(time_list), 2) if _is_number(time_list[i])]
    layovers = [float(time_list[i]) for i in range(1, len(time_list), 2) if _is_number(time_list[i])]

    if time_type == "total":
        return compare_numeric(sum(flights) + sum(layovers), operator, target)
    if time_type == "total_flight":
        return compare_numeric(sum(flights), operator, target)
    if time_type == "total_layover":
        return compare_numeric(sum(layovers), operator, target)
    if time_type == "single_flight":
        return bool(flights) and all(compare_numeric(value, operator, target) for value in flights)
    if time_type == "single_layover":
        return bool(layovers) and all(compare_numeric(value, operator, target) for value in layovers)
    return False


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


def _is_number(value: object) -> bool:
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False


def _parse_args_line(line: str) -> Dict[str, str]:
    args: Dict[str, str] = {}
    for part in [part.strip() for part in line.split(",") if part.strip()]:
        if "=" not in part:
            raise ValueError(f"Invalid argument '{part}'. Expected key=value.")
        key, value = part.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            raise ValueError(f"Invalid argument '{part}'. Empty key.")
        if not value:
            raise ValueError(f"Invalid argument '{part}'. Empty value.")
        if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
            value = value[1:-1]
        args[key] = value
    return args


def _load_options_from_path(path: str) -> List[Dict[str, object]]:
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return [data]
    raise ValueError("Options JSON must be a list or a single object.")
