import json

import provider_factory
from models.weather import MockWeatherProvider, OpenWeatherAPIProvider
from streamlit.errors import StreamlitSecretNotFoundError


def configure_secrets(monkeypatch, api_key, tmp_path):
    monkeypatch.delenv(provider_factory.API_KEY_ENV_VAR, raising=False)
    monkeypatch.setattr(provider_factory, "user_data_dir", lambda: tmp_path)
    monkeypatch.setattr(
        provider_factory.st,
        "secrets",
        {"OPENWEATHER_API_KEY": api_key},
    )
    monkeypatch.setattr(provider_factory.st, "warning", lambda *_args, **_kwargs: None)


def test_empty_key_uses_demo_provider(monkeypatch, tmp_path):
    configure_secrets(monkeypatch, "", tmp_path)

    provider, is_demo = provider_factory.get_provider()

    assert isinstance(provider, MockWeatherProvider)
    assert is_demo


def test_missing_key_uses_demo_provider(monkeypatch, tmp_path):
    configure_secrets(monkeypatch, {}, tmp_path)

    provider, is_demo = provider_factory.get_provider()

    assert isinstance(provider, MockWeatherProvider)
    assert is_demo


def test_unavailable_secrets_use_demo_provider(monkeypatch, tmp_path):
    configure_secrets(monkeypatch, "", tmp_path)

    class MissingSecrets:
        def get(self, _key, _default):
            raise StreamlitSecretNotFoundError("Secrets are not configured.")

    monkeypatch.setattr(provider_factory.st, "secrets", MissingSecrets())

    provider, is_demo = provider_factory.get_provider()

    assert isinstance(provider, MockWeatherProvider)
    assert is_demo


def test_placeholder_key_uses_demo_provider(monkeypatch, tmp_path):
    configure_secrets(monkeypatch, "  'paste_your_api_key_here'\n", tmp_path)

    provider, is_demo = provider_factory.get_provider()

    assert isinstance(provider, MockWeatherProvider)
    assert is_demo


def test_real_key_is_stripped_of_whitespace_and_quotes(monkeypatch, tmp_path):
    api_key = "0123456789abcdef0123456789abcdef"
    configure_secrets(monkeypatch, f"  '\n {api_key} \r\n'  ", tmp_path)

    provider, is_demo = provider_factory.get_provider()

    assert isinstance(provider, OpenWeatherAPIProvider)
    assert provider.api_key == api_key
    assert not is_demo


def test_non_32_character_key_warns_but_is_not_rejected(monkeypatch, tmp_path):
    configure_secrets(monkeypatch, "short", tmp_path)
    warnings = []
    monkeypatch.setattr(
        provider_factory.st,
        "warning",
        lambda message: warnings.append(message),
    )

    provider, is_demo = provider_factory.get_provider()

    assert isinstance(provider, OpenWeatherAPIProvider)
    assert not is_demo
    assert len(warnings) == 1
    assert "not 32 characters" in warnings[0]


def test_api_key_lookup_prefers_environment_then_config_then_secrets(
    monkeypatch, tmp_path
):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps({"OPENWEATHER_API_KEY": "config-key"}),
        encoding="utf-8",
    )
    configure_secrets(monkeypatch, "secrets-key", tmp_path)
    monkeypatch.setenv("OPENWEATHER_API_KEY", "environment-key")

    assert provider_factory._read_api_key() == "environment-key"

    monkeypatch.delenv("OPENWEATHER_API_KEY")
    assert provider_factory._read_api_key() == "config-key"

    config_path.unlink()
    assert provider_factory._read_api_key() == "secrets-key"


def test_save_api_key_writes_user_config(monkeypatch, tmp_path):
    monkeypatch.setattr(provider_factory, "user_data_dir", lambda: tmp_path)

    provider_factory.save_api_key("  saved-key  ")

    config = json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))
    assert config == {"OPENWEATHER_API_KEY": "saved-key"}
