import math
from urllib.parse import quote

import pydeck as pdk
import streamlit as st


CARTO_VOYAGER_STYLE = (
    "https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json"
)
_COLORS = [
    [37, 99, 235, 220],
    [234, 88, 12, 220],
    [22, 163, 74, 220],
    [147, 51, 234, 220],
    [219, 39, 119, 220],
    [8, 145, 178, 220],
]
_START_COLOR = [22, 163, 74, 240]
_FINISH_COLOR = [15, 23, 42, 240]


def _svg_data_url(svg):
    return f"data:image/svg+xml;charset=utf-8,{quote(svg, safe='')}"


_ICON_MAPPING = {
    "start": {
        "url": _svg_data_url(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48">'
            '<path d="M10 4v40" stroke="#166534" stroke-width="4"/>'
            '<path d="M12 6h27l-6 8 6 8H12z" fill="#16a34a" '
            'stroke="#fff" stroke-width="2" stroke-linejoin="round"/>'
            "</svg>"
        ),
        "width": 48,
        "height": 48,
        "anchorY": 44,
    },
    "finish": {
        "url": _svg_data_url(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48">'
            '<path d="M10 4v40" stroke="#111827" stroke-width="4"/>'
            '<path d="M12 6h28v22H12z" fill="#fff" stroke="#111827" '
            'stroke-width="2"/>'
            '<path d="M12 6h9v7h-9zm18 0h10v7H30zM21 13h9v7h-9z'
            'm9 7h10v8H30z" fill="#111827"/>'
            "</svg>"
        ),
        "width": 48,
        "height": 48,
        "anchorY": 44,
    },
}


def _destination_value(destination, key):
    """Read a value from either a database row or a Destination object."""
    if isinstance(destination, dict) or hasattr(destination, "keys"):
        return destination[key]

    if key == "city_name":
        return destination.city.name
    if key == "country":
        return destination.city.country
    if key == "latitude":
        return destination.city.latitude
    if key == "longitude":
        return destination.city.longitude
    return getattr(destination, key)


def _prepare_destinations(destinations):
    rows = []
    for destination in destinations:
        rows.append(
            {
                "city_name": str(_destination_value(destination, "city_name")),
                "country": str(_destination_value(destination, "country")),
                "latitude": float(_destination_value(destination, "latitude")),
                "longitude": float(_destination_value(destination, "longitude")),
                "travel_date": str(_destination_value(destination, "travel_date")),
                "notes": str(_destination_value(destination, "notes") or ""),
            }
        )

    return sorted(rows, key=lambda row: row["travel_date"])


def select_route_endpoints(destinations):
    """Return the original first and last stops by travel date."""
    ordered = sorted(
        destinations,
        key=lambda destination: str(_destination_value(destination, "travel_date")),
    )
    if not ordered:
        return None, None
    return ordered[0], ordered[-1]


def calculate_map_view(coordinates):
    """Return (latitude, longitude, zoom) that fits coordinate pairs."""
    latitudes = [float(point[0]) for point in coordinates]
    longitudes = [float(point[1]) for point in coordinates]
    south, north = min(latitudes), max(latitudes)
    west, east = min(longitudes), max(longitudes)
    center_lat = (south + north) / 2
    center_lon = (west + east) / 2

    if len(coordinates) == 1:
        return center_lat, center_lon, 9

    # Web Mercator fitting needs latitude converted to its projected y value.
    def mercator_y(latitude):
        bounded_latitude = max(min(latitude, 85.0511), -85.0511)
        radians = math.radians(bounded_latitude)
        return math.log(math.tan(math.pi / 4 + radians / 2))

    projected_span = abs(mercator_y(north) - mercator_y(south))
    longitude_span = east - west
    if longitude_span == 0 and projected_span == 0:
        zoom = 9
    else:
        # Estimate a padded zoom for a 900x550 map; lower values fit wider trips.
        available_width, available_height = 720, 400
        zoom_candidates = []
        if longitude_span > 0:
            zoom_candidates.append(
                math.log2(available_width * 360 / (256 * longitude_span))
            )
        if projected_span > 0:
            zoom_candidates.append(
                math.log2(available_height * 2 * math.pi / (256 * projected_span))
            )
        zoom = max(1, min(12, min(zoom_candidates)))

    return center_lat, center_lon, zoom


def build_view_state(
    destinations,
    focus_mode="whole_route",
    focus_point=None,
    bearing=15,
):
    """Create a map view for the whole route or a selected stop."""
    rows = _prepare_destinations(destinations)
    if focus_mode == "stop":
        if focus_point is None:
            raise ValueError("focus point is required for stop view")
        latitude, longitude = map(float, focus_point)
        zoom = 12.5
    elif focus_mode in ("start", "finish"):
        if not rows:
            raise ValueError("cannot focus an empty route")
        stop = rows[0] if focus_mode == "start" else rows[-1]
        latitude = stop["latitude"]
        longitude = stop["longitude"]
        zoom = 12.5
    elif focus_mode == "whole_route":
        if not rows:
            raise ValueError("cannot fit an empty route")
        latitude, longitude, zoom = calculate_map_view(
            [(row["latitude"], row["longitude"]) for row in rows]
        )
    else:
        raise ValueError(f"unsupported map focus mode: {focus_mode}")

    return pdk.ViewState(
        latitude=latitude,
        longitude=longitude,
        zoom=zoom,
        pitch=50,
        bearing=bearing,
    )


def render_trip_map(
    destinations,
    follow_roads=False,
    focus_mode="whole_route",
    focus_point=None,
    bearing=15,
):
    """Render the ordered itinerary as a token-free 3D map."""
    rows = _prepare_destinations(destinations)
    if not rows:
        st.info("Add a destination to see it on the map.")
        return

    stops = []
    for index, row in enumerate(rows):
        row["elevation"] = 1200 + index * 700
        row["label_elevation"] = row["elevation"] + 350
        if index == 0:
            row["color"] = _START_COLOR
        elif index == len(rows) - 1:
            row["color"] = _FINISH_COLOR
        else:
            row["color"] = _COLORS[index % len(_COLORS)]
        stops.append([row["longitude"], row["latitude"]])

    layers = [
        pdk.Layer(
            "ColumnLayer",
            data=rows,
            get_position="[longitude, latitude]",
            get_elevation="elevation",
            elevation_scale=1,
            radius=14000,
            get_fill_color="color",
            extruded=True,
            pickable=True,
            coverage=0.8,
            auto_highlight=True,
        ),
    ]

    route_note = None
    # A single stop is shown as a marker; connect the itinerary only when needed.
    if len(rows) >= 2:
        route_points = stops
        if follow_roads:
            from route_service import RouteService

            route_result = RouteService().get_route(stops)
            route_points = route_result.coordinates
            if route_result.is_straight_line:
                route_note = "Straight-line route"
            else:
                route_note = (
                    f"Road route: {route_result.distance_km:.1f} km, "
                    f"about {route_result.duration_hours:.1f} hours."
                )
        else:
            route_note = "Straight-line route (Follow roads is off)"

        layers.append(
            pdk.Layer(
                "PathLayer",
                data=[{"path": route_points}],
                get_path="path",
                get_color=[37, 99, 235, 190],
                width_scale=20,
                width_min_pixels=3,
                pickable=False,
            )
        )

    if len(rows) > 2:
        layers.append(
            pdk.Layer(
                "ScatterplotLayer",
                id="route-stop-markers",
                data=rows[1:-1],
                get_position="[longitude, latitude]",
                get_radius=7000,
                get_fill_color="color",
                pickable=True,
            )
        )

    endpoint_rows = [
        {
            **rows[0],
            "icon_id": "start",
            "size": 52,
            "route_label": "START",
            "label_color": _START_COLOR,
        }
    ]
    if len(rows) > 1:
        endpoint_rows.append(
            {
                **rows[-1],
                "icon_id": "finish",
                "size": 52,
                "route_label": "FINISH",
                "label_color": [255, 255, 255, 255],
            }
        )

    # Keep colored markers and labels underneath the SVG icons as a visible fallback.
    layers.extend(
        [
            pdk.Layer(
                "ScatterplotLayer",
                id="route-endpoint-fallback",
                data=endpoint_rows,
                get_position="[longitude, latitude]",
                get_radius=11000,
                get_fill_color="color",
                stroked=True,
                get_line_color=[255, 255, 255, 255],
                line_width_min_pixels=2,
                pickable=True,
            ),
            pdk.Layer(
                "TextLayer",
                id="route-endpoint-labels",
                data=endpoint_rows,
                get_position="[longitude, latitude, label_elevation]",
                get_text="route_label",
                get_size=16,
                size_units="pixels",
                get_color="label_color",
                get_text_anchor="middle",
                get_alignment_baseline="bottom",
                billboard=True,
                pickable=False,
            ),
            pdk.Layer(
                "IconLayer",
                id="route-endpoint-icons",
                data=endpoint_rows,
                get_icon="icon_id",
                icon_mapping=_ICON_MAPPING,
                get_position="[longitude, latitude]",
                get_size="size",
                size_units="pixels",
                pickable=True,
                billboard=True,
            ),
            pdk.Layer(
                "TextLayer",
                id="route-city-labels",
                data=rows,
                get_position="[longitude, latitude, label_elevation]",
                get_text="city_name",
                get_size=16,
                size_units="pixels",
                get_color=[25, 35, 50, 255],
                get_text_anchor="middle",
                get_alignment_baseline="bottom",
                billboard=True,
                pickable=False,
            ),
        ]
    )

    deck = pdk.Deck(
        layers=layers,
        initial_view_state=build_view_state(
            rows,
            focus_mode=focus_mode,
            focus_point=focus_point,
            bearing=bearing,
        ),
        map_style=CARTO_VOYAGER_STYLE,
        tooltip={
            "text": (
                "{city_name}, {country}\n"
                "Date: {travel_date}\n"
                "Notes: {notes}"
            )
        },
    )
    st.pydeck_chart(deck, height=550)
    if route_note:
        st.caption(route_note)
