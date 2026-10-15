class City:
    """A simple data holder for one city and its GPS location.

    Storing latitude/longitude ahead of time means the app can ask the
    weather API for a forecast "by GPS coordinates" instead of just a
    city name — this is more accurate (no mixing up two cities that
    share a name) and is exactly how professional weather apps do it.
    """

    def __init__(self, city_id, name, country, latitude, longitude):
        self.id = city_id
        self.name = name
        self.country = country
        self.latitude = latitude
        self.longitude = longitude

    def __str__(self):
        return f"{self.name}, {self.country}"

    def coordinates(self):
        """Return the GPS coordinates as a (lat, lon) tuple."""
        return (self.latitude, self.longitude)
