import json
import csv
import os
import unicodedata
from datetime import datetime, timedelta

from habits_core import (
    DEFAULT_CATEGORY,
    DAYS_OF_WEEK,
    EXPORTS_FOLDER,
    active_habits,
    active_habits_ordered,
    ensure_exports_folder_exists,
    format_habit_label,
    get_current_date,
    get_current_day,
    get_current_month,
    get_current_week,
    is_completed,
)
from ui_terminal import _habit_done_status_mark, print_section_title, style_label


def _display_width(s: str) -> int:
    """Terminal display columns occupied by s (wide chars like emoji count as 2)."""
    return sum(2 if unicodedata.east_asian_width(c) in ("W", "F") else 1 for c in s)


def _ljust_display(s: str, width: int) -> str:
    """Left-justify s to `width` display columns, accounting for wide characters."""
    return s + " " * max(0, width - _display_width(s))


def view_habits(habits, period="today"):
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
        print_section_title(f"Habits for {today_day}, {today_date}")
        for habit, data in active_habits_ordered(habits):
            raw_val = data["completion"].get(today_date, False)
            completed = is_completed(raw_val)
            mark = _habit_done_status_mark(completed)
            label = format_habit_label(habit, data)
            measurement = data.get("measurement")
            if measurement and isinstance(raw_val, (int, float)):
                print(f"- {mark}  {label}: {raw_val} / {measurement}")
            elif measurement:
                print(f"- {mark}  {label} (Measurement: {measurement})")
            else:
                print(f"- {mark}  {label}")
    elif period == "week":
        print_section_title(f"Habits for the week {start_of_week} to {end_of_week}")
        for day in DAYS_OF_WEEK:
            date = (week_start_dt + timedelta(days=DAYS_OF_WEEK.index(day))).strftime("%Y-%m-%d")
            print(f"\n{day}, {date}:")
            for habit, data in active_habits_ordered(habits):
                raw_val = data["completion"].get(date, False)
                completed = is_completed(raw_val)
                mark = _habit_done_status_mark(completed)
                label = format_habit_label(habit, data)
                measurement = data.get("measurement")
                if measurement and isinstance(raw_val, (int, float)):
                    print(f"- {mark}  {label}: {raw_val} / {measurement}")
                elif measurement:
                    print(f"- {mark}  {label} (Measurement: {measurement})")
                else:
                    print(f"- {mark}  {label}")
    elif period == "month":
        print_section_title(f"Habits for the month {start_of_month} to {end_of_month}")
        current_date = datetime.strptime(start_of_month, "%Y-%m-%d")
        end_m = datetime.strptime(end_of_month, "%Y-%m-%d")

        while current_date <= end_m:
            date_str = current_date.strftime("%Y-%m-%d")
            day_str = current_date.strftime("%A")
            print(f"\n{day_str}, {date_str}:")
            for habit, data in active_habits_ordered(habits):
                raw_val = data["completion"].get(date_str, False)
                completed = is_completed(raw_val)
                mark = _habit_done_status_mark(completed)
                label = format_habit_label(habit, data)
                measurement = data.get("measurement")
                if measurement and isinstance(raw_val, (int, float)):
                    print(f"- {mark}  {label}: {raw_val} / {measurement}")
                elif measurement:
                    print(f"- {mark}  {label} (Measurement: {measurement})")
                else:
                    print(f"- {mark}  {label}")
            current_date += timedelta(days=1)

    if period in ["week", "month"]:
        export_habits(
            habits, period,
            start_of_week if period == "week" else start_of_month,
            end_of_week if period == "week" else end_of_month,
        )


def export_habits(habits, period, start_date, end_date):
    ensure_exports_folder_exists()
    while True:
        print_section_title("Export options")
        print("    1. JSON")
        print("    2. CSV")
        print("    3. Markdown")
        print("    4. Skip")
        choice = input("  Choose (1–4): ").strip()

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
                                if is_completed(habits[h]["completion"].get(d, False))
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


def view_stats(habits):
    """Print streak and completion statistics for all active habits."""
    from habits_stats import habit_stats_summary

    ordered = [(name, data) for name, data in habits.items() if not data.get("archived")]
    if not ordered:
        print("No active habits.")
        return

    ordered.sort(key=lambda x: (x[1].get("category") or DEFAULT_CATEGORY, x[0].lower()))

    col = 30
    print_section_title("Habit Statistics")
    print(f"  {'Habit':<{col}} {'Streak':>6} {'Longest':>7} {'Rate':>6} {'Total':>6}")
    print("  " + "─" * (col + 28))
    for name, data in ordered:
        stats = habit_stats_summary(name, data)
        rate_pct = f"{stats['completion_rate'] * 100:.0f}%"
        icon = data.get("icon") or ""
        name_display = f"{icon} {name}" if icon else name
        print(
            f"  {_ljust_display(name_display, col)} {stats['current_streak']:>6}"
            f" {stats['longest_streak']:>7} {rate_pct:>6} {stats['total_completions']:>6}"
        )
