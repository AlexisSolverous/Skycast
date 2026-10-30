# SkyCast

SkyCast is a Python and Streamlit trip planner with a dark weather dashboard.
Plan trips with multiple dated destinations, view their route on a map, and
check current conditions and a five-day forecast.

## Features

- Create an account and log in with a username and password.
- Stay signed in on this browser for up to 30 days; logging out revokes the
  remembered session.
- View current conditions, weather highlights, and a grouped five-day forecast
  in a dark, wide dashboard.
- Use demo weather with no API key, or configure an existing OpenWeatherMap key
  for live weather data.
- Plan trips with multiple dated destinations and notes.
- View trip routes on a map, identify start and finish stops, and zoom to a stop
  or the full route.
- Review trip summaries and destination weather advisories.
- Store accounts, trips, and destinations in a local SQLite database.

## Run SkyCast

### Run in the browser 

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

### Run as a desktop app 

```powershell
py desktop.py
```

This launches a native Windows window titled "SkyCast" with a separate
Streamlit server process in the background. The app still uses the same code in
`app.py`, so all existing features and the browser workflow continue to work.

### Build the .exe

1. Install PyInstaller if it is not already present:

   ```powershell
   py -m pip install pyinstaller
   ```

2. Build the packaged app from the project root:

   ```powershell
   py -m PyInstaller --noconfirm --clean --onedir --windowed --name SkyCast --icon ".\assets\icon.ico" .\skycast.spec
   ```

3. The output executable is:

   ```text
   dist\SkyCast\SkyCast.exe
   ```

See also `build_exe.md` for the full PyInstaller checklist, likely build errors,
and test plan.

SkyCast works without an API key. In demo mode, it uses sample current weather
and a sample five-day forecast. To use a live OpenWeatherMap key, the app checks
these locations in order:

1. `OPENWEATHER_API_KEY` environment variable
2. `%APPDATA%\SkyCast\config.json`
3. `.streamlit/secrets.toml`

A saved key can be entered from the weather tools section of the app; it is kept
in the user's AppData folder instead of the install directory so it is not
embedded inside the exe. If you prefer to use a file instead of the app form,
this is the supported config shape:

```json
{
  "OPENWEATHER_API_KEY": "your-existing-openweathermap-key"
}
```

No paid service, account, or additional API key is needed. The application stores
user accounts, trips, and destinations in `database/skycast.db` in development,
while the packaged app writes the database and runtime data to `%APPDATA%\SkyCast`.
The remember-me cookie contains a random token that is readable by browser
JavaScript; it is not an HttpOnly cookie, so use this custom login only for
trusted, low-risk deployments.

## Run tests

```powershell
py -m pytest
```

## Project structure

- `app.py` - home page, login, and account creation
- `desktop.py` - native Windows desktop launcher using `pywebview`
- `desktop_server.py` - Streamlit child process for the desktop window
- `paths.py` - development vs. packaged file and data paths
- `pages/1_Dashboard.py` - weather and trip overview
- `pages/2_Trips.py` - trip itinerary, destination forms, and route map
- `ui.py` - shared page setup, dark theme, cards, weather icons, and forecast
  helpers
- `models/` - users, trips, cities, and weather providers
- `database/` - SQLite schema and database access
- `map_view.py` - route markers and map focus views
- `build_exe.md` - PyInstaller build instructions and troubleshooting
- `skycast.spec` - PyInstaller spec for a packaged Windows desktop build
