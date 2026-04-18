import calendar
import html
import os
import re
import webbrowser
from datetime import datetime

# PDF backend: prefer WeasyPrint (pure Python on Linux/Mac; requires GTK on Windows).
# Falls back to pdfkit (requires wkhtmltopdf binary). If neither works, HTML-only mode.
try:
    from weasyprint import HTML as _WeasyHTML
    _PDF_BACKEND = "weasyprint"
except (ImportError, OSError):
    _WeasyHTML = None
    _PDF_BACKEND = "pdfkit"

if _PDF_BACKEND == "pdfkit":
    try:
        import pdfkit as _pdfkit
    except ImportError:
        _pdfkit = None
        _PDF_BACKEND = "none"

from habits_core import (
    DEFAULT_CATEGORY,
    get_visualization_folder,
    format_habit_label,
    is_completed,
    prompt_report_year,
)

def _load_visualization_css() -> str:
    css_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "visualization.css")
    try:
        with open(css_path, "r", encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""  # Degrade gracefully — HTML will still render without styles


VISUALIZATION_CSS = _load_visualization_css()


def build_month_calendar_html(data, report_year, month):
    _, last = calendar.monthrange(report_year, month)
    month_name = datetime(report_year, month, 1).strftime("%B")
    lines = [
        f'<div class="month">',
        f'<div class="month-name">{html.escape(month_name)} {report_year}</div>',
        '<div class="calendar">',
    ]
    for day in range(1, last + 1):
        date_str = f"{report_year}-{month:02d}-{day:02d}"
        raw_val = data["completion"].get(date_str, False)
        done = is_completed(raw_val)
        cls = "completed" if done else "empty"
        cell_text = str(raw_val) if isinstance(raw_val, (int, float)) and done else str(day)
        lines.append(f'<div class="day {cls}" title="{date_str}">{cell_text}</div>')
    lines.append("</div></div>")
    return "".join(lines)


def build_habit_year_section_html(habits, habit_name, report_year, *, first=False):
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


def _pdfkit_options():
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

    if _PDF_BACKEND == "weasyprint":
        _WeasyHTML(string=html_content).write_pdf(pdf_path)
        print(f"\nHTML: {html_path}")
        print(f"PDF:  {pdf_path} (WeasyPrint)")
    elif _PDF_BACKEND == "pdfkit":
        _pdfkit.from_string(html_content, pdf_path, options=_pdfkit_options())
        print(f"\nHTML: {html_path}")
        print(f"PDF:  {pdf_path} (pdfkit/wkhtmltopdf)")
    else:
        print(f"\nHTML: {html_path}")
        print("PDF:  skipped (no PDF backend available — install weasyprint or wkhtmltopdf)")

    webbrowser.open(f"file://{os.path.abspath(html_path)}")


def generate_visualization(habits):
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
    if habit_name not in habits:
        print(f"Habit '{habit_name}' not found.")
        return

    vis_folder = get_visualization_folder()
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


def generate_combined_visualization(habits, report_year):
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
