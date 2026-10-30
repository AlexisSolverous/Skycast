# Build SkyCast into a Windows desktop .exe

This project is built for Windows with PyInstaller in `--onedir` mode so the app starts faster and is less likely to trigger antivirus false positives than a single-file exe.

## 1) Install PyInstaller

```powershell
py -m pip install pyinstaller
```

## 2) Place the app icon

The repo includes a simple starter icon at `assets\icon.ico`.

If you already have a better icon, replace that file and keep the same path.

## 3) Build the .exe

This direct command is the exact Windows PowerShell build command for the app. The repo also includes a `skycast.spec` file, but PyInstaller rejects mixing `.spec` with the same build flags, so the CLI form below is the simplest supported version.

```powershell
py -m PyInstaller --noconfirm --clean --onedir --windowed --name SkyCast --icon ".\assets\icon.ico" --collect-all streamlit --collect-all pydeck --copy-metadata streamlit --copy-metadata requests --copy-metadata charset_normalizer --copy-metadata idna --copy-metadata certifi --copy-metadata urllib3 --copy-metadata toml --add-data "app.py;." --add-data "pages;pages" --add-data "models;models" --add-data "database;database" --add-data ".streamlit;.streamlit" app.py
```

This command includes the required settings and data files:

- `--onedir`
- `--windowed`
- `--name SkyCast`
- `--collect-all streamlit`
- `--collect-all pydeck`
- `--copy-metadata streamlit`
- `--copy-metadata requests`
- `--copy-metadata charset_normalizer`
- `--copy-metadata idna`
- `--copy-metadata certifi`
- `--copy-metadata urllib3`
- `--copy-metadata toml`
- `--add-data "app.py;."`
- `--add-data "pages;pages"`
- `--add-data "models;models"`
- `--add-data "database;database"`
- `--add-data ".streamlit;.streamlit"`

The built app will appear in:

```text
dist\SkyCast\SkyCast.exe
```

## 4) Smoke-test checklist after building

- Start the app from `dist\SkyCast\SkyCast.exe`.
- Confirm the app opens as a native desktop window, not a browser tab.
- Log in and create a user account.
- Save a trip and confirm the trip persists after closing and reopening the app.
- Check the map loads and trip routes render.
- Close the window and verify the Streamlit child process stops.
- Confirm the database and app data are stored under `%APPDATA%\SkyCast` instead of the install directory.

## 5) Most common PyInstaller + Streamlit errors and fixes

### Missing metadata error

Example errors: `ModuleNotFoundError` for `streamlit`, `requests`, or `toml` during build time.

Fix:

```powershell
py -m pip install -r requirements.txt
py -m PyInstaller --collect-all streamlit --collect-all pydeck --copy-metadata streamlit --copy-metadata requests ...
```

### Missing page files or app assets

Symptoms: blank app, no sidebar pages, or runtime file-not-found errors.

Fix:

- Include `app.py` and the `pages/`, `models/`, `database/`, and `.streamlit` folders as `--add-data` entries.
- Make sure the app is started from the project root or use `paths.resource_path()` for file lookups.

### Blank window after launch

Symptoms: the exe starts but the app window stays empty or does not display content.

Fix:

- Make sure `webview.create_window(...)` loads `http://127.0.0.1:<port>` after the Streamlit server is ready.
- Confirm `streamlit` is started in a separate process with correct headless settings.
- Check `%APPDATA%\SkyCast\skycast.log` for startup errors.

### Read-only install folder issues

Symptoms: SQLite or data writes fail when the app is installed under `Program Files`.

Fix:

- Use `paths.user_data_dir()` and save data to `%APPDATA%\SkyCast`.
- Keep the packaged app read-only in the install folder and write runtime state to the user profile.
