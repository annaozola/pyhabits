import json
import os

_USER_FOLDER = "user"
_CONFIG_FILE = os.path.join(_USER_FOLDER, "config.json")

CONFIG_DEFAULTS = {
    "default_category": "General",
    "date_format": "%Y-%m-%d",
    "exports_folder": "exports",
    "pdf_enabled": True,
    "open_html_after_export": True,
}


def load_config() -> dict:
    if not os.path.exists(_CONFIG_FILE):
        return dict(CONFIG_DEFAULTS)
    try:
        with open(_CONFIG_FILE, "r", encoding="utf-8") as f:
            stored = json.load(f)
        # Merge: stored values take priority; missing keys fall back to defaults
        result = dict(CONFIG_DEFAULTS)
        result.update(stored)
        return result
    except (json.JSONDecodeError, OSError):
        return dict(CONFIG_DEFAULTS)


def save_config(config: dict) -> None:
    os.makedirs(_USER_FOLDER, exist_ok=True)
    with open(_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)


def get(key: str):
    """Return the config value for key, falling back to CONFIG_DEFAULTS."""
    return load_config().get(key, CONFIG_DEFAULTS.get(key))


def edit_config_interactive() -> None:
    """Simple interactive editor for config settings."""
    config = load_config()
    print("\nCurrent settings:")
    keys = list(CONFIG_DEFAULTS.keys())
    for i, k in enumerate(keys, 1):
        print(f"  {i}. {k} = {config[k]}")
    print(f"  {len(keys) + 1}. Back")

    raw = input("\nEnter setting number to change (or blank to cancel): ").strip()
    if not raw:
        return
    try:
        pick = int(raw) - 1
        if pick == len(keys):
            return
        key = keys[pick]
    except (ValueError, IndexError):
        print("Invalid selection.")
        return

    current = config[key]
    raw_val = input(f"New value for '{key}' [{current}]: ").strip()
    if not raw_val:
        return

    # Coerce to the same type as the default
    default_val = CONFIG_DEFAULTS[key]
    if isinstance(default_val, bool):
        config[key] = raw_val.lower() in ("true", "1", "yes")
    elif isinstance(default_val, int):
        try:
            config[key] = int(raw_val)
        except ValueError:
            print("Expected an integer. Not saved.")
            return
    else:
        config[key] = raw_val

    save_config(config)
    print(f"Saved: {key} = {config[key]}")
