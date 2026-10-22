from pathlib import Path

import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

from models.weather import MockWeatherProvider, OpenWeatherAPIProvider

SECRETS_PATH = Path(__file__).resolve().parent / ".streamlit" / "secrets.toml"


def _read_api_key():
    try:
        value = st.secrets.get("OPENWEATHER_API_KEY", "")
    except StreamlitSecretNotFoundError:
        value = ""

    api_key = str(value or "").strip()
    while len(api_key) >= 2 and api_key[0] == api_key[-1] and api_key[0] in "\"'":
        api_key = api_key[1:-1].strip()
    if api_key.lower() == "paste_your_api_key_here":
        api_key = ""
    return api_key


def get_provider():
    """Return (provider, is_demo). Uses the real OpenWeatherMap provider if
    an API key is set in .streamlit/secrets.toml, otherwise demo mode."""
    api_key = _read_api_key()
    if api_key:
        if len(api_key) != 32:
            st.warning(
                "The OpenWeatherMap API key is not 32 characters long. "
                "Check the value in `.streamlit/secrets.toml`."
            )
        return OpenWeatherAPIProvider(api_key), False
    return MockWeatherProvider(), True


def get_api_key_diagnostics():
    """Return safe key metadata without exposing the configured key."""
    api_key = _read_api_key()
    return {
        "secrets_file_found": SECRETS_PATH.is_file(),
        "key_detected": bool(api_key),
        "key_length": len(api_key),
    }
