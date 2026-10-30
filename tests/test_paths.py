import paths


def test_resource_path_uses_project_directory_in_development():
    path = paths.resource_path("pages/1_Dashboard.py")

    assert path == paths.PROJECT_DIR / "pages/1_Dashboard.py"


def test_resource_path_uses_pyinstaller_bundle_directory(tmp_path, monkeypatch):
    monkeypatch.setattr(paths.sys, "frozen", True, raising=False)
    monkeypatch.setattr(paths.sys, "_MEIPASS", str(tmp_path), raising=False)

    assert paths.resource_path("app.py") == tmp_path / "app.py"


def test_user_data_dir_uses_appdata_and_creates_folder(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))

    data_dir = paths.user_data_dir()

    assert data_dir == tmp_path / "SkyCast"
    assert data_dir.is_dir()
