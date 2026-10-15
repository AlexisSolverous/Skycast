from abc import ABC, abstractmethod


class DataStore(ABC):
    """Abstract interface for SkyCast's user and travel-plan storage."""

    @abstractmethod
    def create_user(self, username, password_hash):
        raise NotImplementedError

    @abstractmethod
    def get_user_by_username(self, username):
        raise NotImplementedError

    @abstractmethod
    def count_cities(self):
        raise NotImplementedError

    @abstractmethod
    def seed_cities(self, city_list):
        raise NotImplementedError

    @abstractmethod
    def get_all_cities(self):
        raise NotImplementedError

    @abstractmethod
    def search_cities(self, keyword):
        raise NotImplementedError

    @abstractmethod
    def add_city(self, name, country, latitude, longitude):
        raise NotImplementedError

    @abstractmethod
    def create_trip(self, user_id, trip_name, created_at):
        raise NotImplementedError

    @abstractmethod
    def get_trips_for_user(self, user_id):
        raise NotImplementedError

    @abstractmethod
    def rename_trip(self, trip_id, new_name):
        raise NotImplementedError

    @abstractmethod
    def delete_trip(self, trip_id):
        raise NotImplementedError

    @abstractmethod
    def add_destination(self, trip_id, city_id, travel_date, notes=""):
        raise NotImplementedError

    @abstractmethod
    def get_destinations_for_trip(self, trip_id):
        raise NotImplementedError

    @abstractmethod
    def delete_destination(self, destination_id):
        raise NotImplementedError
