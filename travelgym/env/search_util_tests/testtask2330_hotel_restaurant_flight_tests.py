import json
import re
from pathlib import Path

from travelgym.env.action_parser import parse_action, perform_search


TEST_TASK_PATH = Path(__file__).with_name("testtask2330_hotel_restaurant_flight.json")


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


def test_restaurant_search_fast_food():
    task = load_test_task()
    _, results = run_search(task, "search_restaurant(cuisine='Fast Food')")
    assert len(results) == 4
    assert_all(results, lambda r: r.get("cuisine") == "Fast Food", "Cuisine filter failed.")


def test_restaurant_search_outdoor_seating():
    task = load_test_task()
    _, results = run_search(task, "search_restaurant(tags='Outdoor Seating')")
    assert len(results) == 4
    assert_all(
        results,
        lambda r: any("Outdoor Seating" in tag for tag in r.get("tags", [])),
        "Outdoor Seating filter failed.",
    )


def test_restaurant_search_rating_high():
    task = load_test_task()
    _, results = run_search(task, "search_restaurant(rating>=9)")
    assert len(results) == 4
    assert_all(results, lambda r: r.get("rating", 0) >= 9, "Rating filter failed.")


def test_restaurant_search_reviews_five_star():
    task = load_test_task()
    _, results = run_search(task, "search_restaurant(reviews='5_star>=800')")
    assert len(results) == 4
    assert_all(
        results,
        lambda r: r.get("reviews", {}).get("5_star", 0) >= 800,
        "Reviews filter failed.",
    )


def test_restaurant_search_reviews_extreme():
    task = load_test_task()
    _, results = run_search(task, "search_restaurant(reviews='5_star>=1000')")
    assert len(results) == 2
    assert_all(
        results,
        lambda r: r.get("reviews", {}).get("5_star", 0) >= 1000,
        "Reviews extreme filter failed.",
    )


def test_hotel_search_room_type_double():
    task = load_test_task()
    _, results = run_search(task, "search_hotel(room_type=Double)")
    assert len(results) == 8
    assert_all(
        results,
        lambda h: any(room.get("type") == "Double" for room in h.get("room", [])),
        "Room type filter failed.",
    )


def test_hotel_search_room_capacity():
    task = load_test_task()
    _, results = run_search(task, "search_hotel(room_capacity>=4)")
    assert len(results) == 12
    assert_all(
        results,
        lambda h: any((room.get("capacity") or 0) >= 4 for room in h.get("room", [])),
        "Room capacity filter failed.",
    )


def test_hotel_search_city_view():
    task = load_test_task()
    _, results = run_search(task, "search_hotel(amenities='City View')")
    assert len(results) == 9
    assert_all(
        results,
        lambda h: any("City View" in amenity for amenity in h.get("amenities", [])),
        "City View amenity filter failed.",
    )


def test_hotel_search_rating_range():
    task = load_test_task()
    _, results = run_search(task, "search_hotel(rating>=7)")
    assert len(results) == 12
    assert_all(
        results,
        lambda h: h.get("rating", 0) >= 7,
        "Rating filter failed.",
    )


def test_hotel_search_breakfast_cost():
    task = load_test_task()
    _, results = run_search(task, "search_hotel(service='cost_breakfast_total>=150')")
    assert len(results) == 5
    assert_all(
        results,
        lambda h: (h.get("service", {}) or {}).get("cost_breakfast_total", 0) is not None
        and (h.get("service", {}) or {}).get("cost_breakfast_total", 0) >= 150,
        "Breakfast service filter failed.",
    )


def test_flight_search_origin_destination():
    task = load_test_task()
    _, results = run_search(task, "search_flight(origin='Los Angeles',destination='New York City')")
    assert len(results) == 15
    assert_all(
        results,
        lambda f: f.get("path", [None])[0] == "Los Angeles" and f.get("path", [None])[-1] == "New York City",
        "Origin/destination filter failed.",
    )


def test_flight_search_num_layovers():
    task = load_test_task()
    _, results = run_search(task, "search_flight(num_layovers=1)")
    assert len(results) == 14
    assert_all(
        results,
        lambda f: len(f.get("path", [])) == 3,
        "Num layovers filter failed.",
    )


def test_flight_search_meal_service():
    task = load_test_task()
    _, results = run_search(task, "search_flight(amenities='Meal Service')")
    assert len(results) == 10
    assert_all(
        results,
        lambda f: any("Meal Service" in amenity for amenity in f.get("amenities", [])),
        "Meal Service filter failed.",
    )


def test_flight_search_business_service():
    task = load_test_task()
    _, results = run_search(task, "search_flight(service='cost_business_total>=200')")
    assert len(results) == 8
    assert_all(
        results,
        lambda f: (f.get("service", {}) or {}).get("cost_business_total", 0) is not None
        and (f.get("service", {}) or {}).get("cost_business_total", 0) >= 200,
        "Business service filter failed.",
    )


def test_flight_search_total_layover_short():
    task = load_test_task()
    _, results = run_search(task, "search_flight(time='total_layover<=1')")
    assert len(results) == 8

