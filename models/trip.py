class Destination:
    """One stop on a trip: a City plus a travel date.

    COMPOSITION: a Destination "has-a" City. The Destination does not
    inherit from City — it simply holds a reference to one.
    """

    def __init__(self, city, travel_date, notes="", destination_id=None):
        self.id = destination_id
        self.city = city
        self.travel_date = travel_date
        self.notes = notes


class Trip:
    """A trip is composed of a list of Destination objects.

    COMPOSITION: a Trip "has-many" Destinations. If the Trip is deleted,
    its Destinations no longer make sense on their own — that whole-part
    relationship is what composition means.
    """

    def __init__(self, trip_name, user_id, trip_id=None):
        self.id = trip_id
        self.trip_name = trip_name
        self.user_id = user_id
        self.destinations = []

    def add_destination(self, destination):
        self.destinations.append(destination)

    def total_stops(self):
        return len(self.destinations)
