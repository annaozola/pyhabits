# Compatibility entry point — delegates to main.py
# All application logic has moved to the module files.
from habits_core import *  # noqa: F401,F403 — re-export for test compatibility
from visualization import (  # noqa: F401
    build_month_calendar_html,
    build_habit_year_section_html,
    build_visualization_html_document,
    VISUALIZATION_CSS,
)
from habits_tracking import track_habit  # noqa: F401
from main import main  # noqa: F401

if __name__ == "__main__":
    main()
