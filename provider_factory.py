import json
import os

import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

from models.weather import MockWeatherProvider, OpenWeatherAPIProvider
from paths import resource_path, user_data_dir

SECRETS_PATH = resource_path(".streamlit/secrets.toml")
API_KEY_ENV_VAR = "OPENWEATHER_API_KEY"


def _clean_api_key(value):
    api_key = str(value or "").strip()
    while len(api_key) >= 2 and api_key[0] == api_key[-1] and api_key[0] in "\"'":
        api_key = api_key[1:-1].strip()
    if api_key.lower() == "paste_your_api_key_here":
        return ""
    return api_key


def _read_config_api_key():
    config_path = user_data_dir() / "config.json"
    if not config_path.is_file():
        return ""

    try:
        with config_path.open("r", encoding="utf-8") as config_file:
            config = json.load(config_file)
    except json.JSONDecodeError:
        st.warning(
            "Could not read the API key from AppData\\SkyCast\\config.json. "
            "Correct or remove that file to use the saved key."
        )
        return ""

    if not isinstance(config, dict):
        st.warning(
            "AppData\\SkyCast\\config.json must contain a JSON object with "
            "an OPENWEATHER_API_KEY value."
        )
        return ""
    return _clean_api_key(config.get(API_KEY_ENV_VAR, ""))


def _read_api_key():
    """Read the key from environment, user config, then Streamlit secrets."""
    api_key = _clean_api_key(os.environ.get(API_KEY_ENV_VAR, ""))
    if api_key:
        return api_key

    api_key = _read_config_api_key()
    if api_key:
        return api_key

    try:
        value = st.secrets.get("OPENWEATHER_API_KEY", "")
    except StreamlitSecretNotFoundError:
        value = ""

    return _clean_api_key(value)


def save_api_key(api_key):
    """Save an API key outside the install folder, for this Windows user."""
    cleaned_key = _clean_api_key(api_key)
    if not cleaned_key:
        raise ValueError("Enter a non-empty OpenWeatherMap API key.")

    config_path = user_data_dir() / "config.json"
    with config_path.open("w", encoding="utf-8") as config_file:
        json.dump({API_KEY_ENV_VAR: cleaned_key}, config_file, indent=2)
        config_file.write("\n")


def get_provider():
    """Return the live provider when configured, or the demo provider otherwise."""
    api_key = _read_api_key()
    if api_key:
        if len(api_key) != 32:
            st.warning(
                "The OpenWeatherMap API key is not 32 characters long. "
                "Check the environment variable, AppData config, or "
                "`.streamlit/secrets.toml`."
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
