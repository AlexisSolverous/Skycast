from datetime import date

import streamlit as st

from database.db_handler import DatabaseHandler
from models.alerts import classify_weather
from models.weather import (
    InvalidApiKeyError,
    MockWeatherProvider,
    RateLimitError,
    WeatherApiError,
    WeatherNetworkError,
)
from provider_factory import get_api_key_diagnostics, get_provider

st.set_page_config(page_title="SkyCast - Dashboard", page_icon="🌦️")

if not st.session_state.get("user"):
    st.warning("Please log in from the Home page first.")
    st.stop()

db = DatabaseHandler()
user = st.session_state.user
provider, is_demo = get_provider()

st.title("🌦️ Trip dashboard")

if is_demo:
    st.info(
        "Demo mode: showing sample weather. Add an OpenWeatherMap key in "
        "`.streamlit/secrets.toml` for live data."
    )


def fetch_weather(latitude, longitude):
    try:
        return provider.get_current_weather(latitude, longitude), is_demo
    except InvalidApiKeyError as exc:
        st.error(str(exc))
        st.info("Showing sample data because the configured API key was rejected.")
        return MockWeatherProvider().get_current_weather(latitude, longitude), True


st.subheader("OpenWeatherMap API key")
if st.button("Test my API key"):
    diagnostics = get_api_key_diagnostics()
    st.write(
        f"secrets.toml found: {'Yes' if diagnostics['secrets_file_found'] else 'No'}"
    )
    st.write(f"Key detected: {'Yes' if diagnostics['key_detected'] else 'No'}")
    st.write(f"Key length: {diagnostics['key_length']}")

    if not diagnostics["key_detected"]:
        st.warning("Invalid or not yet active: no API key was detected.")
        st.write("HTTP status code: N/A")
    else:
        try:
            provider.get_current_weather(14.5995, 120.9842)
        except InvalidApiKeyError as exc:
            st.error(f"Invalid or not yet active: {exc}")
            st.write(f"HTTP status code: {exc.status_code}")
        except RateLimitError as exc:
            st.warning(str(exc))
            st.write(f"HTTP status code: {exc.status_code}")
        except WeatherNetworkError as exc:
            st.error(str(exc))
            st.write("HTTP status code: N/A")
        except WeatherApiError as exc:
            st.error(str(exc))
            st.write(f"HTTP status code: {exc.status_code}")
        else:
            st.success("Key works")
            st.write(f"HTTP status code: {provider.last_status_code}")

today = date.today()
trips = db.get_trips_for_user(user.id)
trip_details = []
upcoming_trips = []

for trip in trips:
    destinations = db.get_destinations_for_trip(trip["id"])
    travel_dates = [date.fromisoformat(row["travel_date"]) for row in destinations]
    trip_details.append((trip, destinations, travel_dates))

    future_dates = [travel_date for travel_date in travel_dates if travel_date >= today]
    if future_dates:
        upcoming_trips.append((min(future_dates), trip["trip_name"]))

st.subheader("Next upcoming trip")
if upcoming_trips:
    upcoming_date, upcoming_name = min(upcoming_trips)
    st.info(f"**{upcoming_name}** — {upcoming_date.strftime('%b %d, %Y')}")
else:
    st.write("You have no upcoming trips.")

st.subheader("Your trips")
if not trip_details:
    st.write("You have no trips yet. Create one in Trips.")

for trip, destinations, travel_dates in trip_details:
    with st.container(border=True):
        st.markdown(f"**{trip['trip_name']}**")
        if travel_dates:
            date_range = (
                f"{min(travel_dates).strftime('%b %d, %Y')} – "
                f"{max(travel_dates).strftime('%b %d, %Y')}"
            )
        else:
            date_range = "No travel dates yet"

        col1, col2 = st.columns(2)
        col1.metric("Stops", len(destinations))
        col2.metric("Travel dates", date_range)

    with st.expander(f"Manage {trip['trip_name']}"):
        if not destinations:
            st.write("No destinations added yet.")
        else:
            for destination in destinations:
                note = f" — {destination['notes']}" if destination["notes"] else ""
                st.write(
                    f"- {destination['city_name']}, {destination['country']} "
                    f"on {destination['travel_date']}{note}"
                )

        new_name = st.text_input(
            "Rename trip",
            value=trip["trip_name"],
            key=f"rename_trip_{trip['id']}",
        )
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Save name", key=f"save_trip_{trip['id']}"):
                db.rename_trip(trip["id"], new_name)
                st.success("Renamed.")
                st.rerun()
        with col2:
            if st.button("Delete trip", key=f"delete_trip_{trip['id']}"):
                db.delete_trip(trip["id"])
                st.success("Deleted.")
                st.rerun()

st.subheader("Today's weather")
cities = db.get_all_cities()
if not cities:
    st.warning("No cities are available for a weather lookup.")
else:
    home_city = min(cities, key=lambda city: city["id"])
    st.caption(
        f"Using {home_city['name']}, {home_city['country']} as the temporary "
        "default until you choose a home city in Settings."
    )

    if st.button("Refresh today's weather", key="refresh_home_weather"):
        st.session_state.pop("dashboard_home_weather", None)

    weather_result = st.session_state.get("dashboard_home_weather")
    if (
        weather_result is None
        or weather_result[0] != user.id
        or weather_result[1] != home_city["id"]
    ):
        with st.spinner("Fetching today's weather..."):
            try:
                condition, using_sample_data = fetch_weather(
                    home_city["latitude"], home_city["longitude"]
                )
            except (RateLimitError, WeatherApiError, WeatherNetworkError) as exc:
                weather_result = (user.id, home_city["id"], None, str(exc), False)
            else:
                weather_result = (
                    user.id,
                    home_city["id"],
                    condition,
                    None,
                    using_sample_data,
                )
            st.session_state["dashboard_home_weather"] = weather_result

    _, _, condition, weather_error, using_sample_data = weather_result
    if weather_error:
        st.error(f"Could not fetch today's weather: {weather_error}")
    else:
        with st.container(border=True):
            st.markdown(f"**{home_city['name']}, {home_city['country']}**")
            if using_sample_data:
                st.caption("Showing sample data")
            col1, col2, col3 = st.columns(3)
            col1.metric("Temperature", f"{condition.temperature:.1f} °C")
            col2.metric("Humidity", f"{condition.humidity}%")
            col3.metric("Wind speed", f"{condition.wind_speed} m/s")
            st.write(f"**Condition:** {condition.description.title()}")

st.subheader("Alerts")
with st.container(border=True):
    st.info("No weather alerts to show yet.")

with st.expander("Quick weather check"):
    cities = db.get_all_cities()
    if not cities:
        st.warning("No cities are available for a weather lookup.")
    else:
        city_labels = [f"{city['name']}, {city['country']}" for city in cities]
        choice = st.selectbox("Choose a city", city_labels)
        selected_city = cities[city_labels.index(choice)]

        st.caption(
            f"GPS coordinates: {selected_city['latitude']:.4f}, "
            f"{selected_city['longitude']:.4f}"
        )

        if st.button("Check weather", type="primary"):
            with st.spinner("Fetching weather..."):
                try:
                    condition, using_sample_data = fetch_weather(
                        selected_city["latitude"], selected_city["longitude"]
                    )
                except (RateLimitError, WeatherApiError, WeatherNetworkError) as exc:
                    st.error(f"Could not fetch weather: {exc}")
                else:
                    if using_sample_data:
                        st.caption("Showing sample data")
                    alert = classify_weather(condition)
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Temperature", f"{condition.temperature:.1f} °C")
                    col2.metric("Humidity", f"{condition.humidity}%")
                    col3.metric("Wind speed", f"{condition.wind_speed} m/s")
                    st.write(f"**Condition:** {condition.description.title()}")
                    st.info(f"**{alert.label} Advisory:** {alert.advisory(condition)}")
                    st.map(
                        {
                            "lat": [selected_city["latitude"]],
                            "lon": [selected_city["longitude"]],
                        }
                    )
