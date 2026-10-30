import ctypes
import logging
import multiprocessing
import socket
import time

from desktop_server import run_streamlit
from paths import resource_path, user_data_dir


STARTUP_TIMEOUT_SECONDS = 60
LOGGER = logging.getLogger("skycast.desktop")


def find_free_port():
    """Ask Windows for an available localhost port for the Streamlit server."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind(("127.0.0.1", 0))
        return server_socket.getsockname()[1]


def _configure_logging():
    log_path = user_data_dir() / "skycast.log"
    logging.basicConfig(
        filename=log_path,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        encoding="utf-8",
        force=True,
    )
    return log_path


def _acquire_single_instance():
    """Use a Windows named mutex so a second desktop window is not launched."""
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateMutexW.argtypes = [
        ctypes.c_void_p,
        ctypes.c_bool,
        ctypes.c_wchar_p,
    ]
    kernel32.CreateMutexW.restype = ctypes.c_void_p
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    kernel32.CloseHandle.restype = ctypes.c_bool

    ctypes.set_last_error(0)
    mutex = kernel32.CreateMutexW(None, False, "Local\\SkyCast.Desktop")
    if not mutex:
        raise ctypes.WinError(ctypes.get_last_error())
    if ctypes.get_last_error() == 183:
        kernel32.CloseHandle(mutex)
        ctypes.windll.user32.MessageBoxW(
            None,
            "SkyCast is already running.",
            "SkyCast",
            0x40,
        )
        return None
    return kernel32, mutex


def _show_startup_splash(server_process, port):
    """Show a small native window while checking whether Streamlit is ready."""
    import tkinter as tk

    splash = tk.Tk()
    splash.title("SkyCast")
    splash.geometry("360x120")
    splash.resizable(False, False)
    tk.Label(
        splash,
        text="Starting SkyCast...",
        font=("Segoe UI", 13),
    ).pack(expand=True)

    result = {"ready": False, "error": None}
    deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS

    def check_server():
        if not server_process.is_alive():
            result["error"] = (
                "The Streamlit server stopped during startup "
                f"(exit code {server_process.exitcode})."
            )
            splash.destroy()
            return

        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                result["ready"] = True
                splash.destroy()
                return
        except OSError:
            if time.monotonic() >= deadline:
                result["error"] = (
                    "SkyCast did not start within "
                    f"{STARTUP_TIMEOUT_SECONDS} seconds."
                )
                splash.destroy()
                return

        splash.after(250, check_server)

    splash.after(100, check_server)
    splash.mainloop()
    return result


def _show_error(message):
    try:
        from tkinter import messagebox

        messagebox.showerror("SkyCast", message)
    except Exception:
        LOGGER.exception("Could not display the SkyCast error dialog.")


def _stop_server(server_process):
    if server_process is None or server_process.pid is None:
        return

    if server_process.is_alive():
        LOGGER.info("Stopping the Streamlit server process.")
        server_process.terminate()
    server_process.join(timeout=10)
    if server_process.is_alive():
        LOGGER.warning("Streamlit did not exit; forcing the server process to stop.")
        server_process.kill()
        server_process.join(timeout=5)


def main():
    log_path = _configure_logging()
    instance = None
    server_process = None

    try:
        instance = _acquire_single_instance()
        if instance is None:
            return 0

        app_path = resource_path("app.py")
        app_dir = resource_path(".")
        if not app_path.is_file():
            raise FileNotFoundError(f"Could not find the Streamlit app: {app_path}")

        port = find_free_port()
        server_process = multiprocessing.Process(
            target=run_streamlit,
            args=(app_path, app_dir, port),
            name="SkyCast-Streamlit",
        )
        server_process.start()

        startup = _show_startup_splash(server_process, port)
        if startup["error"]:
            LOGGER.error(startup["error"])
            raise RuntimeError(startup["error"])
        if not startup["ready"]:
            raise RuntimeError("The Streamlit server did not become ready.")

        import webview

        webview.create_window(
            "SkyCast",
            f"http://127.0.0.1:{port}",
            width=1280,
            height=800,
            min_size=(1000, 650),
        )
        LOGGER.info("Opening the SkyCast desktop window.")
        webview.start()
        return 0
    except Exception as exc:
        LOGGER.exception("SkyCast desktop launcher failed.")
        _show_error(f"{exc}\n\nDetails were written to:\n{log_path}")
        return 1
    finally:
        try:
            _stop_server(server_process)
        finally:
            if instance is not None:
                kernel32, mutex = instance
                kernel32.CloseHandle(mutex)


if __name__ == "__main__":
    multiprocessing.freeze_support()
    raise SystemExit(main())
