import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import streamlit as st

from models.user import User

REMEMBER_LOGIN_DAYS = 30
_COOKIE_NAME = "skycast_login"
_COOKIE_COMPONENT_KEY = "skycast_login_cookie"

_COOKIE_BRIDGE = st.components.v2.component(
    "skycast_login_cookie_bridge",
    html="<span></span>",
    js="""\
export default function (component) {
  const { data, setStateValue } = component
  const cookieName = data.cookieName
  const secure = window.location.protocol === "https:" ? "; Secure" : ""
  let token = ""

  if (data.action === "set") {
    token = data.token
    const expires = new Date(data.expiresAt).toUTCString()
    document.cookie =
      `${cookieName}=${encodeURIComponent(token)}; Expires=${expires}; ` +
      `Path=/; SameSite=Strict${secure}`
  } else if (data.action === "clear") {
    document.cookie =
      `${cookieName}=; Max-Age=0; Path=/; SameSite=Strict${secure}`
  } else {
    const prefix = `${cookieName}=`
    const cookie = document.cookie
      .split(";")
      .map(value => value.trim())
      .find(value => value.startsWith(prefix))
    if (cookie) {
      try {
        token = decodeURIComponent(cookie.slice(prefix.length))
      } catch {
        token = ""
      }
    }
  }

  setStateValue("token", token)
}
""",
)


def _hash_token(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_remembered_login(db, user):
    """Create a random browser token while storing only its hash in SQLite."""
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(days=REMEMBER_LOGIN_DAYS)
    db.create_auth_session(
        _hash_token(token),
        user.id,
        expires_at.isoformat(),
    )
    st.session_state["_login_cookie_action"] = {
        "action": "set",
        "token": token,
        "expires_at": expires_at.isoformat(),
    }
    st.session_state["_active_login_token"] = token


def restore_user_from_token(db, token, now=None):
    """Return the token's user when the token is still valid."""
    if not isinstance(token, str) or not token or len(token) > 128:
        return None

    current_time = now or datetime.now(timezone.utc)
    row = db.get_user_for_auth_session(
        _hash_token(token),
        current_time.astimezone(timezone.utc).isoformat(),
    )
    if row is None:
        return None
    return User(row["id"], row["username"], row["password_hash"])


def initialize_auth(db):
    """Restore a login from the browser cookie after a Streamlit reconnect."""
    st.session_state.setdefault("user", None)
    action = st.session_state.pop("_login_cookie_action", None) or {}
    result = _COOKIE_BRIDGE(
        key=_COOKIE_COMPONENT_KEY,
        data={
            "cookieName": _COOKIE_NAME,
            "action": action.get("action", "read"),
            "token": action.get("token", ""),
            "expiresAt": action.get("expires_at", ""),
        },
        default={"token": ""},
        on_token_change=lambda: None,
    )
    token = result.token or ""
    st.session_state["remembered_login_token"] = token

    if (
        action.get("action") != "clear"
        and st.session_state.user is None
        and token
    ):
        st.session_state.user = restore_user_from_token(db, token)
        if st.session_state.user is not None:
            st.session_state["_active_login_token"] = token
    return st.session_state.user


def logout(db):
    """Revoke the remembered session and clear its browser cookie."""
    token = st.session_state.pop("_active_login_token", None)
    if token:
        db.delete_auth_session(_hash_token(token))
    st.session_state["remembered_login_token"] = ""
    st.session_state["user"] = None
    st.session_state["_login_cookie_action"] = {"action": "clear"}
