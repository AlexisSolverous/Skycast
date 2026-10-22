from collections import Counter, defaultdict
from contextlib import contextmanager
from datetime import date, datetime

import streamlit as st


def setup_page(title, icon):
    """Set a consistent wide layout and apply SkyCast's shared theme."""
    st.set_page_config(page_title=title, page_icon=icon, layout="wide")
    apply_theme()


def apply_theme():
    """Apply the dashboard's shared dark colors and card styling."""
    st.markdown(
        """
        <style>
        :root {
            --skycast-background: #10151d;
            --skycast-card: #19222e;
            --skycast-card-raised: #202c39;
            --skycast-text: #f1f5f9;
            --skycast-muted: #a7b3c2;
            --skycast-border: rgba(210, 225, 240, 0.12);
            --skycast-accent: #84c5ff;
        }

        .stApp {
            background: var(--skycast-background);
            color: var(--skycast-text);
        }
        [data-testid="stHeader"] {
            background: transparent;
        }
        [data-testid="stHorizontalBlock"] {
            align-items: stretch;
            gap: 1rem;
        }
        [data-testid="column"] {
            display: flex;
            flex-direction: column;
        }
        [data-testid="stVerticalBlockBorderWrapper"] {
            height: 100%;
            border: 1px solid var(--skycast-border);
            border-radius: 18px;
            background: var(--skycast-card);
            padding: 1.1rem;
        }
        [data-testid="stMetric"] {
            background: var(--skycast-card-raised);
            border: 1px solid var(--skycast-border);
            border-radius: 14px;
            padding: 0.8rem;
        }
        .skycast-temperature {
            color: var(--skycast-text);
            font-size: clamp(3rem, 5vw, 5rem);
            font-weight: 750;
            letter-spacing: -0.06em;
            line-height: 1.05;
        }
        .skycast-weather-icon {
            font-size: 3rem;
            line-height: 1.2;
        }
        .skycast-muted {
            color: var(--skycast-muted);
        }
        h1, h2, h3, h4, p, label {
            color: var(--skycast-text);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


@contextmanager
def card(title):
    """Group related dashboard content in a consistent bordered card."""
    with st.container(border=True):
        st.markdown(f"#### {title}")
        yield


def weather_icon(main_category):
    """Return a simple weather emoji for an OpenWeatherMap category."""
    icons = {
        "clear": "☀️",
        "clouds": "⛅",
        "rain": "🌧️",
        "drizzle": "🌦️",
        "thunderstorm": "⛈️",
        "snow": "❄️",
        "mist": "🌫️",
    }
    return icons.get(str(main_category).strip().lower(), "🌡️")


def greeting(username, hour=None):
    """Build the greeting for an hour from 0 to 23 (local time by default)."""
    if hour is None:
        hour = datetime.now().hour
    if 5 <= hour < 12:
        time_of_day = "Good Morning"
    elif 12 <= hour < 17:
        time_of_day = "Good Afternoon"
    else:
        time_of_day = "Good Evening"
    return f"Hi, {username} / {time_of_day}"


def group_forecast_by_day(readings):
    """Summarize forecast readings into up to five daily high/low cards."""
    grouped = defaultdict(list)
    for reading in readings:
        forecast_date = getattr(reading, "forecast_date", None)
        if forecast_date is None:
            forecast_date = date.today().isoformat()
        grouped[str(forecast_date)].append(reading)

    daily = []
    for forecast_date in sorted(grouped)[:5]:
        day_readings = grouped[forecast_date]
        categories = Counter(item.main_category for item in day_readings)
        common_category = categories.most_common(1)[0][0]
        daily.append(
            {
                "date": date.fromisoformat(forecast_date),
                "high": max(item.temperature for item in day_readings),
                "low": min(item.temperature for item in day_readings),
                "main_category": common_category,
            }
        )
    return daily
