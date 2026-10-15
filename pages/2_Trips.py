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
from map_view import render_trip_map
from provider_factory import get_provider

st.set_page_config(page_title="SkyCast - Trips", page_icon="🧭")
st.title("🧭 Trips")

if not st.session_state.get("user"):
    st.warning("Please log in from the Home page first.")
    st.stop()

db = DatabaseHandler()
user = st.session_state.user
provider, is_demo = get_provider()
if is_demo:
    st.info("Demo mode: sample weather is shown. Add an API key for live data.")


def fetch_weather(latitude, longitude):
    try:
        return provider.get_current_weather(latitude, longitude), is_demo
    except InvalidApiKeyError as exc:
        st.error(str(exc))
        st.info("Showing sample data because the configured API key was rejected.")
        return MockWeatherProvider().get_current_weather(latitude, longitude), True


st.subheader("1. Start a new trip")
trip_name = st.text_input("Trip name", placeholder="e.g. Summer Island Hopping")
if st.button("Create Trip") and trip_name:
    db.create_trip(user.id, trip_name, str(date.today()))
    st.success(f"Trip '{trip_name}' created.")
    st.rerun()

trips = db.get_trips_for_user(user.id)
if not trips:
    st.write("You have no trips yet. Create one above to get started.")
    st.stop()

trip_options = {t["trip_name"]: t["id"] for t in trips}
chosen_trip_name = st.selectbox("2. Select a trip to edit", list(trip_options.keys()))
trip_id = trip_options[chosen_trip_name]

st.subheader("3. Add a destination")
cities = db.get_all_cities()
city_labels = [f"{c['name']}, {c['country']}" for c in cities]
city_choice = st.selectbox("City", city_labels)
selected_city = cities[city_labels.index(city_choice)]

with st.expander("Can't find your city?"):
    place_query = st.text_input("Search for a place", key="place_search_query")
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
                st.info("No places found. Try a nearby city or a more specific name.")

    search_results = st.session_state.get("place_search_results", [])
    if search_results:
        result_labels = [
            f"{result['display_name']} ({result['latitude']:.4f}, "
            f"{result['longitude']:.4f})"
            for result in search_results
        ]
        selected_result_label = st.selectbox(
            "Choose a search result",
            result_labels,
            key="selected_place_result",
        )
        selected_result = search_results[result_labels.index(selected_result_label)]
        if st.button("Add city to my list", key="add_searched_city"):
            city_id = db.add_city(
                selected_result["name"],
                selected_result["country"] or "Unknown",
                selected_result["latitude"],
                selected_result["longitude"],
            )
            st.session_state.pop("place_search_results", None)
            st.success(
                f"Added {selected_result['name']} to your city list "
                f"(city ID {city_id})."
            )
            st.rerun()

travel_date = st.date_input("Travel date")
notes = st.text_input("Notes (optional)")

if st.button("Add to Trip"):
    db.add_destination(trip_id, selected_city["id"], str(travel_date), notes)
    st.success(f"Added {selected_city['name']} to the trip.")
    st.rerun()

st.subheader("4. Itinerary")

# Build an in-memory Trip object out of the database rows.
# COMPOSITION in action: the Trip is made up of Destination objects,
# and each Destination is made up of a City.
trip = Trip(chosen_trip_name, user.id, trip_id)
for row in db.get_destinations_for_trip(trip_id):
    city = City(row["city_id"], row["city_name"], row["country"],
                row["latitude"], row["longitude"])
    trip.add_destination(Destination(city, row["travel_date"], row["notes"], row["id"]))

if trip.total_stops() == 0:
    st.write("No destinations yet — add one above.")
else:
    st.caption(f"{trip.total_stops()} stop(s) on this trip")
    follow_roads = st.toggle("Follow roads", value=True, key="follow_roads")
    render_trip_map(trip.destinations, follow_roads=follow_roads)
    for destination in trip.destinations:
        header = f"{destination.city.name}, {destination.city.country} — {destination.travel_date}"
        with st.expander(header):
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Get weather advisory", key=f"forecast_{destination.id}"):
                    try:
                        condition, using_sample_data = fetch_weather(
                            destination.city.latitude, destination.city.longitude
                        )
                    except (RateLimitError, WeatherApiError, WeatherNetworkError) as exc:
                        st.error(f"Could not fetch weather: {exc}")
                    else:
                        if using_sample_data:
                            st.caption("Showing sample data")
                        alert = classify_weather(condition)
                        st.write(f"{condition.temperature:.1f} °C, {condition.description}")
                        st.info(f"**{alert.label} Advisory:** {alert.advisory(condition)}")
            with col2:
                if st.button("Remove stop", key=f"remove_{destination.id}"):
                    db.delete_destination(destination.id)
                    st.rerun()
