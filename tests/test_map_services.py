from unittest.mock import Mock, patch

import requests

from geocoder import PlaceSearch, _search_nominatim
from map_view import calculate_map_view
from route_service import RouteService, _request_osrm_route


def clear_route_cache():
    _request_osrm_route.clear()


def test_osrm_success_returns_route_distance_and_duration():
    clear_route_cache()
    points = ((121.0, 14.6), (120.9, 14.5))
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "code": "Ok",
        "routes": [
            {
                "geometry": {"coordinates": [[121.0, 14.6], [120.95, 14.55], [120.9, 14.5]]},
                "distance": 12345,
                "duration": 7200,
            }
        ],
    }

    with patch("route_service.requests.get", return_value=response) as get:
        result = RouteService().get_route(points)

    assert result.coordinates == [
        [121.0, 14.6],
        [120.95, 14.55],
        [120.9, 14.5],
    ]
    assert result.distance_km == 12.345
    assert result.duration_hours == 2
    assert not result.is_straight_line
    request_url = get.call_args.args[0]
    assert "121.0,14.6;120.9,14.5" in request_url
    assert get.call_args.kwargs["params"] == {
        "overview": "full",
        "geometries": "geojson",
    }
    assert get.call_args.kwargs["timeout"] == 10


def test_osrm_failure_falls_back_to_straight_line():
    clear_route_cache()
    points = ((-74.0, 40.7), (139.7, 35.7))
    with patch(
        "route_service.requests.get",
        side_effect=requests.Timeout("request timed out"),
    ):
        result = RouteService().get_route(points)

    assert result.coordinates == [[-74.0, 40.7], [139.7, 35.7]]
    assert result.distance_km is None
    assert result.duration_hours is None
    assert result.is_straight_line


def test_nominatim_results_are_parsed_and_include_country():
    _search_nominatim.clear()
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = [
        {
            "name": "Example City",
            "display_name": "Example City, Example County, Exampleland",
            "lat": "12.5",
            "lon": "-45.25",
            "address": {"country": "Exampleland"},
        },
        {
            "display_name": "Unnamed place",
            "lat": "13",
            "lon": "-46",
            "address": {},
        },
    ]
    with patch("geocoder.requests.get", return_value=response) as get:
        results = PlaceSearch().search("Example City")

    assert results == [
        {
            "name": "Example City",
            "country": "Exampleland",
            "latitude": 12.5,
            "longitude": -45.25,
            "display_name": "Example City, Example County, Exampleland",
        },
        {
            "name": "Unnamed place",
            "country": "",
            "latitude": 13.0,
            "longitude": -46.0,
            "display_name": "Unnamed place",
        },
    ]
    assert get.call_args.kwargs["headers"]["User-Agent"] == "SkyCast-SchoolProject"
    assert get.call_args.kwargs["params"]["format"] == "json"
    assert get.call_args.kwargs["params"]["limit"] == 5
    assert get.call_args.kwargs["timeout"] == 10


def test_map_center_and_zoom_fit_coordinates():
    single = calculate_map_view([(14.6, 121.0)])
    assert single == (14.6, 121.0, 9)

    nearby = calculate_map_view([(14.6, 121.0), (14.7, 121.2)])
    distant = calculate_map_view([(14.6, 121.0), (35.7, 139.7)])

    assert nearby[:2] == (14.649999999999999, 121.1)
    assert distant[:2] == ((14.6 + 35.7) / 2, (121.0 + 139.7) / 2)
    assert 1 <= distant[2] < nearby[2] <= 12
