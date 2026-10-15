from models.alerts import (
    ClearAlert,
    ColdAlert,
    HeatAlert,
    RainAlert,
    StormAlert,
    classify_weather,
)
from models.weather import WeatherCondition


def test_rain_classification():
    condition = WeatherCondition(22, "light rain", 80, 3.0, "Rain")
    assert isinstance(classify_weather(condition), RainAlert)


def test_storm_classification():
    condition = WeatherCondition(24, "thunderstorm", 90, 8.0, "Thunderstorm")
    assert isinstance(classify_weather(condition), StormAlert)


def test_heat_classification():
    condition = WeatherCondition(35, "clear sky", 40, 1.0, "Clear")
    assert isinstance(classify_weather(condition), HeatAlert)


def test_cold_classification():
    condition = WeatherCondition(5, "clear sky", 50, 2.0, "Clear")
    assert isinstance(classify_weather(condition), ColdAlert)


def test_clear_classification():
    condition = WeatherCondition(24, "clear sky", 55, 2.0, "Clear")
    assert isinstance(classify_weather(condition), ClearAlert)


def test_advisory_returns_nonempty_text():
    condition = WeatherCondition(22, "light rain", 80, 3.0, "Rain")
    alert = classify_weather(condition)
    advisory = alert.advisory(condition)
    assert isinstance(advisory, str)
    assert len(advisory) > 0
