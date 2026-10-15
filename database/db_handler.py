import sqlite3
from pathlib import Path

from database.data_store import DataStore

DEFAULT_DB_PATH = Path(__file__).parent / "skycast.db"


class DatabaseHandler(DataStore):
    """Wraps every raw SQL statement SkyCast needs.

    ENCAPSULATION: no other file in the project writes SQL directly —
    pages and models just call methods like create_trip() or
    get_all_cities(). If the database ever changed from SQLite to
    something else, only this one file would need to change.
    """

    def __init__(self, db_path=DEFAULT_DB_PATH):
        self.db_path = db_path
        self._init_schema()

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_schema(self):
        conn = self._connect()
        try:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS cities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    country TEXT NOT NULL,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL
                );

                CREATE TABLE IF NOT EXISTS trips (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    trip_name TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                );

                CREATE TABLE IF NOT EXISTS destinations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trip_id INTEGER NOT NULL,
                    city_id INTEGER NOT NULL,
                    travel_date TEXT NOT NULL,
                    notes TEXT,
                    FOREIGN KEY (trip_id) REFERENCES trips (id),
                    FOREIGN KEY (city_id) REFERENCES cities (id)
                );
                """
            )
            conn.commit()
        finally:
            conn.close()

    # ---------------- users ----------------

    def create_user(self, username, password_hash):
        conn = self._connect()
        try:
            conn.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (username, password_hash),
            )
            conn.commit()
        finally:
            conn.close()

    def get_user_by_username(self, username):
        conn = self._connect()
        try:
            return conn.execute(
                "SELECT * FROM users WHERE username = ?", (username,)
            ).fetchone()
        finally:
            conn.close()

    # ---------------- cities ----------------

    def count_cities(self):
        conn = self._connect()
        try:
            return conn.execute("SELECT COUNT(*) FROM cities").fetchone()[0]
        finally:
            conn.close()

    def seed_cities(self, city_list):
        conn = self._connect()
        try:
            conn.executemany(
                "INSERT INTO cities (name, country, latitude, longitude) "
                "VALUES (?, ?, ?, ?)",
                city_list,
            )
            conn.commit()
        finally:
            conn.close()

    def get_all_cities(self):
        conn = self._connect()
        try:
            return conn.execute("SELECT * FROM cities ORDER BY name").fetchall()
        finally:
            conn.close()

    def search_cities(self, keyword):
        conn = self._connect()
        try:
            return conn.execute(
                "SELECT * FROM cities WHERE name LIKE ? ORDER BY name",
                (f"%{keyword}%",),
            ).fetchall()
        finally:
            conn.close()

    def add_city(self, name, country, latitude, longitude):
        """Add a city that was looked up live through the GPS/geocoding
        API, so it becomes available in the dropdown from now on."""
        conn = self._connect()
        try:
            cur = conn.execute(
                "INSERT INTO cities (name, country, latitude, longitude) "
                "VALUES (?, ?, ?, ?)",
                (name, country, latitude, longitude),
            )
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()

    # ---------------- trips ----------------

    def create_trip(self, user_id, trip_name, created_at):
        conn = self._connect()
        try:
            cur = conn.execute(
                "INSERT INTO trips (user_id, trip_name, created_at) "
                "VALUES (?, ?, ?)",
                (user_id, trip_name, created_at),
            )
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()

    def get_trips_for_user(self, user_id):
        conn = self._connect()
        try:
            return conn.execute(
                "SELECT * FROM trips WHERE user_id = ? ORDER BY created_at DESC",
                (user_id,),
            ).fetchall()
        finally:
            conn.close()

    def rename_trip(self, trip_id, new_name):
        conn = self._connect()
        try:
            conn.execute(
                "UPDATE trips SET trip_name = ? WHERE id = ?", (new_name, trip_id)
            )
            conn.commit()
        finally:
            conn.close()

    def delete_trip(self, trip_id):
        conn = self._connect()
        try:
            conn.execute("DELETE FROM destinations WHERE trip_id = ?", (trip_id,))
            conn.execute("DELETE FROM trips WHERE id = ?", (trip_id,))
            conn.commit()
        finally:
            conn.close()

    # ---------------- destinations ----------------

    def add_destination(self, trip_id, city_id, travel_date, notes=""):
        conn = self._connect()
        try:
            conn.execute(
                "INSERT INTO destinations (trip_id, city_id, travel_date, notes) "
                "VALUES (?, ?, ?, ?)",
                (trip_id, city_id, travel_date, notes),
            )
            conn.commit()
        finally:
            conn.close()

    def get_destinations_for_trip(self, trip_id):
        conn = self._connect()
        try:
            return conn.execute(
                """
                SELECT destinations.*, cities.name AS city_name,
                       cities.country AS country,
                       cities.latitude AS latitude,
                       cities.longitude AS longitude
                FROM destinations
                JOIN cities ON destinations.city_id = cities.id
                WHERE trip_id = ?
                ORDER BY travel_date
                """,
                (trip_id,),
            ).fetchall()
        finally:
            conn.close()

    def delete_destination(self, destination_id):
        conn = self._connect()
        try:
            conn.execute("DELETE FROM destinations WHERE id = ?", (destination_id,))
            conn.commit()
        finally:
            conn.close()
