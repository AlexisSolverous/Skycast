import provider_factory
from models.weather import MockWeatherProvider, OpenWeatherAPIProvider


def configure_secrets(monkeypatch, api_key):
    monkeypatch.setattr(
        provider_factory.st,
        "secrets",
        {"OPENWEATHER_API_KEY": api_key},
    )
    monkeypatch.setattr(provider_factory.st, "warning", lambda *_args, **_kwargs: None)


def test_empty_key_uses_demo_provider(monkeypatch):
    configure_secrets(monkeypatch, "")

    provider, is_demo = provider_factory.get_provider()

    assert isinstance(provider, MockWeatherProvider)
    assert is_demo


def test_placeholder_key_uses_demo_provider(monkeypatch):
    configure_secrets(monkeypatch, "  'paste_your_api_key_here'\n")

    provider, is_demo = provider_factory.get_provider()

    assert isinstance(provider, MockWeatherProvider)
    assert is_demo


def test_real_key_is_stripped_of_whitespace_and_quotes(monkeypatch):
    api_key = "0123456789abcdef0123456789abcdef"
    configure_secrets(monkeypatch, f"  '\n {api_key} \r\n'  ")

    provider, is_demo = provider_factory.get_provider()

    assert isinstance(provider, OpenWeatherAPIProvider)
    assert provider.api_key == api_key
    assert not is_demo


def test_non_32_character_key_warns_but_is_not_rejected(monkeypatch):
    configure_secrets(monkeypatch, "short")
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
