import json
import csv
import os
import sys
import calendar
import html
import webbrowser
import difflib
import re
from datetime import datetime, timedelta
import pdfkit

# Folder structure
USER_FOLDER = "user"
EXPORTS_FOLDER = "exports"
HABIT_FILE = os.path.join(USER_FOLDER, "habits.json")
DAYS_OF_WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
DEFAULT_CATEGORY = "General"
REPORT_YEAR_MIN = 2000
REPORT_YEAR_MAX = 2100

# ======================
# Terminal UI (menu banner)
# Brand: primary #D24441, banner #473335; accents = primary at 75% / 35% / 15% over banner.
# ======================

class _Term:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    WHITE = "\033[97m"


_BRAND_PRIMARY = (0xD2, 0x44, 0x41)  # #D24441
_BRAND_BANNER_BG = (0x47, 0x33, 0x35)  # #473335
_BRAND_MENU_BG = (30, 30, 30)


def _blend_rgb(fg, bg, alpha):
    return tuple(round(fg[i] * alpha + bg[i] * (1 - alpha)) for i in range(3))


def _brand_on_banner(alpha):
    return _blend_rgb(_BRAND_PRIMARY, _BRAND_BANNER_BG, alpha)


def _brand_on_menu_bg(alpha):
    return _blend_rgb(_BRAND_PRIMARY, _BRAND_MENU_BG, alpha)


_BRAND_SUBTITLE_RGB = _brand_on_banner(0.75)
_BRAND_DECOR_RGB = _brand_on_banner(0.35)
_BRAND_BORDER_RGB = _brand_on_menu_bg(0.75)
_BRAND_MENU_ACCENT_RGB = _brand_on_menu_bg(0.35)


def _tc_fg(rgb):
    r, g, b = rgb
    return f"\033[38;2;{r};{g};{b}m"


def _tc_bg(rgb):
    r, g, b = rgb
    return f"\033[48;2;{r};{g};{b}m"


_STYLE_OK = False


def _enable_windows_ansi():
    if sys.platform != "win32":
        return
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)
        mode = ctypes.c_ulong()
        if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            return
        mode.value |= 0x0004
        kernel32.SetConsoleMode(handle, mode.value)
    except (OSError, AttributeError, ValueError):
        pass


def init_terminal_ui():
    """Enable ANSI colors when possible; safe no-op for logs / pipes."""
    global _STYLE_OK
    _STYLE_OK = bool(sys.stdout.isatty())
    if _STYLE_OK:
        _enable_windows_ansi()


def _s(code: str, text: str) -> str:
    if not _STYLE_OK:
        return text
    return f"{code}{text}{_Term.RESET}"


def _menu_inner_width() -> int:
    return 44


def _today_menu_subtitle() -> str:
    """e.g. 'Thursday, 2 April' (full month name)."""
    d = datetime.now()
    return f"{d.strftime('%A')}, {d.day} {d.strftime('%B')}"


def _subtitle_seq():
    """Same colour for subtitle + date (full header and compact header)."""
    return _tc_fg(_BRAND_SUBTITLE_RGB)


_BRAND_DONE_GREEN = (0x3C, 0xCD, 0x6C)  # #3CCD6C (completed today)


def _habit_done_status_mark(completed: bool) -> str:
    """✓ in brand green; ✗ in 75% primary-on-banner tint. Plain if colours off."""
    if not _STYLE_OK:
        return "✓" if completed else "✗"
    if completed:
        return _s(_tc_fg(_BRAND_DONE_GREEN), "✓")
    return _s(_tc_fg(_BRAND_SUBTITLE_RGB), "✗")


def print_main_menu(*, show_header_art: bool = True):
    """
    Framed main menu. Use show_header_art=False after first return for a shorter prompt.
    """
    w = _menu_inner_width()
    bar = "─" * w
    border = _tc_fg(_BRAND_BORDER_RGB)
    v = _s(border, "│")
    edge_top = _s(border, "╭" + bar + "╮")
    edge_bot = _s(border, "╰" + bar + "╯")

    primary_word = _tc_fg(_BRAND_PRIMARY) + _Term.BOLD
    sub = _subtitle_seq()
    decor = _tc_fg(_BRAND_DECOR_RGB)
    accent = _tc_fg(_BRAND_MENU_ACCENT_RGB)

    rows = []

    if show_header_art:
        rows.append("")
        if _STYLE_OK:
            bg = _tc_bg(_BRAND_BANNER_BG)
            row1 = (
                "  "
                + bg
                + "  "
                + decor
                + "····"
                + _Term.RESET
                + bg
                + "   "
                + primary_word
                + "pyhabits"
                + _Term.RESET
                + bg
                + "   "
                + decor
                + "····"
                + _Term.RESET
                + bg
                + "                    "
                + _Term.RESET
            )
            sub_text = f"      terminal habit tracker  · {_today_menu_subtitle()}"
            row2 = (
                "  "
                + bg
                + sub
                + sub_text
                + _Term.RESET
                + bg
                + " " * max(0, 52 - len(sub_text))
                + _Term.RESET
            )
            rows.append(row1)
            rows.append(row2)
        else:
            rows.append("            ·····  pyhabits  ·····")
            rows.append(f"      terminal habit tracker  · {_today_menu_subtitle()}")
        rows.append("")
    else:
        rows.append("")
        rows.append(
            _s(accent, "  ───  ")
            + _s(primary_word, "pyhabits")
            + _s(accent, "  · main menu ───  ")
            + _s(sub, _today_menu_subtitle())
        )
        rows.append("")

    rows.append("  " + edge_top)

    pad_line = " " * w
    rows.append("  " + v + pad_line + v)

    menu_items = [
        ("1", "Track a habit for today"),
        ("2", "View habits for today"),
        ("3", "View habits for this week"),
        ("4", "View habits for this month"),
        ("5", "Generate visualization (HTML/PDF)"),
        ("6", "Manage habits"),
        ("7", "Exit"),
    ]

    plain_tpl = " {} · {}"
    num_sty = _tc_fg(_BRAND_PRIMARY) + _Term.BOLD
    for num, label in menu_items:
        left = _s(num_sty, f" {num} ")
        mid = _s(accent, "·")
        rest = _s(_Term.WHITE, f" {label}")
        inner = left + mid + rest
        raw_len = len(plain_tpl.format(num, label))
        pad = max(0, w - raw_len - 2)
        rows.append("  " + v + " " + inner + " " * pad + " " + v)

    rows.append("  " + v + pad_line + v)
    rows.append("  " + edge_bot)
    print("\n".join(rows))


def input_main_choice() -> str:
    """Prompt after the framed menu (colors when TTY)."""
    prompt = (
        "\n  "
        + _s(_tc_fg(_BRAND_PRIMARY), "▸")
        + " "
        + _s(_Term.WHITE + _Term.BOLD, "Choose")
        + _s(_tc_fg(_BRAND_MENU_ACCENT_RGB), " — type 1–7, then Enter: ")
    )
    return input(prompt).strip()


# Light, print-first styles. wkhtmltopdf often does not apply @media print, so defaults must be PDF-safe.
VISUALIZATION_CSS = """
    :root {
        --paper: #ffffff;
        --surface: #f1f5f9;
        --text: #0f172a;
        --muted: #475569;
        --rule: #1e3a5f;
        --month-border: #94a3b8;
        --day-border: #cbd5e1;
        --day-empty-bg: #ffffff;
        --done-fill: #166534;
        --done-text: #ffffff;
        --done-border: #14532d;
    }
    * { box-sizing: border-box; }
    @page { size: A4 portrait; }
    html {
        -webkit-print-color-adjust: exact;
        print-color-adjust: exact;
        color-adjust: exact;
    }
    body {
        font-family: "Source Sans 3", "Segoe UI", "Helvetica Neue", Arial, sans-serif;
        margin: 0;
        padding: 0;
        background: var(--paper);
        color: var(--text);
        line-height: 1.45;
        font-size: 11pt;
    }
    .wrap {
        max-width: 100%;
        margin: 0 auto;
        padding: 0;
    }
    .doc-header {
        border-bottom: 3px solid var(--rule);
        padding-bottom: 12px;
        margin-bottom: 24px;
    }
    .doc-header h1 {
        font-family: "Fraunces", "Iowan Old Style", "Palatino Linotype", Georgia, serif;
        font-weight: 600;
        font-size: 22pt;
        margin: 0 0 6px 0;
        letter-spacing: -0.02em;
        color: var(--text);
    }
    .doc-header .meta {
        color: var(--muted);
        font-size: 10pt;
        margin: 0;
    }
    .habit-section {
        margin-bottom: 28px;
        page-break-before: always;
        break-before: page;
    }
    .habit-section.first {
        page-break-before: auto;
        break-before: auto;
    }
    .habit-section h2 {
        font-family: "Fraunces", "Iowan Old Style", "Palatino Linotype", Georgia, serif;
        font-size: 14pt;
        font-weight: 600;
        margin: 0 0 8px 0;
        padding-bottom: 6px;
        border-bottom: 1px solid var(--day-border);
        color: var(--rule);
    }
    .habit-section .sub {
        color: var(--muted);
        font-size: 9.5pt;
        margin: 0 0 14px 0;
    }
    .year {
        display: flex;
        flex-wrap: wrap;
        gap: 14px 12px;
        align-items: flex-start;
    }
    .month {
        width: 212px;
        background: var(--surface);
        border: 1px solid var(--month-border);
        border-radius: 2px;
        padding: 10px 8px 8px;
        break-inside: avoid;
        page-break-inside: avoid;
        -webkit-print-color-adjust: exact;
        print-color-adjust: exact;
    }
    .month-name {
        font-weight: 600;
        text-align: center;
        margin-bottom: 8px;
        font-size: 9.5pt;
        color: var(--text);
        letter-spacing: 0.02em;
    }
    .calendar {
        display: grid;
        grid-template-columns: repeat(7, 1fr);
        gap: 2px;
        border: 1px solid var(--day-border);
        background: var(--day-border);
    }
    .day {
        height: 28px;
        min-width: 0;
        text-align: center;
        font-size: 9pt;
        font-weight: 500;
        line-height: 28px;
        border: none;
        -webkit-print-color-adjust: exact;
        print-color-adjust: exact;
    }
    .day.completed {
        background: var(--done-fill) !important;
        color: var(--done-text) !important;
        font-weight: 700;
    }
    .day.empty {
        background: var(--day-empty-bg) !important;
        color: var(--muted);
    }
    @media screen {
        body {
            padding: 24px 20px 40px;
            background: #e2e8f0;
        }
        .wrap {
            max-width: 900px;
            background: var(--paper);
            padding: 32px 36px;
            box-shadow: 0 4px 24px rgba(15, 23, 42, 0.08);
            border: 1px solid var(--day-border);
        }
    }
"""


# ======================
# Core Functions
# ======================

def ensure_user_folder_exists():
    """Ensure the 'user' folder exists."""
    if not os.path.exists(USER_FOLDER):
        os.makedirs(USER_FOLDER)


def ensure_exports_folder_exists():
    """Ensure the exports folder structure exists."""
    if not os.path.exists(EXPORTS_FOLDER):
        os.makedirs(EXPORTS_FOLDER)

    current_year = datetime.now().strftime("%Y")
    year_folder = os.path.join(EXPORTS_FOLDER, current_year)
    if not os.path.exists(year_folder):
        os.makedirs(year_folder)

    return year_folder


def get_visualization_folder():
    """Get the visualization folder path with date structure."""
    year_folder = ensure_exports_folder_exists()
    date_folder = datetime.now().strftime("%d-%m-%Y")
    vis_folder = os.path.join(year_folder, date_folder)

    if not os.path.exists(vis_folder):
        os.makedirs(vis_folder)

    return vis_folder


def normalize_habit_data(data):
    """Ensure habit dict has archived, category, icon, completion."""
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
    """Load habits from the JSON file."""
    ensure_user_folder_exists()
    if os.path.exists(HABIT_FILE):
        with open(HABIT_FILE, "r", encoding="utf-8") as file:
            raw = json.load(file)
        return {k: normalize_habit_data(v) for k, v in raw.items()}
    return {}


def save_habits(habits):
    """Save habits to the JSON file."""
    ensure_user_folder_exists()
    with open(HABIT_FILE, "w", encoding="utf-8") as file:
        json.dump(habits, file, indent=4, ensure_ascii=False)


def active_habits(habits):
    """Habit names that are not archived."""
    return {k: v for k, v in habits.items() if not v.get("archived", False)}


def active_habits_ordered(habits):
    """List of (name, data) sorted by category then habit name."""
    items = [(name, habits[name]) for name in habits if not habits[name].get("archived", False)]
    items.sort(key=lambda x: (x[1].get("category") or DEFAULT_CATEGORY, x[0].lower()))
    return items


def format_habit_label(name, data):
    """Display label with optional icon."""
    icon = data.get("icon")
    if icon:
        return f"{icon} {name}"
    return name


def parse_habit_pick(raw, n):
    """If input is integer 1..n (optional trailing '.'), return index 0-based; else None."""
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
    """Get today's date in YYYY-MM-DD format."""
    return datetime.now().strftime("%Y-%m-%d")


def get_current_day():
    """Get today's day of the week."""
    return datetime.now().strftime("%A")


def get_current_week():
    """Get the current week's start and end dates."""
    today = datetime.now()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    return start_of_week.strftime("%Y-%m-%d"), end_of_week.strftime("%Y-%m-%d")


def get_current_month():
    """Get the current month's start and end dates."""
    today = datetime.now()
    start_of_month = today.replace(day=1)
    end_of_month = (start_of_month + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    return start_of_month.strftime("%Y-%m-%d"), end_of_month.strftime("%Y-%m-%d")


def min_max_years_from_habits(habits, habit_names=None):
    """Infer min/max year from completion keys."""
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
    """Prompt for report year; default current year. scope_habit_names limits date inference."""
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


def print_active_habits_grouped_numbered(habits):
    """Print active habits grouped by category with global indices 1..N. Returns ordered list of names."""
    ordered = active_habits_ordered(habits)
    if not ordered:
        print("\nNo active habits.")
        return []

    print("\nYour saved habits:")
    idx = 1
    current_cat = None
    names_in_order = []
    for name, data in ordered:
        cat = data.get("category") or DEFAULT_CATEGORY
        if cat != current_cat:
            current_cat = cat
            print(f"\n[{cat}]")
        label = format_habit_label(name, data)
        measurement = data.get("measurement")
        if measurement:
            print(f"  {idx}. {label} (Measurement: {measurement})")
        else:
            print(f"  {idx}. {label}")
        names_in_order.append(name)
        idx += 1
    return names_in_order


def suggest_close_habit_names(typed, active_names):
    """Return up to 3 close matches among active habit names (case-insensitive)."""
    if not active_names:
        return []
    lower_map = {n.lower(): n for n in active_names}
    candidates = list(lower_map.keys())
    matches = difflib.get_close_matches(typed.lower(), candidates, n=3, cutoff=0.55)
    return [lower_map[m] for m in matches]


def find_active_by_casefold(habits, typed):
    """Resolve active habit name ignoring case, or None."""
    t = typed.lower()
    for name, d in active_habits(habits).items():
        if name.lower() == t:
            return name
    return None


def resolve_new_habit_flow(habits, habit_name):
    """Prompt measurement, category, icon; insert habit."""
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


# ======================
# Manage habits
# ======================

def manage_habits(habits):
    """Archive, unarchive, edit category/icon, list archived."""
    while True:
        print("\nManage habits")
        print("1. Archive a habit (hide from tracking, keep history)")
        print("2. Unarchive a habit")
        print("3. Edit category / icon for a habit")
        print("4. List archived habits")
        print("5. Back to main menu")
        c = input("Choose (1-5): ").strip()

        if c == "5":
            return
        if c == "4":
            archived = [n for n, d in habits.items() if d.get("archived")]
            if not archived:
                print("No archived habits.")
            else:
                print("\nArchived habits:")
                for n in sorted(archived, key=str.lower):
                    print(f"  - {format_habit_label(n, habits[n])}")
            continue
        if c == "1":
            names = [n for n, d in habits.items() if not d.get("archived")]
            if not names:
                print("No active habits to archive.")
                continue
            print("\nActive habits:")
            for i, n in enumerate(sorted(names, key=str.lower), 1):
                print(f"  {i}. {format_habit_label(n, habits[n])}")
            raw = input("Enter number to archive (or blank to cancel): ").strip()
            if not raw:
                continue
            try:
                pick = int(raw) - 1
                sel = sorted(names, key=str.lower)[pick]
            except (ValueError, IndexError):
                print("Invalid selection.")
                continue
            habits[sel]["archived"] = True
            save_habits(habits)
            print(f"Archived '{sel}' (history preserved).")
            continue
        if c == "2":
            archived = [n for n, d in habits.items() if d.get("archived")]
            if not archived:
                print("No archived habits.")
                continue
            print("\nArchived habits:")
            for i, n in enumerate(sorted(archived, key=str.lower), 1):
                print(f"  {i}. {format_habit_label(n, habits[n])}")
            raw = input("Enter number to unarchive (or blank to cancel): ").strip()
            if not raw:
                continue
            try:
                pick = int(raw) - 1
                sel = sorted(archived, key=str.lower)[pick]
            except (ValueError, IndexError):
                print("Invalid selection.")
                continue
            habits[sel]["archived"] = False
            save_habits(habits)
            print(f"Unarchived '{sel}'.")
            continue
        if c == "3":
            if not habits:
                print("No habits.")
                continue
            all_names = sorted(habits.keys(), key=str.lower)
            print("\nAll habits:")
            for i, n in enumerate(all_names, 1):
                arch = " [archived]" if habits[n].get("archived") else ""
                print(f"  {i}. {format_habit_label(n, habits[n])}{arch}")
            raw = input("Enter number to edit (or blank to cancel): ").strip()
            if not raw:
                continue
            try:
                pick = int(raw) - 1
                sel = all_names[pick]
            except (ValueError, IndexError):
                print("Invalid selection.")
                continue
            data = habits[sel]
            print(f"Current category: {data.get('category', DEFAULT_CATEGORY)}")
            print(f"Current icon: {data.get('icon') or '(none)'}")
            cat_raw = input(f"New category [{data.get('category', DEFAULT_CATEGORY)}]: ").strip()
            if cat_raw:
                data["category"] = cat_raw
            icon_raw = input("New icon (Enter to keep current; type 'clear' to remove): ").strip()
            if icon_raw.lower() == "clear":
                data["icon"] = None
            elif icon_raw:
                data["icon"] = icon_raw
            save_habits(habits)
            print("Updated.")
            continue
        print("Invalid choice.")


# ======================
# Habit Tracking Functions
# ======================

def track_habit(habits):
    """Track a habit for the current day."""
    names_in_order = print_active_habits_grouped_numbered(habits)
    n = len(names_in_order)

    raw_input = input("\nEnter habit number, habit name, or a new name to add: ").strip()
    if not raw_input:
        print("No input.")
        return

    today_date = get_current_date()
    today_day = get_current_day()
    habit_name = None

    if n:
        pick_idx = parse_habit_pick(raw_input, n)
        if pick_idx is not None:
            habit_name = names_in_order[pick_idx]

    active_only = active_habits(habits)
    active_names = list(active_only.keys())

    if habit_name is None:
        ci = find_active_by_casefold(habits, raw_input)
        if ci:
            habit_name = ci
        elif raw_input in habits:
            if habits[raw_input].get("archived"):
                print(f"'{raw_input}' is archived. Unarchive it in Manage habits to track again.")
                return
            habit_name = raw_input
        else:
            matches = suggest_close_habit_names(raw_input, active_names)
            if matches:
                print("\nNo exact match. Did you mean:")
                for i, m in enumerate(matches, 1):
                    print(f"  {i}. {m}")
                print(f"  {len(matches) + 1}. Create new habit '{raw_input}'")
                sel = input("Choose (number): ").strip()
                try:
                    choice_n = int(sel)
                except ValueError:
                    print("Cancelled.")
                    return
                if 1 <= choice_n <= len(matches):
                    habit_name = matches[choice_n - 1]
                elif choice_n == len(matches) + 1:
                    habit_name = None
                else:
                    print("Cancelled.")
                    return
            else:
                habit_name = None

    if habit_name is None:
        resolve_new_habit_flow(habits, raw_input)
        habit_name = raw_input

    if habits[habit_name]["completion"].get(today_date, False):
        print(f"'{habit_name}' already tracked today.")
        return

    habits[habit_name]["completion"][today_date] = True
    print(f"'{habit_name}' marked as completed for {today_day}, {today_date}.")
    save_habits(habits)


# ======================
# Viewing and Export Functions
# ======================

def view_habits(habits, period="today"):
    """View habits for today, this week, or this month."""
    if not habits:
        print("No habits found to display.")
        return

    today_date = get_current_date()
    today_day = get_current_day()
    start_of_week, end_of_week = get_current_week()
    start_of_month, end_of_month = get_current_month()
    week_start_dt = datetime.strptime(start_of_week, "%Y-%m-%d")

    ah = active_habits(habits)
    if not ah:
        print("No active habits. (Archived habits are hidden here — use Manage → List archived.)")
        return

    if period == "today":
        print(f"\nHabits for {today_day}, {today_date}:")
        for habit, data in active_habits_ordered(habits):
            completed = data["completion"].get(today_date, False)
            mark = _habit_done_status_mark(completed)
            label = format_habit_label(habit, data)
            measurement = data.get("measurement")
            if measurement:
                print(f"- {mark}  {label} (Measurement: {measurement})")
            else:
                print(f"- {mark}  {label}")
    elif period == "week":
        print(f"\nHabits for the week {start_of_week} to {end_of_week} (by day):")
        for day in DAYS_OF_WEEK:
            date = (week_start_dt + timedelta(days=DAYS_OF_WEEK.index(day))).strftime("%Y-%m-%d")
            done = []
            for habit, data in active_habits_ordered(habits):
                if data["completion"].get(date, False):
                    done.append(format_habit_label(habit, data))
            if done:
                print(f"\n{day}, {date}:")
                for label in done:
                    print(f"  - {label}")
            else:
                print(f"\n{day}, {date}: (none)")
    elif period == "month":
        print(f"\nHabits for the month {start_of_month} to {end_of_month}:")
        current_date = datetime.strptime(start_of_month, "%Y-%m-%d")
        end_m = datetime.strptime(end_of_month, "%Y-%m-%d")

        while current_date <= end_m:
            date_str = current_date.strftime("%Y-%m-%d")
            day_str = current_date.strftime("%A")
            print(f"\n{day_str}, {date_str}:")
            for habit, data in active_habits_ordered(habits):
                completed = data["completion"].get(date_str, False)
                status = "✓" if completed else "✗"
                label = format_habit_label(habit, data)
                measurement = data.get("measurement")
                if measurement:
                    print(f"- {label} (Measurement: {measurement}): {status}")
                else:
                    print(f"- {label}: {status}")
            current_date += timedelta(days=1)

    if period in ["week", "month"]:
        export_habits(habits, period, start_of_week if period == "week" else start_of_month,
                      end_of_week if period == "week" else end_of_month)


def export_habits(habits, period, start_date, end_date):
    """Export habits to JSON, CSV, or Markdown."""
    ensure_exports_folder_exists()
    while True:
        print("\nExport Options:")
        print("1. Export as JSON")
        print("2. Export as CSV")
        print("3. Export as Markdown")
        print("4. Exit")
        choice = input("Choose an option (1/2/3/4): ").strip()

        if choice == "1":
            filename = os.path.join(EXPORTS_FOLDER, f"habits_{period}_{start_date}_to_{end_date}.json")
            try:
                with open(filename, "w", encoding="utf-8") as file:
                    json.dump(habits, file, indent=4, ensure_ascii=False)
                print(f"Habits exported to {filename}")
            except Exception as e:
                print(f"Error exporting to JSON: {e}")
        elif choice == "2":
            filename = os.path.join(EXPORTS_FOLDER, f"habits_{period}_{start_date}_to_{end_date}.csv")
            try:
                with open(filename, "w", newline="", encoding="utf-8") as file:
                    writer = csv.writer(file)
                    writer.writerow(["Habit", "Measurement", "Category", "Archived", "Date", "Status"])
                    for habit, data in habits.items():
                        for date, completed in data["completion"].items():
                            writer.writerow([
                                habit,
                                data.get("measurement", "") or "",
                                data.get("category", DEFAULT_CATEGORY),
                                "yes" if data.get("archived") else "no",
                                date,
                                "✓" if completed else "✗",
                            ])
                print(f"Habits exported to {filename}")
            except Exception as e:
                print(f"Error exporting to CSV: {e}")
        elif choice == "3":
            filename = os.path.join(EXPORTS_FOLDER, f"habits_{period}_{start_date}_to_{end_date}.md")
            try:
                with open(filename, "w", encoding="utf-8") as file:
                    file.write(f"# Habits for {period} ({start_date} to {end_date})\n\n")
                    if period == "week":
                        week_start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                        ah = dict(active_habits_ordered(habits))
                        for day in DAYS_OF_WEEK:
                            d = (week_start_dt + timedelta(days=DAYS_OF_WEEK.index(day))).strftime("%Y-%m-%d")
                            done = [
                                format_habit_label(h, habits[h])
                                for h in ah
                                if habits[h]["completion"].get(d, False)
                            ]
                            file.write(f"## {day}, {d}\n\n")
                            if done:
                                for label in done:
                                    file.write(f"- {label}\n")
                            else:
                                file.write("- *(none)*\n")
                            file.write("\n")
                    else:
                        for habit, data in habits.items():
                            file.write(f"## {habit}\n")
                            if data.get("measurement"):
                                file.write(f"- **Measurement**: {data['measurement']}\n")
                            file.write("| Date       | Status |\n")
                            file.write("|------------|--------|\n")
                            for date, completed in sorted(data["completion"].items()):
                                file.write(f"| {date} | {'✓' if completed else '✗'} |\n")
                            file.write("\n")
                print(f"Habits exported to {filename}")
            except Exception as e:
                print(f"Error exporting to Markdown: {e}")
        elif choice == "4":
            break
        else:
            print("Invalid choice. Please try again.")


# Visualization: HTML fragments
# ======================

def build_month_calendar_html(data, report_year, month):
    """HTML for one month's grid."""
    _, last = calendar.monthrange(report_year, month)
    month_name = datetime(report_year, month, 1).strftime("%B")
    lines = [
        f'<div class="month">',
        f'<div class="month-name">{html.escape(month_name)} {report_year}</div>',
        '<div class="calendar">',
    ]
    for day in range(1, last + 1):
        date_str = f"{report_year}-{month:02d}-{day:02d}"
        done = data["completion"].get(date_str, False)
        cls = "completed" if done else "empty"
        lines.append(f'<div class="day {cls}" title="{date_str}">{day}</div>')
    lines.append("</div></div>")
    return "".join(lines)


def build_habit_year_section_html(habits, habit_name, report_year, *, first=False):
    """One habit's year block (wrapped section)."""
    data = habits[habit_name]
    icon = data.get("icon") or ""
    cat = data.get("category") or DEFAULT_CATEGORY
    arch = " (archived)" if data.get("archived") else ""
    measurement = data.get("measurement")
    sub_parts = [html.escape(cat)]
    if measurement:
        sub_parts.append(html.escape(str(measurement)))
    sub = " · ".join(sub_parts) + arch
    title = f"{icon} {habit_name}".strip() if icon else habit_name
    cls = "habit-section first" if first else "habit-section"
    parts = [
        f'<section class="{cls}">',
        f"<h2>{html.escape(title)}</h2>",
        f'<p class="sub">{html.escape(sub)}</p>',
        '<div class="year">',
    ]
    for month in range(1, 13):
        parts.append(build_month_calendar_html(data, report_year, month))
    parts.append("</div></section>")
    return "".join(parts)


def build_visualization_html_document(page_title, inner_body):
    """Full HTML document with shared fonts + CSS."""
    esc_title = html.escape(page_title)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8" />
    <title>{esc_title}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,600&family=Source+Sans+3:wght@400;600&display=swap" rel="stylesheet" />
    <style>{VISUALIZATION_CSS}</style>
</head>
<body>
<div class="wrap">
{inner_body}
</div>
</body>
</html>"""


def pdfkit_options():
    """Options tuned for wkhtmltopdf: light CSS + print color fidelity."""
    return {
        "page-size": "A4",
        "margin-top": "12mm",
        "margin-right": "11mm",
        "margin-bottom": "12mm",
        "margin-left": "11mm",
        "encoding": "UTF-8",
        "quiet": "",
        "print-media-type": None,
        "image-quality": "94",
    }


def write_visualization_files(html_content, html_path, pdf_path):
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    pdfkit.from_string(html_content, pdf_path, options=pdfkit_options())
    print(f"\nHTML: {html_path}")
    print(f"PDF: {pdf_path}")
    webbrowser.open(f"file://{os.path.abspath(html_path)}")


# ======================
# Visualization Functions
# ======================

def generate_visualization(habits):
    """Generate HTML and PDF visualizations with organized folder structure"""
    if not habits:
        print("No habits found to visualize.")
        return

    print("\nGenerate visualization for:")
    print("1. All habits")
    print("2. Specific habit")
    choice = input("Choose an option (1/2): ").strip()

    if choice == "2":
        all_names = sorted(habits.keys(), key=str.lower)
        print("\nAvailable habits:")
        for i, habit in enumerate(all_names, 1):
            arch = " [archived]" if habits[habit].get("archived") else ""
            print(f"{i}. {format_habit_label(habit, habits[habit])}{arch}")

        while True:
            try:
                habit_choice = input("\nEnter the number of the habit to visualize (or 'cancel' to go back): ").strip()
                if habit_choice.lower() == "cancel":
                    return

                habit_index = int(habit_choice) - 1
                selected_habit = all_names[habit_index]
                report_year = prompt_report_year(habits, [selected_habit])
                generate_single_visualization(habits, selected_habit, report_year)
                break
            except (ValueError, IndexError):
                print("Invalid selection. Please enter a valid number or 'cancel'.")
    elif choice == "1":
        report_year = prompt_report_year(habits, list(habits.keys()))
        generate_combined_visualization(habits, report_year)
    else:
        print("Invalid choice. Returning to main menu.")


def generate_single_visualization(habits, habit_name, report_year):
    """Generate visualization for a single habit"""
    if habit_name not in habits:
        print(f"Habit '{habit_name}' not found.")
        return

    vis_folder = get_visualization_folder()
    data = habits[habit_name]
    inner = f"""
    <header class="doc-header">
        <h1>Habit year — {report_year}</h1>
        <p class="meta">Single habit report</p>
    </header>
    {build_habit_year_section_html(habits, habit_name, report_year, first=True)}
    """
    html_content = build_visualization_html_document(
        f"Habit Tracker — {habit_name} ({report_year})", inner
    )

    safe_habit_name = re.sub(r"[^\w\s\-]", "", habit_name).strip().replace(" ", "_") or "habit"
    base = f"habit_{safe_habit_name}_{report_year}"
    html_filename = os.path.join(vis_folder, f"{base}_visualization.html")
    pdf_filename = os.path.join(vis_folder, f"{base}_visualization.pdf")

    try:
        write_visualization_files(html_content, html_filename, pdf_filename)
        print(f"Generated visualization for '{habit_name}' ({report_year})")
    except Exception as e:
        print(f"\nError generating visualization for '{habit_name}': {e}")
        if "No wkhtmltopdf executable found" in str(e):
            print("Please install wkhtmltopdf from: https://wkhtmltopdf.org/downloads.html")


def generate_combined_visualization(habits, report_year):
    """One HTML/PDF with every habit (archived labeled)."""
    if not habits:
        return
    vis_folder = get_visualization_folder()
    names = sorted(habits.keys(), key=str.lower)
    sections = [
        """
    <header class="doc-header">
        <h1>Habit year — """ + str(report_year) + """</h1>
        <p class="meta">All habits · annual-style document</p>
    </header>
        """
    ]
    for i, name in enumerate(names):
        sections.append(build_habit_year_section_html(habits, name, report_year, first=(i == 0)))
    inner = "".join(sections)
    html_content = build_visualization_html_document(
        f"Habit Tracker — All habits ({report_year})", inner
    )

    html_filename = os.path.join(vis_folder, f"all_habits_{report_year}_visualization.html")
    pdf_filename = os.path.join(vis_folder, f"all_habits_{report_year}_visualization.pdf")

    try:
        write_visualization_files(html_content, html_filename, pdf_filename)
        print(f"\nCombined report for {len(names)} habit(s), year {report_year}")
    except Exception as e:
        print(f"\nError generating combined visualization: {e}")
        if "No wkhtmltopdf executable found" in str(e):
            print("Please install wkhtmltopdf from: https://wkhtmltopdf.org/downloads.html")


# ======================
# Main Application
# ======================

def main():
    init_terminal_ui()

    # Check wkhtmltopdf installation
    try:
        pdfkit.from_string("<html><body><h1>Test</h1></body></html>", "test.pdf")
        os.remove("test.pdf")
    except Exception as e:
        print("\nWarning: PDF generation might not work properly.")
        print(f"Error: {str(e)}")
        print("Please ensure wkhtmltopdf is installed from: https://wkhtmltopdf.org/downloads.html\n")

    habits = load_habits()
    first_menu = True

    while True:
        print_main_menu(show_header_art=first_menu)
        first_menu = False
        choice = input_main_choice()

        if choice == "1":
            track_habit(habits)
        elif choice == "2":
            view_habits(habits, period="today")
        elif choice == "3":
            view_habits(habits, period="week")
        elif choice == "4":
            view_habits(habits, period="month")
        elif choice == "5":
            generate_visualization(habits)
        elif choice == "6":
            manage_habits(habits)
        elif choice == "7":
            print("Exiting pyhabits.")
            break
        else:
            print("Invalid choice. Please try again.")


if __name__ == "__main__":
    main()
