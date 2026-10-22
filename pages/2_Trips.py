from datetime import date

import requests
import streamlit as st

from database.db_handler import DatabaseHandler
from models.alerts import classify_weather
from models.city import City
from models.trip import Destination, Trip
from models.weather import (
    InvalidApiKeyError,
    MockWeatherProvider,
    RateLimitError,
    WeatherApiError,
    WeatherNetworkError,
)
from geocoder import PlaceSearch
from map_view import render_trip_map, select_route_endpoints
from provider_factory import get_provider
from ui import setup_page

setup_page("SkyCast - Trips", "🧭")
st.title("🧭 Trips")

if not st.session_state.get("user"):
    st.warning("Please log in from the Home page first.")
    st.stop()

db = DatabaseHandler()
user = st.session_state.user
provider, is_demo = get_provider()
if is_demo:
    st.info("Demo mode: sample weather is shown. Add an API key for live data.")

flash_message = st.session_state.pop("trips_flash_message", None)
if flash_message:
    st.success(flash_message)


def fetch_weather(latitude, longitude):
    try:
        return provider.get_current_weather(latitude, longitude), is_demo
    except InvalidApiKeyError as exc:
        st.error(str(exc))
        st.info("Showing sample data because the configured API key was rejected.")
        return MockWeatherProvider().get_current_weather(latitude, longitude), True


trips = db.get_trips_for_user(user.id)
st.subheader("Your trips")
if not trips:
    st.info("You have no trips yet. Use the form at the bottom to get started.")
else:
    for trip_row in trips:
        with st.container(border=True):
            st.markdown(f"**{trip_row['trip_name']}**")
            destinations = db.get_destinations_for_trip(trip_row["id"])
            if destinations:
                st.caption(
                    f"{len(destinations)} stop(s) · "
                    f"{destinations[0]['travel_date']} to "
                    f"{destinations[-1]['travel_date']}"
                )
                st.write(
                    " → ".join(
                        f"{destination['city_name']} "
                        f"({destination['travel_date']})"
                        for destination in destinations
                    )
                )
            else:
                st.caption("No destinations yet")

if trips:
    trip_options = {
        f"{trip['trip_name']} (#{trip['id']})": trip["id"] for trip in trips
    }
    chosen_trip_label = st.selectbox(
        "Select a trip to view its itinerary", list(trip_options)
    )
    trip_id = trip_options[chosen_trip_label]
    chosen_trip = next(trip for trip in trips if trip["id"] == trip_id)
    destinations = db.get_destinations_for_trip(trip_id)

    trip = Trip(chosen_trip["trip_name"], user.id, trip_id)
    for row in destinations:
        city = City(
            row["city_id"],
            row["city_name"],
            row["country"],
            row["latitude"],
            row["longitude"],
        )
        trip.add_destination(
            Destination(city, row["travel_date"], row["notes"], row["id"])
        )

    ordered_stops = sorted(
        trip.destinations, key=lambda destination: destination.travel_date
    )
    st.subheader("Itinerary")
    map_focus_key = f"trip_map_focus_{trip_id}"
    if map_focus_key not in st.session_state:
        st.session_state[map_focus_key] = {"mode": "whole_route", "point": None}

    start_stop, finish_stop = select_route_endpoints(ordered_stops)
    if ordered_stops:
        map_column, controls_column = st.columns([4, 1])
        with map_column:
            follow_roads = st.toggle("Follow roads", value=True, key="follow_roads")
            focus = st.session_state[map_focus_key]
            render_trip_map(
                ordered_stops,
                follow_roads=follow_roads,
                focus_mode=focus["mode"],
                focus_point=focus["point"],
            )
        with controls_column:
            st.markdown("**Map view**")
            if st.button("Go to start", key=f"map_start_{trip_id}"):
                st.session_state[map_focus_key] = {
                    "mode": "start",
                    "point": None,
                }
                st.rerun()
            if st.button("Go to finish", key=f"map_finish_{trip_id}"):
                st.session_state[map_focus_key] = {
                    "mode": "finish",
                    "point": None,
                }
                st.rerun()
            if st.button("Show whole route", key=f"map_route_{trip_id}"):
                st.session_state[map_focus_key] = {
                    "mode": "whole_route",
                    "point": None,
                }
                st.rerun()
    else:
        st.info("Add a destination to see your route and itinerary.")

    if not ordered_stops:
        st.info("No destinations yet — add one using the form below.")
    for index, destination in enumerate(ordered_stops):
        is_start = destination is start_stop
        is_finish = destination is finish_stop
        if is_start and is_finish:
            stop_label = "🚩 Start · 🏁 Finish"
        elif is_start:
            stop_label = "🚩 Start"
        elif is_finish:
            stop_label = "🏁 Finish"
        else:
            stop_label = f"Stop {index + 1}"

        header = (
            f"{stop_label} · {destination.city.name}, "
            f"{destination.city.country} — {destination.travel_date}"
        )
        with st.expander(header):
            st.write(destination.notes or "No notes for this stop.")
            if st.button(
                "Zoom to this stop", key=f"zoom_stop_{trip_id}_{destination.id}"
            ):
                st.session_state[map_focus_key] = {
                    "mode": "stop",
                    "point": (
                        destination.city.latitude,
                        destination.city.longitude,
                    ),
                }
                st.rerun()
            col1, col2 = st.columns(2)
            with col1:
                if st.button(
                    "Get weather advisory",
                    key=f"forecast_{destination.id}",
                ):
                    try:
                        condition, using_sample_data = fetch_weather(
                            destination.city.latitude, destination.city.longitude
                        )
                    except (
                        RateLimitError,
                        WeatherApiError,
                        WeatherNetworkError,
                    ) as exc:
                        st.error(f"Could not fetch weather: {exc}")
                    else:
                        if using_sample_data:
                            st.caption("Showing sample data")
                        alert = classify_weather(condition)
                        st.write(
                            f"{condition.temperature:.1f} °C, "
                            f"{condition.description}"
                        )
                        st.info(
                            f"**{alert.label} Advisory:** "
                            f"{alert.advisory(condition)}"
                        )
            with col2:
                if st.button("Remove stop", key=f"remove_{destination.id}"):
                    db.delete_destination(destination.id)
                    st.rerun()

with st.expander("Add a new trip or destination"):
    st.subheader("Add a new trip")
    with st.form("create_trip_form"):
        trip_name = st.text_input(
            "Trip name", placeholder="e.g. Summer Island Hopping"
        )
        create_trip = st.form_submit_button("Create trip")
    if create_trip:
        if not trip_name.strip():
            st.warning("Please enter a trip name.")
        else:
            db.create_trip(user.id, trip_name.strip(), str(date.today()))
            st.session_state["trips_flash_message"] = (
                f"Trip '{trip_name.strip()}' created."
            )
            st.rerun()

    st.subheader("Add a destination")
    if not trips:
        st.info("Create a trip first, then add its destinations.")
    else:
        city_list = db.get_all_cities()
        if not city_list:
            st.warning("There are no cities available yet.")
        else:
            with st.expander("Can't find your city?"):
                place_query = st.text_input(
                    "Search for a place", key="place_search_query"
                )
                if st.button("Search places", key="search_places"):
                    try:
                        st.session_state["place_search_results"] = PlaceSearch().search(
                            place_query
                        )
                    except (requests.RequestException, ValueError) as exc:
                        st.session_state.pop("place_search_results", None)
                        st.error(f"Could not search for places: {exc}")
                    else:
                        if not st.session_state["place_search_results"]:
                            st.info(
                                "No places found. Try a nearby city or a more "
                                "specific name."
                            )

                search_results = st.session_state.get("place_search_results", [])
                if search_results:
                    result_labels = [
                        f"{result['display_name']} "
                        f"({result['latitude']:.4f}, {result['longitude']:.4f})"
                        for result in search_results
                    ]
                    selected_result_label = st.selectbox(
                        "Choose a search result",
                        result_labels,
                        key="selected_place_result",
                    )
                    selected_result = search_results[
                        result_labels.index(selected_result_label)
                    ]
                    if st.button("Add city to my list", key="add_searched_city"):
                        db.add_city(
                            selected_result["name"],
                            selected_result["country"] or "Unknown",
                            selected_result["latitude"],
                            selected_result["longitude"],
                        )
                        st.session_state.pop("place_search_results", None)
                        st.session_state["trips_flash_message"] = (
                            f"Added {selected_result['name']} to your city list."
                        )
                        st.rerun()

            trip_labels = {
                f"{trip_row['trip_name']} (#{trip_row['id']})": trip_row["id"]
                for trip_row in trips
            }
            with st.form("add_destination_form"):
                trip_label = st.selectbox(
                    "Trip", list(trip_labels), key="destination_trip_choice"
                )
                city_labels = [
                    f"{city['name']}, {city['country']}" for city in city_list
                ]
                city_label = st.selectbox("City", city_labels)
                travel_date = st.date_input("Travel date")
                notes = st.text_input("Notes (optional)")
                add_destination = st.form_submit_button("Add destination")

            if add_destination:
                selected_city = city_list[city_labels.index(city_label)]
                db.add_destination(
                    trip_labels[trip_label],
                    selected_city["id"],
                    str(travel_date),
                    notes,
                )
                st.session_state["trips_flash_message"] = (
                    f"Added {selected_city['name']} to the trip."
                )
                st.rerun()
