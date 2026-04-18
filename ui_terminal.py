import sys
from datetime import datetime

from brand import BRAND_BANNER_BG, BRAND_DONE_GREEN, BRAND_MENU_BG, BRAND_PRIMARY
from habits_core import DEFAULT_CATEGORY


class _Term:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    WHITE = "\033[97m"


_BRAND_PRIMARY = BRAND_PRIMARY
_BRAND_BANNER_BG = BRAND_BANNER_BG
_BRAND_MENU_BG = BRAND_MENU_BG


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
_BRAND_DONE_GREEN = BRAND_DONE_GREEN


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


def _render_logo() -> list:
    try:
        import pyfiglet

        art = pyfiglet.figlet_format("pyhabits", font="doom")
    except Exception:
        return ["  pyhabits"]
    lines = art.rstrip("\n").split("\n")
    if not _STYLE_OK:
        return ["  " + line for line in lines]
    color = _tc_fg(_BRAND_PRIMARY)
    return ["  " + color + line + _Term.RESET for line in lines]


def _today_menu_subtitle() -> str:
    d = datetime.now()
    return f"{d.strftime('%A')}, {d.day} {d.strftime('%B')}"


def _subtitle_seq():
    return _tc_fg(_BRAND_SUBTITLE_RGB)


def _habit_done_status_mark(completed: bool) -> str:
    if not _STYLE_OK:
        return "✓" if completed else "✗"
    if completed:
        return _s(_tc_fg(_BRAND_DONE_GREEN), "✓")
    return _s(_tc_fg(_BRAND_SUBTITLE_RGB), "✗")


def print_main_menu(*, show_header_art: bool = True, extra_items: list = None):
    """Framed main menu. Pass extra_items as list of (key, label) to extend defaults."""
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
        rows.extend(_render_logo())
        rows.append("")
        sub_text = f"  terminal habit tracker  · {_today_menu_subtitle()}"
        rows.append("  " + _s(sub, sub_text))
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
        ("1", "Track a habit"),
        ("2", "View habits"),
        ("3", "Generate visualization (HTML/PDF)"),
        ("4", "Manage habits"),
        ("5", "View statistics"),
        ("6", "Undo last habit entry"),
        ("7", "Exit"),
    ]
    if extra_items:
        menu_items = menu_items + extra_items

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


def print_section_title(text: str) -> None:
    """Styled section heading in brand red, left-aligned with content."""
    print("\n  " + _s(_subtitle_seq(), text))


def style_label(text: str) -> str:
    """Return text styled in brand red (for category labels, sub-headers)."""
    return _s(_subtitle_seq(), text)


def print_view_habits_submenu() -> None:
    sub = _subtitle_seq()
    accent = _tc_fg(_BRAND_MENU_ACCENT_RGB)
    num_sty = _tc_fg(_BRAND_PRIMARY) + _Term.BOLD
    print("")
    print("  " + _s(sub, "View habits — choose a period"))
    print("")
    for num, label in [("1", "Today"), ("2", "This week"), ("3", "This month"), ("4", "Back")]:
        left = _s(num_sty, f" {num} ")
        mid = _s(accent, "·")
        rest = _s(_Term.WHITE, f" {label}")
        print("    " + left + mid + rest)
    print("")


def input_view_period_choice() -> str:
    prompt = (
        "  "
        + _s(_tc_fg(_BRAND_PRIMARY), "▸")
        + " "
        + _s(_Term.WHITE + _Term.BOLD, "Choose")
        + _s(_tc_fg(_BRAND_MENU_ACCENT_RGB), " — type 1–4, then Enter: ")
    )
    return input(prompt).strip()


def input_main_choice() -> str:
    prompt = (
        "\n  "
        + _s(_tc_fg(_BRAND_PRIMARY), "▸")
        + " "
        + _s(_Term.WHITE + _Term.BOLD, "Choose")
        + _s(_tc_fg(_BRAND_MENU_ACCENT_RGB), " — type 1–7, then Enter: ")
    )
    return input(prompt).strip()
