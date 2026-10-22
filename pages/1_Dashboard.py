from datetime import date

import streamlit as st

from auth_session import initialize_auth
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
from ui import card, group_forecast_by_day, greeting, setup_page, weather_icon

setup_page("SkyCast - Dashboard", "🌦️")

db = DatabaseHandler()
user = initialize_auth(db)
if not user:
    st.warning("Please log in from the Home page first.")
    st.stop()

provider, is_demo = get_provider()

today = date.today()
trips = db.get_trips_for_user(user.id)
trip_details = []
all_destinations = []
upcoming_trips = []

for trip in trips:
    destinations = db.get_destinations_for_trip(trip["id"])
    travel_dates = [date.fromisoformat(row["travel_date"]) for row in destinations]
    trip_details.append((trip, destinations, travel_dates))
    all_destinations.extend(destinations)

    future_dates = [travel_date for travel_date in travel_dates if travel_date >= today]
    if future_dates:
        upcoming_trips.append((min(future_dates), trip["trip_name"]))

all_destinations.sort(key=lambda destination: destination["travel_date"])
cities = db.get_all_cities()
if all_destinations:
    home_city = all_destinations[0]
elif cities:
    # Use the first seeded city as a useful default until a home-city setting exists.
    first_city = min(cities, key=lambda city: city["id"])
    home_city = {
        "id": first_city["id"],
        "city_id": first_city["id"],
        "city_name": first_city["name"],
        "country": first_city["country"],
        "latitude": first_city["latitude"],
        "longitude": first_city["longitude"],
    }
else:
    home_city = None

if st.button("Refresh weather"):
    st.session_state.pop("dashboard_weather_cache", None)

if is_demo:
    st.info("Demo mode: sample weather is shown. No API key is needed.")


def load_weather(city, forecast=False):
    """Reuse readings during reruns so widgets do not repeat API requests."""
    cache = st.session_state.setdefault("dashboard_weather_cache", {})
    key = (
        user.id,
        float(city["latitude"]),
        float(city["longitude"]),
        "forecast" if forecast else "current",
    )
    if key in cache:
        return cache[key]

    try:
        if forecast:
            result = provider.get_forecast(city["latitude"], city["longitude"])
        else:
            result = provider.get_current_weather(city["latitude"], city["longitude"])
    except InvalidApiKeyError as exc:
        st.error(str(exc))
        mock_provider = MockWeatherProvider()
        result = (
            mock_provider.get_forecast(city["latitude"], city["longitude"])
            if forecast
            else mock_provider.get_current_weather(
                city["latitude"], city["longitude"]
            )
        )
        value = (result, None, True)
    except (RateLimitError, WeatherApiError, WeatherNetworkError) as exc:
        value = (None, str(exc), False)
    else:
        value = (result, None, is_demo)

    cache[key] = value
    return value


st.markdown(f"### {greeting(user.username)}")
st.caption("Your trips and local weather, together in one place.")

left_column, right_column = st.columns([1, 2])

with left_column:
    with card("Current weather"):
        if home_city is None:
            st.info("No cities are available yet. Add a destination from Trips.")
        else:
            condition, weather_error, sample_data = load_weather(home_city)
            st.markdown(
                f"**{home_city['city_name']}, {home_city['country']}**"
            )
            st.caption(today.strftime("%A, %B %d, %Y").replace(" 0", " "))
            if weather_error:
                st.error(f"Could not fetch current weather: {weather_error}")
            elif condition:
                icon_column, temperature_column = st.columns([1, 2])
                with icon_column:
                    st.markdown(
                        f'<div class="skycast-weather-icon">'
                        f'{weather_icon(condition.main_category)}</div>',
                        unsafe_allow_html=True,
                    )
                with temperature_column:
                    st.markdown(
                        f'<div class="skycast-temperature">'
                        f'{condition.temperature:.0f}°</div>',
                        unsafe_allow_html=True,
                    )
                st.write(condition.description.capitalize())
                if sample_data:
                    st.caption("Showing sample data")
                alert = classify_weather(condition)
                st.info(f"**{alert.label} advisory:** {alert.advisory(condition)}")

    with card("Other places"):
        other_places = []
        seen_city_ids = {home_city["city_id"]} if home_city else set()
        for destination in all_destinations:
            city_id = destination["city_id"]
            if city_id not in seen_city_ids:
                seen_city_ids.add(city_id)
                other_places.append(destination)
            if len(other_places) == 4:
                break

        if other_places:
            for place in other_places:
                condition, weather_error, sample_data = load_weather(place)
                place_column, temperature_column = st.columns([3, 2])
                with place_column:
                    st.write(
                        f"{weather_icon(condition.main_category) if condition else '🌡️'} "
                        f"**{place['city_name']}**"
                    )
                    st.caption(place["country"])
                with temperature_column:
                    if weather_error:
                        st.caption("Weather unavailable")
                    elif condition:
                        st.markdown(f"**{condition.temperature:.0f}°C**")
                        if sample_data:
                            st.caption("Sample")
        else:
            st.info("Your trip destinations will appear here.")
        st.page_link("pages/2_Trips.py", label="View and plan trips")

with right_column:
    with card("Today's highlights"):
        if home_city is None:
            st.info("Add a city to see today's weather highlights.")
        else:
            condition, weather_error, _ = load_weather(home_city)
            if weather_error:
                st.info("Weather highlights are unavailable right now.")
            elif condition:
                highlight_columns = st.columns(2)
                with highlight_columns[0]:
                    st.metric("Wind speed", f"{condition.wind_speed:g} m/s")
                    # Older readings may remain in session state after an app update.
                    feels_like = getattr(condition, "feels_like", None)
                    pressure = getattr(condition, "pressure", None)
                    feels_value = f"{feels_like:.1f}°C" if feels_like is not None else "—"
                    pressure_value = f"{pressure} hPa" if pressure is not None else "—"
                    st.metric(
                        "Feels like / pressure",
                        f"{feels_value} / {pressure_value}",
                    )
                with highlight_columns[1]:
                    st.metric("Humidity", f"{condition.humidity}%")
                    sunrise = getattr(condition, "sunrise", None) or "—"
                    sunset = getattr(condition, "sunset", None) or "—"
                    st.metric("Sunrise / sunset", f"{sunrise} / {sunset}")

    with card("5-day forecast"):
        if home_city is None:
            st.info("Add a city to see its five-day forecast.")
        else:
            readings, forecast_error, sample_data = load_weather(
                home_city, forecast=True
            )
            if forecast_error:
                st.info(f"Forecast unavailable: {forecast_error}")
            else:
                daily_forecast = group_forecast_by_day(readings)
                if not daily_forecast:
                    st.info("No forecast is available yet.")
                else:
                    forecast_columns = st.columns(len(daily_forecast))
                    for column, day in zip(forecast_columns, daily_forecast):
                        with column:
                            st.markdown(
                                f"**{day['date'].strftime('%a')}**  \n"
                                f"{day['date'].strftime('%b %d')}"
                            )
                            st.markdown(
                                f'<div class="skycast-weather-icon">'
                                f'{weather_icon(day["main_category"])}</div>',
                                unsafe_allow_html=True,
                            )
                            st.markdown(
                                f"**{day['high']:.0f}°** / {day['low']:.0f}°"
                            )
                    if sample_data:
                        st.caption("Showing sample forecast data")

    with card("Trips summary"):
        upcoming = min(upcoming_trips) if upcoming_trips else None
        total_stops = sum(len(destinations) for _, destinations, _ in trip_details)
        summary_columns = st.columns(3)
        summary_columns[0].metric("Trips", len(trips))
        summary_columns[1].metric(
            "Next upcoming trip",
            upcoming[1] if upcoming else "None",
            upcoming[0].strftime("%b %d") if upcoming else None,
        )
        summary_columns[2].metric("Stops", total_stops)
        if not trips:
            st.info("You have no trips yet. Start planning from the Trips page.")
        st.page_link("pages/2_Trips.py", label="Open Trips")

with st.expander("Manage trips"):
    if not trip_details:
        st.info("You have no trips yet. Create one on the Trips page.")
    for trip, destinations, travel_dates in trip_details:
        st.markdown(f"**{trip['trip_name']}**")
        if destinations:
            for destination in destinations:
                note = f" — {destination['notes']}" if destination["notes"] else ""
                st.write(
                    f"- {destination['city_name']}, {destination['country']} "
                    f"on {destination['travel_date']}{note}"
                )
        else:
            st.write("No destinations added yet.")
        new_name = st.text_input(
            "Rename trip",
            value=trip["trip_name"],
            key=f"rename_trip_{trip['id']}",
        )
        rename_column, delete_column = st.columns(2)
        with rename_column:
            if st.button("Save name", key=f"save_trip_{trip['id']}"):
                db.rename_trip(trip["id"], new_name)
                st.success("Renamed.")
                st.rerun()
        with delete_column:
            if st.button("Delete trip", key=f"delete_trip_{trip['id']}"):
                db.delete_trip(trip["id"])
                st.success("Deleted.")
                st.rerun()

with st.expander("Weather tools"):
    if st.button("Test my API key"):
        diagnostics = get_api_key_diagnostics()
        st.write(
            f"secrets.toml found: "
            f"{'Yes' if diagnostics['secrets_file_found'] else 'No'}"
        )
        st.write(f"Key detected: {'Yes' if diagnostics['key_detected'] else 'No'}")
        st.write(f"Key length: {diagnostics['key_length']}")

        if not diagnostics["key_detected"]:
            st.warning("No API key was detected; demo mode is active.")
        else:
            try:
                provider.get_current_weather(14.5995, 120.9842)
            except InvalidApiKeyError as exc:
                st.error(f"Invalid or not yet active: {exc}")
                st.write(f"HTTP status code: {exc.status_code}")
            except RateLimitError as exc:
                st.warning(str(exc))
                st.write(f"HTTP status code: {exc.status_code}")
            except (WeatherNetworkError, WeatherApiError) as exc:
                st.error(str(exc))
                st.write(f"HTTP status code: {getattr(exc, 'status_code', 'N/A')}")
            else:
                st.success("Key works")
                st.write(f"HTTP status code: {provider.last_status_code}")

    if cities:
        city_labels = [f"{city['name']}, {city['country']}" for city in cities]
        choice = st.selectbox("Quick weather check", city_labels)
        selected_city = cities[city_labels.index(choice)]
        if st.button("Check weather"):
            condition, weather_error, sample_data = load_weather(selected_city)
            if weather_error:
                st.error(f"Could not fetch weather: {weather_error}")
            elif condition:
                if sample_data:
                    st.caption("Showing sample data")
                alert = classify_weather(condition)
                st.metric("Temperature", f"{condition.temperature:.1f} °C")
                st.metric("Humidity", f"{condition.humidity}%")
                st.metric("Wind speed", f"{condition.wind_speed} m/s")
                st.write(f"**Condition:** {condition.description.title()}")
                st.info(f"**{alert.label} advisory:** {alert.advisory(condition)}")
                st.map(
                    {
                        "lat": [selected_city["latitude"]],
                        "lon": [selected_city["longitude"]],
                    }
                )
