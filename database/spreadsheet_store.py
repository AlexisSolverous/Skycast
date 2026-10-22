import csv
import sqlite3
import tempfile
from pathlib import Path

from database.data_store import DataStore
from database.seed_cities import CITIES


class SpreadsheetStore(DataStore):
    """CSV-backed implementation of SkyCast's storage interface."""

    _HEADERS = {
        "users": ("id", "username", "password_hash"),
        "auth_sessions": ("token_hash", "user_id", "expires_at"),
        "cities": ("id", "name", "country", "latitude", "longitude"),
        "trips": ("id", "user_id", "trip_name", "created_at"),
        "destinations": ("id", "trip_id", "city_id", "travel_date", "notes"),
    }
    _INTEGER_FIELDS = {
        "users": {"id"},
        "auth_sessions": {"user_id"},
        "cities": {"id"},
        "trips": {"id", "user_id"},
        "destinations": {"id", "trip_id", "city_id"},
    }
    _FLOAT_FIELDS = {"latitude", "longitude"}

    def __init__(self, data_dir=None):
        self.data_dir = (
            Path(data_dir)
            if data_dir is not None
            else Path(__file__).resolve().parent.parent / "data"
        )
        self.data_dir.mkdir(parents=True, exist_ok=True)

        for table, headers in self._HEADERS.items():
            path = self._path(table)
            if not path.exists() or path.stat().st_size == 0:
                self._write_rows(table, [])

        if self.count_cities() == 0:
            self.seed_cities(CITIES)

    def _path(self, table):
        return self.data_dir / f"{table}.csv"

    def _read_rows(self, table):
        with self._path(table).open("r", newline="", encoding="utf-8-sig") as csv_file:
            rows = []
            for raw_row in csv.DictReader(csv_file):
                row = dict(raw_row)
                for field in self._INTEGER_FIELDS[table]:
                    row[field] = int(row[field])
                for field in self._FLOAT_FIELDS.intersection(row):
                    row[field] = float(row[field])
                rows.append(row)
            return rows

    def _write_rows(self, table, rows):
        path = self._path(table)
        temporary_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                newline="",
                encoding="utf-8-sig",
                dir=self.data_dir,
                prefix=f".{table}_",
                suffix=".tmp",
                delete=False,
            ) as csv_file:
                temporary_path = Path(csv_file.name)
                writer = csv.DictWriter(csv_file, fieldnames=self._HEADERS[table])
                writer.writeheader()
                writer.writerows(rows)
            temporary_path.replace(path)
        except PermissionError as exc:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
            raise PermissionError(
                f"Close {path.name} in Excel and try again."
            ) from exc
        except Exception:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
            raise

    def _next_id(self, table):
        return max((row["id"] for row in self._read_rows(table)), default=0) + 1

    # ---------------- users ----------------

    def create_user(self, username, password_hash):
        users = self._read_rows("users")
        if any(user["username"] == username for user in users):
            raise sqlite3.IntegrityError(
                "UNIQUE constraint failed: users.username"
            )
        users.append(
            {
                "id": self._next_id("users"),
                "username": username,
                "password_hash": password_hash,
            }
        )
        self._write_rows("users", users)

    def get_user_by_username(self, username):
        return next(
            (
                row
                for row in self._read_rows("users")
                if row["username"] == username
            ),
            None,
        )

    def create_auth_session(self, token_hash, user_id, expires_at):
        sessions = self._read_rows("auth_sessions")
        sessions.append(
            {
                "token_hash": token_hash,
                "user_id": user_id,
                "expires_at": expires_at,
            }
        )
        self._write_rows("auth_sessions", sessions)

    def get_user_for_auth_session(self, token_hash, now):
        session = next(
            (
                item
                for item in self._read_rows("auth_sessions")
                if item["token_hash"] == token_hash and item["expires_at"] > now
            ),
            None,
        )
        if session is None:
            return None
        return next(
            (
                user
                for user in self._read_rows("users")
                if user["id"] == session["user_id"]
            ),
            None,
        )

    def delete_auth_session(self, token_hash):
        sessions = self._read_rows("auth_sessions")
        self._write_rows(
            "auth_sessions",
            [session for session in sessions if session["token_hash"] != token_hash],
        )

    # ---------------- cities ----------------

    def count_cities(self):
        return len(self._read_rows("cities"))

    def seed_cities(self, city_list):
        cities = self._read_rows("cities")
        next_id = self._next_id("cities")
        for name, country, latitude, longitude in city_list:
            cities.append(
                {
                    "id": next_id,
                    "name": name,
                    "country": country,
                    "latitude": float(latitude),
                    "longitude": float(longitude),
                }
            )
            next_id += 1
        self._write_rows("cities", cities)

    def get_all_cities(self):
        return sorted(self._read_rows("cities"), key=lambda city: city["name"])

    def search_cities(self, keyword):
        query = keyword.casefold()
        return sorted(
            (
                city
                for city in self._read_rows("cities")
                if query in city["name"].casefold()
            ),
            key=lambda city: city["name"],
        )

    def add_city(self, name, country, latitude, longitude):
        cities = self._read_rows("cities")
        city_id = self._next_id("cities")
        cities.append(
            {
                "id": city_id,
                "name": name,
                "country": country,
                "latitude": float(latitude),
                "longitude": float(longitude),
            }
        )
        self._write_rows("cities", cities)
        return city_id

    # ---------------- trips ----------------

    def create_trip(self, user_id, trip_name, created_at):
        trips = self._read_rows("trips")
        trip_id = self._next_id("trips")
        trips.append(
            {
                "id": trip_id,
                "user_id": int(user_id),
                "trip_name": trip_name,
                "created_at": created_at,
            }
        )
        self._write_rows("trips", trips)
        return trip_id

    def get_trips_for_user(self, user_id):
        return sorted(
            (
                trip
                for trip in self._read_rows("trips")
                if trip["user_id"] == int(user_id)
            ),
            key=lambda trip: trip["created_at"],
            reverse=True,
        )

    def rename_trip(self, trip_id, new_name):
        trips = self._read_rows("trips")
        for trip in trips:
            if trip["id"] == int(trip_id):
                trip["trip_name"] = new_name
                break
        self._write_rows("trips", trips)

    def delete_trip(self, trip_id):
        trip_id = int(trip_id)
        trips = [
            trip for trip in self._read_rows("trips") if trip["id"] != trip_id
        ]
        destinations = [
            destination
            for destination in self._read_rows("destinations")
            if destination["trip_id"] != trip_id
        ]
        self._write_rows("destinations", destinations)
        self._write_rows("trips", trips)

    # ---------------- destinations ----------------

    def add_destination(self, trip_id, city_id, travel_date, notes=""):
        destinations = self._read_rows("destinations")
        destinations.append(
            {
                "id": self._next_id("destinations"),
                "trip_id": int(trip_id),
                "city_id": int(city_id),
                "travel_date": travel_date,
                "notes": notes,
            }
        )
        self._write_rows("destinations", destinations)

    def get_destinations_for_trip(self, trip_id):
        cities = {city["id"]: city for city in self._read_rows("cities")}
        rows = []
        for destination in self._read_rows("destinations"):
            if destination["trip_id"] != int(trip_id):
                continue
            city = cities.get(destination["city_id"])
            if city is None:
                continue
            rows.append(
                {
                    **destination,
                    "city_name": city["name"],
                    "country": city["country"],
                    "latitude": city["latitude"],
                    "longitude": city["longitude"],
                }
            )
        return sorted(rows, key=lambda row: row["travel_date"])

    def delete_destination(self, destination_id):
        destination_id = int(destination_id)
        destinations = [
            destination
            for destination in self._read_rows("destinations")
            if destination["id"] != destination_id
        ]
        self._write_rows("destinations", destinations)
