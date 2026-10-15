from models.alerts import classify_weather
from models.weather import MockWeatherProvider, WeatherProvider


def test_mock_is_a_weather_provider():
    assert isinstance(MockWeatherProvider(), WeatherProvider)


def test_mock_returns_condition_and_alert():
    condition = MockWeatherProvider().get_current_weather(14.6, 121.0)
    assert classify_weather(condition).advisory(condition)
