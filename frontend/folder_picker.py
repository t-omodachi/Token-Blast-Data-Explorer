"""Open a native Windows "choose folder" dialog.

The browser can't pick folders on its own, but the app runs on the user's own
PC, so we pop up a regular Windows dialog using tkinter (built into Python).
It runs in a separate process so it can't freeze the app.
"""

import os
import subprocess
import sys

_DIALOG_CODE = """
import tkinter as tk
from tkinter import filedialog
root = tk.Tk()
root.withdraw()
root.attributes("-topmost", True)
print(filedialog.askdirectory(title="Choose the folder with your levels CSV files"), end="")
"""


def pick_folder() -> str | None:
    """Return the chosen folder path, or None if the user cancelled."""
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    try:
        result = subprocess.run(
            [sys.executable, "-c", _DIALOG_CODE],
            capture_output=True, text=True, encoding="utf-8", env=env, timeout=600,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    folder = result.stdout.strip()
    return os.path.normpath(folder) if folder else None
