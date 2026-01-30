import json
from pathlib import Path

from travelgym.env.action_parser import parse_action, perform_search


TEST_TASK_PATH = Path(__file__).with_name("testtask733_rentalcar_restaurant.json")


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


def test_restaurant_search_cuisine():
    task = load_test_task()
    _, results = run_search(task, "search_restaurant(cuisine=Vegetarian)")
    assert len(results) == 3
    assert_all(results, lambda r: r.get("cuisine") == "Vegetarian", "Non-vegetarian result returned.")


def test_restaurant_search_tags_partial():
    task = load_test_task()
    _, results = run_search(task, "search_restaurant(tags='Late Night')")
    assert len(results) == 3
    assert_all(
        results,
        lambda r: any("Late Night" in tag for tag in r.get("tags", [])),
        "Late-night tag missing in results.",
    )


def test_restaurant_search_rating():
    task = load_test_task()
    _, results = run_search(task, "search_restaurant(rating>=9)")
    assert len(results) == 4
    assert_all(results, lambda r: r.get("rating", 0) >= 9, "Rating filter failed.")


def test_restaurant_search_expectation():
    task = load_test_task()
    _, results = run_search(task, "search_restaurant(expectation=Cheap)")
    assert len(results) == 3
    assert_all(results, lambda r: r.get("expectation") == "Cheap", "Expectation filter failed.")


def test_restaurant_search_reviews():
    task = load_test_task()
    _, results = run_search(task, "search_restaurant(reviews='5_star>=200')")
    assert len(results) == 4
    assert_all(
        results,
        lambda r: r.get("reviews", {}).get("5_star", 0) >= 200,
        "Reviews filter failed.",
    )

def test_rental_car_search_brand():
    task = load_test_task()
    _, results = run_search(task, "search_car_rental(brand=Tesla)")
    assert len(results) == 3
    assert_all(results, lambda r: r.get("brand") == "Tesla", "Non-Tesla result returned.")


def test_rental_car_search_categories():
    task = load_test_task()
    _, results = run_search(task, "search_car_rental(categories=Electric)")
    assert len(results) == 6
    assert_all(results, lambda r: r.get("categories") == "Electric", "Non-electric result returned.")


def test_rental_car_search_seats():
    task = load_test_task()
    _, results = run_search(task, "search_car_rental(seats>=7)")
    assert len(results) == 3
    assert_all(results, lambda r: r.get("seats", 0) >= 7, "Seats filter failed.")


def test_rental_car_search_cost():
    task = load_test_task()
    _, results = run_search(task, "search_car_rental(cost<=500)")
    assert len(results) == 7
    assert_all(results, lambda r: r.get("cost", 0) <= 500, "Cost filter failed.")


def test_rental_car_search_insurance():
    task = load_test_task()
    _, results = run_search(task, "search_car_rental(insurance='cost_belonging_waiver>=75')")
    assert len(results) == 7
    assert_all(
        results,
        lambda r: (r.get("insurance", {}) or {}).get("cost_belonging_waiver", 0) is not None
        and (r.get("insurance", {}) or {}).get("cost_belonging_waiver", 0) >= 75,
        "Insurance filter failed.",
    )
