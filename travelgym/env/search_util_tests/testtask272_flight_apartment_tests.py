import json
import re
from pathlib import Path

from travelgym.env.action_parser import parse_action, perform_search


TEST_TASK_PATH = Path(__file__).with_name("testtask272_flight_apartment.json")


def load_test_task() -> dict:
    with TEST_TASK_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def assert_all(results, predicate, message):
    for item in results:
        assert predicate(item), message


def run_search(task: dict, command: str):
    parsed = parse_action(command)
    assert parsed is not None, f"Failed to parse command: {command}"
    dimension, results = perform_search(task, parsed)
    return dimension, results


def _parse_room(room: str):
    match = re.match(r"^\s*(\d+)\s*B\s*(\d+)\s*B\s*$", str(room), re.IGNORECASE)
    if not match:
        return None, None
    return int(match.group(1)), int(match.group(2))


def test_apartment_search_garden():
    task = load_test_task()
    _, results = run_search(task, "search_apartment(amenities=Garden)")
    assert len(results) == 7
    assert_all(
        results,
        lambda r: any("Garden" in amenity for amenity in r.get("amenities", [])),
        "Garden amenity missing in results.",
    )


def test_apartment_search_num_bedrooms():
    task = load_test_task()
    _, results = run_search(task, "search_apartment(num_bedrooms>=3)")
    assert len(results) == 10
    assert_all(
        results,
        lambda r: (_parse_room(r.get("room"))[0] or 0) >= 3,
        "Bedroom filter failed.",
    )


def test_apartment_search_num_bathrooms():
    task = load_test_task()
    _, results = run_search(task, "search_apartment(num_bathrooms=1)")
    assert len(results) == 5
    assert_all(
        results,
        lambda r: (_parse_room(r.get("room"))[1] or 0) == 1,
        "Bathroom filter failed.",
    )


def test_apartment_search_rating():
    task = load_test_task()
    _, results = run_search(task, "search_apartment(rating>=10)")
    assert len(results) == 5
    assert_all(results, lambda r: r.get("rating", 0) >= 10, "Rating filter failed.")


def test_apartment_search_service_late_checkout():
    task = load_test_task()
    _, results = run_search(task, "search_apartment(service='cost_late_checkout_fee>=50')")
    assert len(results) == 5
    assert_all(
        results,
        lambda r: (r.get("service", {}) or {}).get("cost_late_checkout_fee", 0) is not None
        and (r.get("service", {}) or {}).get("cost_late_checkout_fee", 0) >= 50,
        "Late checkout filter failed.",
    )


def test_flight_search_origin_destination():
    task = load_test_task()
    _, results = run_search(task, "search_flight(origin='New York',destination=Barcelona)")
    assert len(results) == 13
    assert_all(
        results,
        lambda r: r.get("path", [None])[0] == "New York" and r.get("path", [None])[-1] == "Barcelona",
        "Origin/destination filter failed.",
    )


def test_flight_search_num_layovers_zero():
    task = load_test_task()
    _, results = run_search(task, "search_flight(num_layovers=0)")
    assert len(results) == 5
    assert_all(
        results,
        lambda r: len(r.get("path", [])) <= 2,
        "Layover filter failed.",
    )


def test_flight_search_amenities_meal():
    task = load_test_task()
    _, results = run_search(task, "search_flight(amenities='Meal Service')")
    assert len(results) == 10
    assert_all(
        results,
        lambda r: any("Meal Service" in amenity for amenity in r.get("amenities", [])),
        "Meal Service filter failed.",
    )


def test_flight_search_service_business():
    task = load_test_task()
    _, results = run_search(task, "search_flight(service='cost_business_total>=200')")
    assert len(results) == 5
    assert_all(
        results,
        lambda r: (r.get("service", {}) or {}).get("cost_business_total", 0) is not None
        and (r.get("service", {}) or {}).get("cost_business_total", 0) >= 200,
        "Business service filter failed.",
    )


def test_flight_search_company_vueling():
    task = load_test_task()
    _, results = run_search(task, "search_flight(company='has Vueling')")
    assert len(results) == 7
    assert_all(
        results,
        lambda r: "Vueling" in r.get("company", []),
        "Company filter failed.",
    )
