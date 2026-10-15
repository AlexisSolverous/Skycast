from models.city import City
from models.trip import Destination, Trip


def test_trip_composition():
    trip = Trip("Beach Trip", user_id=1, trip_id=1)
    city = City(1, "Cebu City", "Philippines", 10.3157, 123.8854)
    destination = Destination(city, "2026-03-01")

    trip.add_destination(destination)

    assert trip.total_stops() == 1
    assert trip.destinations[0].city.name == "Cebu City"


def test_trip_with_multiple_destinations():
    trip = Trip("Grand Tour", user_id=1, trip_id=2)
    trip.add_destination(Destination(City(1, "Manila", "Philippines", 14.5995, 120.9842), "2026-04-01"))
    trip.add_destination(Destination(City(2, "Cebu City", "Philippines", 10.3157, 123.8854), "2026-04-05"))

    assert trip.total_stops() == 2


def test_city_coordinates_tuple():
    city = City(1, "Tokyo", "Japan", 35.6762, 139.6503)
    assert city.coordinates() == (35.6762, 139.6503)
