import multiprocessing
import pickle
import socket
import time

from desktop import find_free_port
from desktop_server import run_streamlit


def test_find_free_port_returns_an_available_local_port():
    port = find_free_port()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as test_socket:
        test_socket.bind(("127.0.0.1", port))


def test_streamlit_worker_is_importable_by_spawned_processes():
    assert pickle.loads(pickle.dumps(run_streamlit)) is run_streamlit


def test_streamlit_worker_starts_in_a_separate_process(tmp_path):
    app_path = tmp_path / "test_app.py"
    app_path.write_text("import streamlit as st\nst.write('ready')\n", encoding="utf-8")
    port = find_free_port()
    server_process = multiprocessing.Process(
        target=run_streamlit,
        args=(app_path, tmp_path, port),
    )
    server_process.start()
    ready = False

    try:
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline and server_process.is_alive():
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                    ready = True
                    break
            except OSError:
                time.sleep(0.1)
        assert ready, (
            "Streamlit process did not start "
            f"(exit code {server_process.exitcode})."
        )
    finally:
        if server_process.is_alive():
            server_process.terminate()
        server_process.join(timeout=10)
        if server_process.is_alive():
            server_process.kill()
            server_process.join(timeout=5)
