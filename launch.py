"""Start the Streamlit app and open it in the default browser once it's ready.

Start.bat runs this. It picks a free port, so two copies can run at once.
"""

import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path

from streamlit.web import cli as streamlit_cli

APP_FILE = Path(__file__).with_name("app.py")


def find_free_port(start: int = 8501) -> int:
    for port in range(start, start + 50):
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    return start


def open_browser_when_ready(port: int) -> None:
    for _ in range(120):  # wait up to ~60 seconds
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", port)) == 0:
                webbrowser.open(f"http://localhost:{port}")
                return
        time.sleep(0.5)


if __name__ == "__main__":
    port = find_free_port()
    threading.Thread(target=open_browser_when_ready, args=(port,), daemon=True).start()
    sys.argv = [
        "streamlit", "run", str(APP_FILE),
        "--server.port", str(port),
        "--server.address", "localhost",  # only this PC can open the app
        "--server.headless", "true",
        "--browser.gatherUsageStats", "false",
        "--global.developmentMode", "false",
    ]
    sys.exit(streamlit_cli.main())
