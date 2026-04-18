from datetime import datetime, timedelta

from habits_core import (
    DEFAULT_CATEGORY,
    active_habits,
    active_habits_ordered,
    find_active_by_casefold,
    format_habit_label,
    get_current_date,
    get_current_day,
    is_completed,
    parse_habit_pick,
    resolve_new_habit_flow,
    save_habits,
    suggest_close_habit_names,
)
from ui_terminal import print_section_title, style_label


def _print_habits_list(habits) -> list:
    """Print active habits grouped by category with index numbers. Returns ordered name list."""
    ordered = active_habits_ordered(habits)
    if not ordered:
        print("\n  No active habits.")
        return []

    print_section_title("Your habits")
    idx = 1
    current_cat = None
    names_in_order = []
    for name, data in ordered:
        cat = data.get("category") or DEFAULT_CATEGORY
        if cat != current_cat:
            current_cat = cat
            print(f"\n  {style_label(cat)}")
        label = format_habit_label(name, data)
        measurement = data.get("measurement")
        if measurement:
            print(f"    {idx}. {label}  ({measurement})")
        else:
            print(f"    {idx}. {label}")
        names_in_order.append(name)
        idx += 1
    return names_in_order


def _prompt_tracking_date() -> str:
    """Ask the user which date to log for. Returns a YYYY-MM-DD string."""
    today = datetime.now()
    today_str = today.strftime("%Y-%m-%d")
    yesterday_str = (today - timedelta(days=1)).strftime("%Y-%m-%d")

    print_section_title("Log for:")
    print(f"    1. Today ({today_str})")
    print(f"    2. Yesterday ({yesterday_str})")
    print("    3. Enter a specific date")
    choice = input("Choose (1-3) [1]: ").strip()

    if choice == "2":
        return yesterday_str
    if choice == "3":
        raw = input("Enter date (YYYY-MM-DD): ").strip()
        try:
            datetime.strptime(raw, "%Y-%m-%d")
            return raw
        except ValueError:
            print(f"Invalid date '{raw}'; using today.")
            return today_str
    return today_str


def track_habit(habits):
    names_in_order = _print_habits_list(habits)
    n = len(names_in_order)

    raw_input = input("\nEnter habit number, habit name, or a new name to add: ").strip()
    if not raw_input:
        print("No input.")
        return

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

    target_date = _prompt_tracking_date()
    today_date = get_current_date()
    today_day = get_current_day()

    if is_completed(habits[habit_name]["completion"].get(target_date, False)):
        already_label = "today" if target_date == today_date else target_date
        print(f"'{habit_name}' already tracked for {already_label}.")
        return

    # Prompt for a quantity if the habit has a measurement
    completion_value = True
    measurement = habits[habit_name].get("measurement")
    if measurement:
        raw_qty = input(f"Log amount for '{measurement}' (or Enter to skip): ").strip()
        if raw_qty:
            try:
                completion_value = float(raw_qty) if "." in raw_qty else int(raw_qty)
            except ValueError:
                print(f"'{raw_qty}' is not a number; logging as a simple check-in.")

    habits[habit_name]["completion"][target_date] = completion_value
    date_label = today_day if target_date == today_date else target_date
    qty_label = f" ({completion_value} {measurement})" if isinstance(completion_value, (int, float)) and measurement else ""
    print(f"'{habit_name}' marked as completed for {date_label}, {target_date}.{qty_label}")
    save_habits(habits)


def track_habit_cli(habits, habit_name, date=None):
    """Non-interactive tracking for CLI use. Returns True on success, False on error."""
    target_date = date or get_current_date()

    if habit_name not in habits:
        print(f"Error: habit '{habit_name}' not found. Use the interactive menu to create it.")
        return False

    if habits[habit_name].get("archived"):
        print(f"Error: '{habit_name}' is archived. Unarchive it first via Manage habits.")
        return False

    if is_completed(habits[habit_name]["completion"].get(target_date, False)):
        print(f"'{habit_name}' already tracked for {target_date}.")
        return False

    habits[habit_name]["completion"][target_date] = True
    save_habits(habits)
    print(f"'{habit_name}' marked as completed for {target_date}.")
    return True


def undo_last_completion(habits, habit_name):
    """Remove the most recent truthy completion. Returns the removed date or None."""
    if habit_name not in habits:
        return None
    completions = habits[habit_name]["completion"]
    completed_dates = [d for d, v in completions.items() if v]
    if not completed_dates:
        return None
    last = max(completed_dates)
    del completions[last]
    save_habits(habits)
    return last


def undo_habit(habits):
    """Interactive undo: list habits, prompt selection, remove last completion."""
    names_in_order = _print_habits_list(habits)
    if not names_in_order:
        return

    raw = input("\nEnter habit number or name to undo last entry: ").strip()
    if not raw:
        print("Cancelled.")
        return

    habit_name = None
    pick_idx = parse_habit_pick(raw, len(names_in_order))
    if pick_idx is not None:
        habit_name = names_in_order[pick_idx]
    else:
        habit_name = find_active_by_casefold(habits, raw) or (raw if raw in habits else None)

    if habit_name is None:
        print(f"Habit '{raw}' not found.")
        return

    removed_date = undo_last_completion(habits, habit_name)
    if removed_date:
        print(f"Removed completion for '{habit_name}' on {removed_date}.")
    else:
        print(f"No completions found for '{habit_name}'.")
