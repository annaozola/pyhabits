from habits_core import (
    DEFAULT_CATEGORY,
    active_habits,
    format_habit_label,
    save_habits,
)
from habits_config import edit_config_interactive
from ui_terminal import print_section_title, style_label


def manage_habits(habits):
    while True:
        print_section_title("Manage habits")
        print("    1. Archive a habit")
        print("    2. Unarchive a habit")
        print("    3. Edit category / icon")
        print("    4. List archived habits")
        print("    5. Clean up old exports")
        print("    6. Configure settings")
        print("    7. Back")
        c = input("  Choose (1–7): ").strip()

        if c == "7":
            return
        if c == "5":
            from habits_core import clean_old_exports
            days_raw = input("Delete exports older than how many days? [30]: ").strip()
            try:
                days = int(days_raw) if days_raw else 30
            except ValueError:
                days = 30
            n_files, n_dirs = clean_old_exports(keep_days=days)
            print(f"Removed {n_files} file(s) and {n_dirs} empty director(ies).")
            continue
        if c == "6":
            edit_config_interactive()
            continue
        if c == "4":
            archived = [n for n, d in habits.items() if d.get("archived")]
            if not archived:
                print("\n  No archived habits.")
            else:
                print_section_title("Archived habits")
                for n in sorted(archived, key=str.lower):
                    print(f"    - {format_habit_label(n, habits[n])}")
            continue
        if c == "1":
            names = [n for n, d in habits.items() if not d.get("archived")]
            if not names:
                print("\n  No active habits to archive.")
                continue
            print_section_title("Active habits")
            for i, n in enumerate(sorted(names, key=str.lower), 1):
                print(f"    {i}. {format_habit_label(n, habits[n])}")
            raw = input("  Enter number to archive (or blank to cancel): ").strip()
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
                print("\n  No archived habits.")
                continue
            print_section_title("Archived habits")
            for i, n in enumerate(sorted(archived, key=str.lower), 1):
                print(f"    {i}. {format_habit_label(n, habits[n])}")
            raw = input("  Enter number to unarchive (or blank to cancel): ").strip()
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
                print("\n  No habits.")
                continue
            all_names = sorted(habits.keys(), key=str.lower)
            print_section_title("All habits")
            for i, n in enumerate(all_names, 1):
                arch = f"  {style_label('[archived]')}" if habits[n].get("archived") else ""
                print(f"    {i}. {format_habit_label(n, habits[n])}{arch}")
            raw = input("  Enter number to edit (or blank to cancel): ").strip()
            if not raw:
                continue
            try:
                pick = int(raw) - 1
                sel = all_names[pick]
            except (ValueError, IndexError):
                print("Invalid selection.")
                continue
            data = habits[sel]
            print(f"\n  Category : {style_label(data.get('category', DEFAULT_CATEGORY))}")
            print(f"  Icon     : {data.get('icon') or '(none)'}")
            cat_raw = input(f"  New category [{data.get('category', DEFAULT_CATEGORY)}]: ").strip()
            if cat_raw:
                data["category"] = cat_raw
            icon_raw = input("  New icon (Enter to keep current; 'clear' to remove): ").strip()
            if icon_raw.lower() == "clear":
                data["icon"] = None
            elif icon_raw:
                data["icon"] = icon_raw
            save_habits(habits)
            print("  Saved.")
            continue
        print("  Invalid choice.")
