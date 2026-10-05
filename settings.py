"""Per-device settings (settings.json, git-ignored): values from --measure and your usual port, used as defaults.

Command-line options always win. Delete settings.json to go back to the built-in defaults.
Set RING_WRITER_SETTINGS to use a different file."""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
KEYS = {"port", "min_flick", "gap", "lockout", "debounce"}


def path():
    return os.environ.get("RING_WRITER_SETTINGS", os.path.join(HERE, "settings.json"))


def load(p=None):
    p = p or path()
    try:
        with open(p) as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {}
    return {k: v for k, v in data.items() if k in KEYS}


def save(updates, p=None):
    """Merge `updates` into the settings file and return the merged dict."""
    p = p or path()
    data = load(p)
    data.update({k: v for k, v in updates.items() if k in KEYS and v is not None})
    with open(p, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    return data
