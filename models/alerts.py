from abc import ABC, abstractmethod


class Alert(ABC):
    """Abstract base class for a travel advisory.

    INHERITANCE: every specific alert below (RainAlert, StormAlert, ...)
    inherits from this class and must provide its own advisory().

    POLYMORPHISM: the rest of the app calls alert.advisory(condition) on
    whatever Alert object it was handed, without checking which subclass
    it is. Each subclass answers in its own way — that's polymorphism.
    """

    label = "General"

    @abstractmethod
    def advisory(self, condition):
        """Return a short, plain-language travel tip."""
        raise NotImplementedError


class ClearAlert(Alert):
    label = "Clear"

    def advisory(self, condition):
        return "Good weather for travel. No special preparation needed."


class RainAlert(Alert):
    label = "Rain"

    def advisory(self, condition):
        return "Rain is expected — bring an umbrella and allow extra travel time."


class StormAlert(Alert):
    label = "Storm"

    def advisory(self, condition):
        return "Thunderstorms are expected — consider rescheduling outdoor plans."


class HeatAlert(Alert):
    label = "Heat"

    def advisory(self, condition):
        return "High temperature expected — stay hydrated and wear light clothing."


class ColdAlert(Alert):
    label = "Cold"

    def advisory(self, condition):
        return "Cold weather expected — dress warmly and check for ice or frost."


def classify_weather(condition):
    """Factory function: looks at a WeatherCondition and returns the
    matching Alert object. This is the one place that decides WHICH
    subclass to use — everywhere else in the app just calls
    .advisory() polymorphically on whatever comes back.
    """
    category = condition.main_category.lower()

    if "storm" in category or "thunder" in category:
        return StormAlert()
    if "rain" in category or "drizzle" in category:
        return RainAlert()
    if condition.temperature >= 33:
        return HeatAlert()
    if condition.temperature <= 10:
        return ColdAlert()
    return ClearAlert()
