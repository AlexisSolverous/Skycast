import os
import sys
import traceback

from paths import user_data_dir


def run_streamlit(app_path, app_dir, port):
    """Run Streamlit in its own process, where it can register signal handlers."""
    log_path = user_data_dir() / "skycast.log"
    with log_path.open("a", encoding="utf-8") as log_file:
        sys.stdout = log_file
        sys.stderr = log_file
        try:
            os.chdir(app_dir)
            from streamlit.web import cli as stcli

            sys.argv = [
                "streamlit",
                "run",
                str(app_path),
                "--server.headless=true",
                f"--server.port={port}",
                "--server.address=127.0.0.1",
                "--browser.gatherUsageStats=false",
                "--global.developmentMode=false",
                "--server.fileWatcherType=none",
            ]
            stcli.main()
        except Exception:
            traceback.print_exc(file=log_file)
            raise
