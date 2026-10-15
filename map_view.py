import math

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


def render_trip_map(destinations, follow_roads=False):
    """Render the ordered itinerary as a token-free 3D map."""
    rows = _prepare_destinations(destinations)
    if not rows:
        st.info("Add a destination to see it on the map.")
        return

    stops = []
    for index, row in enumerate(rows):
        row["elevation"] = 1200 + index * 700
        row["label_elevation"] = row["elevation"] + 350
        row["color"] = _COLORS[index % len(_COLORS)]
        stops.append([row["longitude"], row["latitude"]])

    latitude, longitude, zoom = calculate_map_view(
        [(row["latitude"], row["longitude"]) for row in rows]
    )
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
        pdk.Layer(
            "TextLayer",
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
    else:
        layers.append(
            pdk.Layer(
                "ScatterplotLayer",
                data=rows,
                get_position="[longitude, latitude]",
                get_radius=9000,
                get_fill_color="color",
                pickable=True,
            )
        )

    deck = pdk.Deck(
        layers=layers,
        initial_view_state=pdk.ViewState(
            latitude=latitude,
            longitude=longitude,
            zoom=zoom,
            pitch=50,
            bearing=15,
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
