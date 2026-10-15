from unittest.mock import Mock, patch

import pytest
import requests

from models.weather import (
    InvalidApiKeyError,
    OpenWeatherAPIProvider,
    RateLimitError,
    WeatherApiError,
    WeatherNetworkError,
)


def make_response(status_code, payload=None):
    response = Mock()
    response.status_code = status_code
    response.json.return_value = payload or {
        "main": {"temp": 23, "humidity": 60},
        "weather": [{"description": "clear sky", "main": "Clear"}],
        "wind": {"speed": 2.5},
    }
    if status_code >= 400:
        response.raise_for_status.side_effect = requests.HTTPError(
            response=response
        )
    return response


@pytest.mark.parametrize(
    ("status_code", "error_type", "message"),
    [
        (
            401,
            InvalidApiKeyError,
            "OpenWeatherMap rejected the API key. If the key is new, it can "
            "take up to 2 hours to activate. Otherwise check it for typos in "
            ".streamlit/secrets.toml.",
        ),
        (429, RateLimitError, "Too many requests, wait a minute"),
    ],
)
def test_openweather_maps_http_errors(status_code, error_type, message):
    provider = OpenWeatherAPIProvider("a" * 32)
    with patch("models.weather.requests.get", return_value=make_response(status_code)):
        with pytest.raises(error_type, match=message) as error:
            provider.get_current_weather(14.5995, 120.9842)

    assert error.value.status_code == status_code
    assert provider.last_status_code == status_code


def test_openweather_returns_condition_for_successful_response():
    provider = OpenWeatherAPIProvider("a" * 32)
    with patch("models.weather.requests.get", return_value=make_response(200)):
        condition = provider.get_current_weather(14.5995, 120.9842)

    assert condition.temperature == 23
    assert condition.description == "clear sky"
    assert condition.main_category == "Clear"
    assert provider.last_status_code == 200


def test_other_http_errors_do_not_expose_the_request_url_or_key():
    api_key = "a" * 32
    provider = OpenWeatherAPIProvider(api_key)
    response = make_response(500)
    response.raise_for_status.side_effect = requests.HTTPError(
        f"500 Server Error for url: ?appid={api_key}", response=response
    )

    with patch("models.weather.requests.get", return_value=response):
        with pytest.raises(WeatherApiError, match="OpenWeatherMap request failed with HTTP 500") as error:
            provider.get_current_weather(14.5995, 120.9842)

    assert api_key not in str(error.value)


@pytest.mark.parametrize("network_error", [requests.ConnectionError, requests.Timeout])
def test_network_errors_have_clear_message(network_error):
    provider = OpenWeatherAPIProvider("a" * 32)
    with patch("models.weather.requests.get", side_effect=network_error):
        with pytest.raises(WeatherNetworkError, match="No internet connection"):
            provider.get_current_weather(14.5995, 120.9842)
