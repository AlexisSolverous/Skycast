from abc import ABC, abstractmethod
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

    def __init__(self, temperature, description, humidity, wind_speed, main_category):
        self.temperature = temperature
        self.description = description
        self.humidity = humidity
        self.wind_speed = wind_speed
        self.main_category = main_category  # e.g. "Rain", "Clear", "Thunderstorm"


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
        return WeatherCondition(
            temperature=data["main"]["temp"],
            description=data["weather"][0]["description"],
            humidity=data["main"]["humidity"],
            wind_speed=data["wind"]["speed"],
            main_category=data["weather"][0]["main"],
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
        for entry in data["list"][:8]:  # next ~24 hours, in 3-hour steps
            readings.append(
                WeatherCondition(
                    temperature=entry["main"]["temp"],
                    description=entry["weather"][0]["description"],
                    humidity=entry["main"]["humidity"],
                    wind_speed=entry["wind"]["speed"],
                    main_category=entry["weather"][0]["main"],
                )
            )
        return readings


class MockWeatherProvider(WeatherProvider):
    """DEMO MODE: a second concrete WeatherProvider that returns believable
    fake data, so the whole front end works with no API key and no internet.
    (Inheritance + polymorphism: the pages treat it exactly like the real one.)
    """

    _SAMPLES = [
        (30.5, "scattered clouds", 70, 3.2, "Clouds"),
        (27.0, "light rain", 85, 4.5, "Rain"),
        (35.0, "clear sky", 55, 2.0, "Clear"),
        (24.0, "thunderstorm", 90, 8.0, "Thunderstorm"),
        (8.0, "clear sky", 45, 1.5, "Clear"),
    ]

    def _pick(self, latitude, longitude):
        index = int(abs(latitude) + abs(longitude)) % len(self._SAMPLES)
        return WeatherCondition(*self._SAMPLES[index])

    def get_coordinates(self, city_name, country_code=""):
        return None

    def get_current_weather(self, latitude, longitude):
        return self._pick(latitude, longitude)

    def get_forecast(self, latitude, longitude):
        return [self._pick(latitude, longitude)]
