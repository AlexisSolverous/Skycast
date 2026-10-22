from datetime import date, timedelta

import pytest

from map_view import build_view_state, select_route_endpoints
from models.city import City
from models.trip import Destination
from models.weather import MockWeatherProvider, WeatherCondition
from ui import greeting, group_forecast_by_day


def test_greeting_changes_with_time_of_day():
    assert greeting("Avery", 8) == "Hi, Avery / Good Morning"
    assert greeting("Avery", 14) == "Hi, Avery / Good Afternoon"
    assert greeting("Avery", 20) == "Hi, Avery / Good Evening"
    assert greeting("Avery", 4) == "Hi, Avery / Good Evening"


def test_forecast_groups_readings_into_five_daily_cards():
    today = date.today()
    readings = []
    for offset in range(6):
        forecast_date = (today + timedelta(days=offset)).isoformat()
        for temperature, category in (
            (18 + offset, "Clear"),
            (25 + offset, "Clouds"),
            (21 + offset, "Clouds"),
        ):
            readings.append(
                WeatherCondition(
                    temperature,
                    category.lower(),
                    60,
                    2.0,
                    category,
                    forecast_date=forecast_date,
                )
            )

    grouped = group_forecast_by_day(readings)

    assert len(grouped) == 5
    assert grouped[0] == {
        "date": today,
        "high": 25,
        "low": 18,
        "main_category": "Clouds",
    }


def test_mock_provider_returns_a_five_day_forecast():
    readings = MockWeatherProvider().get_forecast(14.6, 121.0)

    assert len(group_forecast_by_day(readings)) == 5


def test_route_endpoints_follow_travel_date():
    city = City(1, "Example", "Country", 10, 20)
    late = Destination(city, "2026-10-30")
    early = Destination(city, "2026-10-22")
    middle = Destination(city, "2026-10-25")

    start, finish = select_route_endpoints([late, middle, early])

    assert start is early
    assert finish is late


@pytest.fixture
def route_stops():
    return [
        {
            "city_name": "Start City",
            "country": "A",
            "latitude": 10.0,
            "longitude": 20.0,
            "travel_date": "2026-10-22",
            "notes": "",
        },
        {
            "city_name": "Finish City",
            "country": "B",
            "latitude": 30.0,
            "longitude": 40.0,
            "travel_date": "2026-10-24",
            "notes": "",
        },
    ]


def test_whole_route_view_state_fits_all_stops(route_stops):
    view_state = build_view_state(route_stops, bearing=28)

    assert view_state.latitude == 20.0
    assert view_state.longitude == 30.0
    assert view_state.zoom < 12.5
    assert view_state.pitch == 50
    assert view_state.bearing == 28


@pytest.mark.parametrize(
    ("focus_mode", "expected_latitude", "expected_longitude"),
    [("start", 10.0, 20.0), ("finish", 30.0, 40.0)],
)
def test_endpoint_view_state_focuses_selected_stop(
    route_stops, focus_mode, expected_latitude, expected_longitude
):
    view_state = build_view_state(route_stops, focus_mode=focus_mode)

    assert view_state.latitude == expected_latitude
    assert view_state.longitude == expected_longitude
    assert view_state.zoom == 12.5


def test_stop_view_state_uses_selected_focus_point(route_stops):
    view_state = build_view_state(
        route_stops, focus_mode="stop", focus_point=(14.6, 121.0)
    )

    assert view_state.latitude == 14.6
    assert view_state.longitude == 121.0
    assert view_state.zoom == 12.5


def test_stop_view_state_requires_a_focus_point(route_stops):
    with pytest.raises(ValueError, match="focus point is required"):
        build_view_state(route_stops, focus_mode="stop")


def test_empty_routes_do_not_have_endpoints():
    assert select_route_endpoints([]) == (None, None)
