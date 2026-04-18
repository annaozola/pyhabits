import sys
import argparse

from habits_core import load_habits, get_current_date
from ui_terminal import (
    init_terminal_ui,
    print_main_menu,
    input_main_choice,
    print_view_habits_submenu,
    input_view_period_choice,
)
from habits_tracking import track_habit, track_habit_cli, undo_habit, undo_last_completion
from habits_viewing import view_habits, view_stats, export_habits
from habits_management import manage_habits
from visualization import generate_visualization


def build_parser():
    parser = argparse.ArgumentParser(
        prog="pyhabits",
        description="Terminal habit tracker",
    )
    sub = parser.add_subparsers(dest="command")

    # track
    p_track = sub.add_parser("track", help="Mark a habit completed")
    p_track.add_argument("habit", help="Habit name (exact, case-insensitive)")
    p_track.add_argument("--date", help="Date to log (YYYY-MM-DD); defaults to today")

    # view
    p_view = sub.add_parser("view", help="View habit completions")
    p_view.add_argument("period", choices=["today", "week", "month"])

    # stats
    p_stats = sub.add_parser("stats", help="Show streak and completion statistics")
    p_stats.add_argument("habit", nargs="?", help="Specific habit name (optional)")

    # undo
    p_undo = sub.add_parser("undo", help="Remove the last completion for a habit")
    p_undo.add_argument("habit", help="Habit name")

    # export
    p_export = sub.add_parser("export", help="Export habit data")
    p_export.add_argument("period", choices=["week", "month"])
    p_export.add_argument("--format", choices=["json", "csv", "md"], default="csv")

    # clean-exports
    p_clean = sub.add_parser("clean-exports", help="Delete old export files")
    p_clean.add_argument("--older-than", type=int, default=30, metavar="DAYS",
                         help="Delete files older than N days (default: 30)")

    return parser


def _run_cli(args, habits):
    """Dispatch non-interactive CLI commands. Returns exit code."""
    from habits_core import find_active_by_casefold, get_current_week, get_current_month

    if args.command == "track":
        name = find_active_by_casefold(habits, args.habit) or args.habit
        ok = track_habit_cli(habits, name, date=args.date)
        return 0 if ok else 1

    elif args.command == "view":
        view_habits(habits, period=args.period)
        return 0

    elif args.command == "stats":
        if args.habit:
            from habits_stats import habit_stats_summary
            name = find_active_by_casefold(habits, args.habit) or args.habit
            if name not in habits:
                print(f"Habit '{args.habit}' not found.")
                return 1
            stats = habit_stats_summary(name, habits[name])
            print(f"\n{name}")
            print(f"  Current streak : {stats['current_streak']} days")
            print(f"  Longest streak : {stats['longest_streak']} days")
            print(f"  Completion rate: {stats['completion_rate'] * 100:.1f}%")
            print(f"  Total logged   : {stats['total_completions']}")
        else:
            view_stats(habits)
        return 0

    elif args.command == "undo":
        name = find_active_by_casefold(habits, args.habit) or args.habit
        if name not in habits:
            print(f"Habit '{args.habit}' not found.")
            return 1
        removed = undo_last_completion(habits, name)
        if removed:
            print(f"Removed completion for '{name}' on {removed}.")
        else:
            print(f"No completions found for '{name}'.")
        return 0

    elif args.command == "export":
        if args.period == "week":
            start, end = get_current_week()
        else:
            start, end = get_current_month()
        # Map --format to numeric choice for export_habits
        fmt_map = {"json": "1", "csv": "2", "md": "3"}
        from unittest.mock import patch
        with patch("builtins.input", return_value=fmt_map[args.format]):
            # export_habits loops until "4" (exit); patch to run once then exit
            inputs = iter([fmt_map[args.format], "4"])
            with patch("builtins.input", side_effect=inputs):
                export_habits(habits, args.period, start, end)
        return 0

    elif args.command == "clean-exports":
        from habits_core import clean_old_exports
        n_files, n_dirs = clean_old_exports(keep_days=args.older_than)
        print(f"Removed {n_files} file(s) and {n_dirs} empty director(ies).")
        return 0

    return 0


def _run_interactive(habits):
    init_terminal_ui()
    first_menu = True

    while True:
        print_main_menu(show_header_art=first_menu)
        first_menu = False
        choice = input_main_choice()

        if choice == "1":
            track_habit(habits)
        elif choice == "2":
            while True:
                print_view_habits_submenu()
                period_choice = input_view_period_choice()
                if period_choice == "1":
                    view_habits(habits, period="today")
                elif period_choice == "2":
                    view_habits(habits, period="week")
                elif period_choice == "3":
                    view_habits(habits, period="month")
                elif period_choice == "4":
                    break
                else:
                    print("  Invalid choice. Please try again.")
        elif choice == "3":
            generate_visualization(habits)
        elif choice == "4":
            manage_habits(habits)
        elif choice == "5":
            view_stats(habits)
        elif choice == "6":
            undo_habit(habits)
        elif choice == "7":
            print("Exiting pyhabits.")
            break
        else:
            print("  Invalid choice. Please try again.")


def main():
    habits = load_habits()

    if len(sys.argv) > 1:
        parser = build_parser()
        args = parser.parse_args()
        if args.command is None:
            parser.print_help()
            sys.exit(0)
        sys.exit(_run_cli(args, habits))
    else:
        _run_interactive(habits)


if __name__ == "__main__":
    main()
