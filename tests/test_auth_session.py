import hashlib
from datetime import datetime, timezone
from types import SimpleNamespace

import auth_session
from auth_session import restore_user_from_token
from database.db_handler import DatabaseHandler


def test_remembered_token_restores_user_from_hashed_database_record(tmp_path):
    db = DatabaseHandler(tmp_path / "auth.db")
    db.create_user("avery", "hashed-password")
    user_row = db.get_user_by_username("avery")
    token = "random-browser-token"
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    db.create_auth_session(
        token_hash,
        user_row["id"],
        "2099-01-01T00:00:00+00:00",
    )

    user = restore_user_from_token(
        db,
        token,
        now=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )

    assert user.username == "avery"


def test_unknown_and_expired_remembered_tokens_do_not_restore_user(tmp_path):
    db = DatabaseHandler(tmp_path / "auth.db")
    db.create_user("avery", "hashed-password")
    user_row = db.get_user_by_username("avery")
    expired_token = "expired-browser-token"
    db.create_auth_session(
        hashlib.sha256(expired_token.encode("utf-8")).hexdigest(),
        user_row["id"],
        "2025-12-31T00:00:00+00:00",
    )

    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    assert restore_user_from_token(db, expired_token, now=now) is None
    assert restore_user_from_token(db, "unknown-token", now=now) is None
    assert restore_user_from_token(db, "x" * 129, now=now) is None


def test_initialize_auth_restores_token_from_request_cookie(tmp_path, monkeypatch):
    class SessionState(dict):
        __getattr__ = dict.__getitem__
        __setattr__ = dict.__setitem__

    db = DatabaseHandler(tmp_path / "auth.db")
    db.create_user("avery", "hashed-password")
    user_row = db.get_user_by_username("avery")
    token = "request-cookie-token"
    db.create_auth_session(
        hashlib.sha256(token.encode("utf-8")).hexdigest(),
        user_row["id"],
        "2099-01-01T00:00:00+00:00",
    )

    fake_streamlit = SimpleNamespace(
        session_state=SessionState(),
        context=SimpleNamespace(cookies={"skycast_login": token}),
    )
    monkeypatch.setattr(auth_session, "st", fake_streamlit)
    monkeypatch.setattr(
        auth_session,
        "_COOKIE_BRIDGE",
        lambda **_kwargs: SimpleNamespace(token=""),
    )

    user = auth_session.initialize_auth(db)

    assert user.username == "avery"
    assert fake_streamlit.session_state["remembered_login_token"] == token
