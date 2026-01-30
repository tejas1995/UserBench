import re
from typing import Dict, List, Tuple


def normalize_value(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip()).lower()


def parse_numeric_filter(value: str) -> Tuple[str, float]:
    value = value.strip()
    operators = [">=", "<=", ">", "<", "="]
    for operator in operators:
        if value.startswith(operator):
            number_str = value[len(operator):].strip()
            return operator, float(number_str)
    return "=", float(value)


def compare_numeric(actual: float, operator: str, target: float) -> bool:
    if operator == ">=":
        return actual >= target
    if operator == "<=":
        return actual <= target
    if operator == ">":
        return actual > target
    if operator == "<":
        return actual < target
    return actual == target


def parse_comparison_conditions(value: str) -> List[Tuple[str, str, float]]:
    conditions: List[Tuple[str, str, float]] = []
    raw_conditions = [part.strip() for part in re.split(r"[;,]", value) if part.strip()]
    for raw in raw_conditions:
        match = re.match(r"^(?P<key>\w+)\s*(>=|<=|=|>|<)\s*(?P<num>\d+(\.\d+)?)$", raw)
        if not match:
            raise ValueError(
                "Invalid filter. Use format like 'field>=100,other=0'."
            )
        key = match.group("key")
        operator = match.group(2)
        number = float(match.group("num"))
        conditions.append((key, operator, number))
    return conditions


def tags_partial_match(tag_list: List[object], filter_value: str) -> bool:
    desired_tags = [tag.strip() for tag in re.split(r"[|,]", filter_value) if tag.strip()]
    if not desired_tags:
        return False
    for tag in desired_tags:
        desired = normalize_value(tag)
        matched = False
        for option_tag in tag_list:
            if desired in normalize_value(str(option_tag)):
                matched = True
                break
        if not matched:
            return False
    return True


def string_field_match(option: Dict[str, object], key: str, value: str) -> bool:
    if key not in option:
        return False
    return normalize_value(str(option[key])) == normalize_value(value)


def numeric_field_match(option: Dict[str, object], key: str, value: str) -> bool:
    if key not in option:
        return False
    try:
        option_value = float(option[key])
    except (TypeError, ValueError):
        return False
    operator, target_value = parse_numeric_filter(value)
    return compare_numeric(option_value, operator, target_value)
