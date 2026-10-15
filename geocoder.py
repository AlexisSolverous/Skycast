import threading
import time

import requests
import streamlit as st


_last_nominatim_request = 0.0
_nominatim_lock = threading.Lock()
_NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
_USER_AGENT = "SkyCast-SchoolProject"


def _wait_for_nominatim_slot():
    """Keep uncached Nominatim request starts at least one second apart."""
    global _last_nominatim_request
    with _nominatim_lock:
        now = time.monotonic()
        wait_seconds = 1.0 - (now - _last_nominatim_request)
        if wait_seconds > 0:
            time.sleep(wait_seconds)
        _last_nominatim_request = time.monotonic()


@st.cache_data(ttl=86400, show_spinner=False)
def _search_nominatim(query):
    _wait_for_nominatim_slot()
    response = requests.get(
        _NOMINATIM_URL,
        params={
            "q": query,
            "format": "json",
            "limit": 5,
            "addressdetails": 1,
        },
        headers={"User-Agent": _USER_AGENT},
        timeout=10,
    )
    response.raise_for_status()

    results = []
    for item in response.json():
        address = item.get("address") or {}
        display_name = item.get("display_name", "")
        name = item.get("name") or display_name.split(",")[0].strip()
        if not name or "lat" not in item or "lon" not in item:
            continue
        results.append(
            {
                "name": name,
                "country": address.get("country", ""),
                "latitude": float(item["lat"]),
                "longitude": float(item["lon"]),
                "display_name": display_name,
            }
        )
    return results


class PlaceSearch:
    """Search OpenStreetMap's free Nominatim geocoder."""

    def search(self, query):
        cleaned_query = query.strip()
        if not cleaned_query:
            return []
        return _search_nominatim(cleaned_query)
