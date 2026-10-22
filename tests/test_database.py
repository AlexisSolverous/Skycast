import os

from database.db_handler import DatabaseHandler
from database.seed_cities import seed_if_empty

TEST_DB = "test_skycast.db"


def setup_function():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


def teardown_function():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


def test_city_seed_loads_100_records():
    db = DatabaseHandler(TEST_DB)
    seed_if_empty(db)
    assert db.count_cities() == 100


def test_seed_is_not_duplicated_on_second_run():
    db = DatabaseHandler(TEST_DB)
    seed_if_empty(db)
    seed_if_empty(db)  # calling it again should not add more rows
    assert db.count_cities() == 100


def test_create_and_fetch_user():
    db = DatabaseHandler(TEST_DB)
    db.create_user("testuser", "hashedpw")
    row = db.get_user_by_username("testuser")
    assert row is not None
    assert row["username"] == "testuser"


def test_auth_session_restores_user_until_expiration():
    db = DatabaseHandler(TEST_DB)
    db.create_user("remembered", "hashedpw")
    user = db.get_user_by_username("remembered")
    token_hash = "hashed-session-token"

    db.create_auth_session(token_hash, user["id"], "2026-01-02T00:00:00+00:00")

    active = db.get_user_for_auth_session(
        token_hash, "2026-01-01T00:00:00+00:00"
    )
    expired = db.get_user_for_auth_session(
        token_hash, "2026-01-03T00:00:00+00:00"
    )

    assert active["username"] == "remembered"
    assert expired is None


def test_auth_session_can_be_revoked():
    db = DatabaseHandler(TEST_DB)
    db.create_user("logout-user", "hashedpw")
    user = db.get_user_by_username("logout-user")
    token_hash = "revoked-session-token"
    db.create_auth_session(token_hash, user["id"], "2099-01-01T00:00:00+00:00")

    db.delete_auth_session(token_hash)

    assert db.get_user_for_auth_session(
        token_hash, "2026-01-01T00:00:00+00:00"
    ) is None


def test_create_trip_and_add_destination():
    db = DatabaseHandler(TEST_DB)
    seed_if_empty(db)
    db.create_user("traveler", "hashedpw")
    user_row = db.get_user_by_username("traveler")

    trip_id = db.create_trip(user_row["id"], "Test Trip", "2026-01-01")
    first_city = db.get_all_cities()[0]
    db.add_destination(trip_id, first_city["id"], "2026-01-05", "test note")

    destinations = db.get_destinations_for_trip(trip_id)
    assert len(destinations) == 1
    assert destinations[0]["notes"] == "test note"


def test_delete_trip_removes_its_destinations():
    db = DatabaseHandler(TEST_DB)
    seed_if_empty(db)
    db.create_user("traveler2", "hashedpw")
    user_row = db.get_user_by_username("traveler2")

    trip_id = db.create_trip(user_row["id"], "Temp Trip", "2026-01-01")
    first_city = db.get_all_cities()[0]
    db.add_destination(trip_id, first_city["id"], "2026-01-05")

    db.delete_trip(trip_id)

    assert db.get_destinations_for_trip(trip_id) == []
