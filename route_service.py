from dataclasses import dataclass

import requests
import streamlit as st


@dataclass(frozen=True)
class RouteResult:
    coordinates: list
    distance_km: float | None
    duration_hours: float | None
    is_straight_line: bool


@st.cache_data(ttl=3600, show_spinner=False)
def _request_osrm_route(points):
    coordinates = ";".join(f"{longitude},{latitude}" for longitude, latitude in points)
    url = f"https://router.project-osrm.org/route/v1/driving/{coordinates}"
    response = requests.get(
        url,
        params={"overview": "full", "geometries": "geojson"},
        timeout=10,
    )
    response.raise_for_status()
    data = response.json()
    if data.get("code") != "Ok" or not data.get("routes"):
        raise ValueError("OSRM did not return a route.")

    route = data["routes"][0]
    geometry = route["geometry"]["coordinates"]
    if len(geometry) < 2:
        raise ValueError("OSRM returned an empty route.")

    return (
        [
            [float(longitude), float(latitude)]
            for longitude, latitude in geometry
        ],
        float(route["distance"]) / 1000,
        float(route["duration"]) / 3600,
    )


class RouteService:
    """Fetch road routes from OSRM, with a local straight-line fallback."""

    def get_route(self, points):
        """Return route coordinates, distance in km, duration in hours and fallback status."""
        normalized_points = tuple(
            (float(point[0]), float(point[1])) for point in points
        )
        if len(normalized_points) < 2:
            return RouteResult(
                [list(point) for point in normalized_points], None, None, True
            )

        try:
            coordinates, distance_km, duration_hours = _request_osrm_route(
                normalized_points
            )
        except (requests.RequestException, ValueError, KeyError, TypeError):
            return RouteResult(
                [list(point) for point in normalized_points], None, None, True
            )

        return RouteResult(coordinates, distance_km, duration_hours, False)
