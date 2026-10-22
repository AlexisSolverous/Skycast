# SkyCast

SkyCast is a Python and Streamlit trip planner with a dark weather dashboard.
Plan trips with multiple dated destinations, view their route on a map, and
check current conditions and a five-day forecast.

## Run SkyCast

1. Install Python 3 and the project dependencies:

   ```powershell
   py -m pip install -r requirements.txt
   ```

2. Start the app:

   ```powershell
   py -m streamlit run app.py
   ```

3. Create an account from the home page, then use the sidebar to open the
   Dashboard or Trips page.

SkyCast works without an API key. In demo mode, it uses sample current weather
and a sample five-day forecast. To use your existing OpenWeatherMap key, add it
to `.streamlit/secrets.toml`:

```toml
OPENWEATHER_API_KEY = "your-existing-openweathermap-key"
```

No paid service, account, or additional API key is needed. The application
stores user accounts, trips, and destinations in `database/skycast.db`.

## Run tests

```powershell
py -m pytest
```

## Project structure

- `app.py` - home page, login, and account creation
- `pages/1_Dashboard.py` - weather and trip overview
- `pages/2_Trips.py` - trip itinerary, destination forms, and route map
- `ui.py` - shared page setup, dark theme, cards, weather icons, and forecast
  helpers
- `models/` - users, trips, cities, and weather providers
- `database/` - SQLite schema and database access
- `map_view.py` - route markers and map focus views
