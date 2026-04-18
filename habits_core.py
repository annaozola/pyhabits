import json
import csv
import os
import time
import difflib
import calendar
from datetime import datetime, timedelta

USER_FOLDER = "user"
EXPORTS_FOLDER = "exports"
HABIT_FILE = os.path.join(USER_FOLDER, "habits.json")
DAYS_OF_WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
DEFAULT_CATEGORY = "General"
REPORT_YEAR_MIN = 2000
REPORT_YEAR_MAX = 2100


def ensure_user_folder_exists():
    if not os.path.exists(USER_FOLDER):
        os.makedirs(USER_FOLDER)


def ensure_exports_folder_exists():
    if not os.path.exists(EXPORTS_FOLDER):
        os.makedirs(EXPORTS_FOLDER)
    year_folder = os.path.join(EXPORTS_FOLDER, str(datetime.now().year))
    if not os.path.exists(year_folder):
        os.makedirs(year_folder)


def get_visualization_folder():
    today_str = datetime.now().strftime("%d-%m-%Y")
    year_str = str(datetime.now().year)
    folder = os.path.join(EXPORTS_FOLDER, year_str, today_str)
    if not os.path.exists(folder):
        os.makedirs(folder)
    return folder


def is_completed(val) -> bool:
    """True if val represents a completion — boolean True or a positive number."""
    if val is True:
        return True
    if isinstance(val, (int, float)) and val > 0:
        return True
    return False


def normalize_habit_data(data):
    if not isinstance(data, dict):
        return {
            "measurement": None,
            "completion": {},
            "archived": False,
            "category": DEFAULT_CATEGORY,
            "icon": None,
        }
    out = {**data}
    out.setdefault("completion", {})
    if "measurement" not in out:
        out["measurement"] = None
    out.setdefault("archived", False)
    cat = out.get("category")
    out["category"] = (cat.strip() if isinstance(cat, str) and cat.strip() else DEFAULT_CATEGORY)
    icon = out.get("icon")
    out["icon"] = icon if isinstance(icon, str) and icon.strip() else None
    return out


def load_habits():
    ensure_user_folder_exists()
    if os.path.exists(HABIT_FILE):
        with open(HABIT_FILE, "r", encoding="utf-8") as file:
            raw = json.load(file)
        return {k: normalize_habit_data(v) for k, v in raw.items()}
    return {}


def save_habits(habits):
    ensure_user_folder_exists()
    with open(HABIT_FILE, "w", encoding="utf-8") as file:
        json.dump(habits, file, indent=4, ensure_ascii=False)


def active_habits(habits):
    return {k: v for k, v in habits.items() if not v.get("archived", False)}


def active_habits_ordered(habits):
    items = [(name, habits[name]) for name in habits if not habits[name].get("archived", False)]
    items.sort(key=lambda x: (x[1].get("category") or DEFAULT_CATEGORY, x[0].lower()))
    return items


def format_habit_label(name, data):
    icon = data.get("icon")
    if icon:
        return f"{icon} {name}"
    return name


def parse_habit_pick(raw, n):
    s = raw.strip()
    if s.endswith(".") and s[:-1].isdigit():
        s = s[:-1]
    if not s.isdigit():
        return None
    i = int(s)
    if 1 <= i <= n:
        return i - 1
    return None


def get_current_date():
    return datetime.now().strftime("%Y-%m-%d")


def get_current_day():
    return datetime.now().strftime("%A")


def get_current_week():
    today = datetime.now()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    return start_of_week.strftime("%Y-%m-%d"), end_of_week.strftime("%Y-%m-%d")


def get_current_month():
    today = datetime.now()
    start_of_month = today.replace(day=1)
    end_of_month = (start_of_month + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    return start_of_month.strftime("%Y-%m-%d"), end_of_month.strftime("%Y-%m-%d")


def min_max_years_from_habits(habits, habit_names=None):
    years = []
    names = habit_names if habit_names is not None else list(habits.keys())
    for hn in names:
        if hn not in habits:
            continue
        for d in habits[hn].get("completion", {}):
            try:
                years.append(int(d[:4]))
            except (ValueError, TypeError):
                continue
    if not years:
        y = datetime.now().year
        return y, y
    return min(years), max(years)


def prompt_report_year(habits, scope_habit_names=None):
    default_y = datetime.now().year
    mn, mx = min_max_years_from_habits(habits, scope_habit_names)
    hint = f" ({mn}–{mx} in your data)" if mn != mx or scope_habit_names else ""
    raw = input(f"\nYear for this report [{default_y}]{hint}: ").strip()
    if not raw:
        return default_y
    try:
        y = int(raw)
    except ValueError:
        print(f"Invalid year; using {default_y}.")
        return default_y
    if y < REPORT_YEAR_MIN or y > REPORT_YEAR_MAX:
        print(f"Year must be between {REPORT_YEAR_MIN} and {REPORT_YEAR_MAX}; using {default_y}.")
        return default_y
    return y



def suggest_close_habit_names(typed, active_names):
    if not active_names:
        return []
    lower_map = {n.lower(): n for n in active_names}
    candidates = list(lower_map.keys())
    matches = difflib.get_close_matches(typed.lower(), candidates, n=3, cutoff=0.55)
    return [lower_map[m] for m in matches]


def find_active_by_casefold(habits, typed):
    t = typed.lower()
    for name, d in active_habits(habits).items():
        if name.lower() == t:
            return name
    return None


def resolve_new_habit_flow(habits, habit_name):
    measurement = input(
        f"Enter the measurement for '{habit_name}' (e.g., '15 pages', '30 min', '2 km') or press Enter to skip: "
    ).strip()
    cat_raw = input(f"Category [{DEFAULT_CATEGORY}]: ").strip()
    category = cat_raw if cat_raw else DEFAULT_CATEGORY
    icon_raw = input("Optional icon (emoji or single char, Enter to skip): ").strip()
    icon = icon_raw if icon_raw else None
    habits[habit_name] = normalize_habit_data({
        "measurement": measurement if measurement else None,
        "completion": {},
        "archived": False,
        "category": category,
        "icon": icon,
    })


def clean_old_exports(keep_days: int = 30) -> tuple:
    """Delete files in EXPORTS_FOLDER older than keep_days days, then remove empty dirs.

    Returns (files_deleted, dirs_deleted).
    """
    if not os.path.exists(EXPORTS_FOLDER):
        return 0, 0

    cutoff = time.time() - keep_days * 86400
    files_deleted = 0
    dirs_deleted = 0

    # Walk bottom-up so we can remove empty directories after deleting files
    for dirpath, dirnames, filenames in os.walk(EXPORTS_FOLDER, topdown=False):
        for fname in filenames:
            fpath = os.path.join(dirpath, fname)
            try:
                if os.path.getmtime(fpath) < cutoff:
                    os.remove(fpath)
                    files_deleted += 1
            except OSError:
                pass
        # Remove directory if now empty (and not the root exports folder itself)
        if dirpath != EXPORTS_FOLDER:
            try:
                if not os.listdir(dirpath):
                    os.rmdir(dirpath)
                    dirs_deleted += 1
            except OSError:
                pass

    return files_deleted, dirs_deleted
