from abc import ABC, abstractmethod
from datetime import date, datetime, timedelta, timezone

import requests


class InvalidApiKeyError(Exception):
    """Raised when OpenWeatherMap rejects the configured API key."""

    def __init__(self, status_code=401):
        super().__init__(
            "OpenWeatherMap rejected the API key. If the key is new, it can "
            "take up to 2 hours to activate. Otherwise check it for typos in "
            ".streamlit/secrets.toml."
        )
        self.status_code = status_code


class RateLimitError(Exception):
    """Raised when OpenWeatherMap rate-limits a request."""

    def __init__(self, status_code=429):
        super().__init__("Too many requests, wait a minute")
        self.status_code = status_code


class WeatherApiError(Exception):
    """Raised for other HTTP failures without exposing the request URL."""

    def __init__(self, status_code):
        super().__init__(f"OpenWeatherMap request failed with HTTP {status_code}.")
        self.status_code = status_code


class WeatherNetworkError(Exception):
    """Raised when a weather request cannot reach its server."""


class WeatherCondition:
    """A simple data holder for one weather reading."""

    def __init__(
        self,
        temperature,
        description,
        humidity,
        wind_speed,
        main_category,
        sunrise=None,
        sunset=None,
        feels_like=None,
        pressure=None,
        forecast_date=None,
    ):
        self.temperature = temperature
        self.description = description
        self.humidity = humidity
        self.wind_speed = wind_speed
        self.main_category = main_category  # e.g. "Rain", "Clear", "Thunderstorm"
        self.sunrise = sunrise
        self.sunset = sunset
        self.feels_like = feels_like
        self.pressure = pressure
        self.forecast_date = forecast_date


class WeatherProvider(ABC):
    """ABSTRACTION: this class defines WHAT any weather data source must
    be able to do, without saying HOW. SkyCast's pages only ever talk
    to a WeatherProvider — they never need to know which company's API
    is behind it. If a different provider is needed later (a different
    API, or a fake provider used only for testing), it can be swapped
    in here without changing a single line of the Streamlit pages.
    """

    @abstractmethod
    def get_coordinates(self, city_name, country_code=""):
        """GPS lookup: turn a city name into (latitude, longitude)."""
        raise NotImplementedError

    @abstractmethod
    def get_current_weather(self, latitude, longitude):
        """Return a WeatherCondition for the given GPS coordinates."""
        raise NotImplementedError

    @abstractmethod
    def get_forecast(self, latitude, longitude):
        """Return a list of upcoming WeatherCondition readings."""
        raise NotImplementedError


class OpenWeatherAPIProvider(WeatherProvider):
    """Concrete implementation that talks to the free OpenWeatherMap API.

    Two endpoints are used:
      - the GPS / Geocoding API  -> turns a city name into coordinates
      - the Weather API (by lat/lon) -> turns coordinates into a forecast
    """

    GEO_URL = "https://api.openweathermap.org/geo/1.0/direct"
    WEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"
    FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"

    def __init__(self, api_key):
        self.api_key = api_key
        self.last_status_code = None

    def _get_json(self, url, params):
        try:
            response = requests.get(url, params=params, timeout=10)
        except (requests.ConnectionError, requests.Timeout) as exc:
            raise WeatherNetworkError("No internet connection") from exc
        except requests.RequestException as exc:
            raise WeatherNetworkError("Weather service request failed") from exc

        self.last_status_code = response.status_code
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            status_code = response.status_code
            if status_code == 401:
                raise InvalidApiKeyError(status_code) from exc
            if status_code == 429:
                raise RateLimitError(status_code) from exc
            raise WeatherApiError(status_code) from exc
        return response.json()

    def get_coordinates(self, city_name, country_code=""):
        query = city_name if not country_code else f"{city_name},{country_code}"
        results = self._get_json(
            self.GEO_URL,
            params={"q": query, "limit": 1, "appid": self.api_key},
        )
        if not results:
            return None
        return results[0]["lat"], results[0]["lon"]

    def get_current_weather(self, latitude, longitude):
        data = self._get_json(
            self.WEATHER_URL,
            params={
                "lat": latitude,
                "lon": longitude,
                "appid": self.api_key,
                "units": "metric",
            },
        )
        timezone_offset = data.get("timezone", 0)
        system = data.get("sys", {})

        def local_time(timestamp):
            if timestamp is None:
                return None
            local_timestamp = timestamp + timezone_offset
            return datetime.fromtimestamp(
                local_timestamp, tz=timezone.utc
            ).strftime("%H:%M")

        return WeatherCondition(
            temperature=data["main"]["temp"],
            description=data["weather"][0]["description"],
            humidity=data["main"]["humidity"],
            wind_speed=data["wind"]["speed"],
            main_category=data["weather"][0]["main"],
            sunrise=local_time(system.get("sunrise")),
            sunset=local_time(system.get("sunset")),
            feels_like=data["main"].get("feels_like"),
            pressure=data["main"].get("pressure"),
        )

    def get_forecast(self, latitude, longitude):
        data = self._get_json(
            self.FORECAST_URL,
            params={
                "lat": latitude,
                "lon": longitude,
                "appid": self.api_key,
                "units": "metric",
            },
        )
        readings = []
        timezone_offset = data.get("city", {}).get("timezone", 0)
        for entry in data["list"]:
            entry_date = entry.get("dt_txt")
            if entry_date:
                forecast_date = datetime.fromisoformat(entry_date).date().isoformat()
            else:
                forecast_date = datetime.fromtimestamp(
                    entry["dt"] + timezone_offset, tz=timezone.utc
                ).date().isoformat()
            readings.append(
                WeatherCondition(
                    temperature=entry["main"]["temp"],
                    description=entry["weather"][0]["description"],
                    humidity=entry["main"]["humidity"],
                    wind_speed=entry["wind"]["speed"],
                    main_category=entry["weather"][0]["main"],
                    feels_like=entry["main"].get("feels_like"),
                    pressure=entry["main"].get("pressure"),
                    forecast_date=forecast_date,
                )
            )
        return readings


class MockWeatherProvider(WeatherProvider):
    """DEMO MODE: a second concrete WeatherProvider that returns believable
    fake data, so the whole front end works with no API key and no internet.
    (Inheritance + polymorphism: the pages treat it exactly like the real one.)
    """

    _SAMPLES = [
        (30.5, "scattered clouds", 70, 3.2, "Clouds", "06:12", "18:24", 32.0, 1008),
        (27.0, "light rain", 85, 4.5, "Rain", "05:48", "18:02", 29.0, 1009),
        (35.0, "clear sky", 55, 2.0, "Clear", "06:25", "18:40", 37.0, 1006),
        (24.0, "thunderstorm", 90, 8.0, "Thunderstorm", "06:03", "18:12", 26.0, 1007),
        (8.0, "clear sky", 45, 1.5, "Clear", "07:10", "17:38", 7.0, 1018),
    ]

    def _pick(self, latitude, longitude):
        index = int(abs(latitude) + abs(longitude)) % len(self._SAMPLES)
        return WeatherCondition(*self._SAMPLES[index])

    def get_coordinates(self, city_name, country_code=""):
        return None

    def get_current_weather(self, latitude, longitude):
        return self._pick(latitude, longitude)

    def get_forecast(self, latitude, longitude):
        today = date.today()
        base = self._pick(latitude, longitude)
        readings = []
        # Three readings per day give the dashboard realistic daily highs and lows.
        for day_offset in range(5):
            forecast_date = (today + timedelta(days=day_offset)).isoformat()
            daily_shift = ((day_offset % 3) - 1) * 1.5
            for temperature_shift in (-3.0, 2.0, 0.0):
                readings.append(
                    WeatherCondition(
                        temperature=base.temperature + daily_shift + temperature_shift,
                        description=base.description,
                        humidity=base.humidity,
                        wind_speed=base.wind_speed,
                        main_category=base.main_category,
                        feels_like=base.feels_like,
                        pressure=base.pressure,
                        forecast_date=forecast_date,
                    )
                )
        return readings
