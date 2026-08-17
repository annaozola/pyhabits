# Antigravity AI Project Instructions for pyhabits

## CRITICAL: User Data Protection

The `user/` folder contains the user's personal habit tracking data, accumulated over months of effort. It is **never** backed up to GitHub (it is gitignored). If it is overwritten or deleted, that data is gone permanently.

### Rules — read and follow these for every interaction:

1. **NEVER modify the user folder at all.** Do not delete, overwrite, or modify any file inside `user/` (especially `habits.json`). This rule is absolute to prevent accidental data loss.
2. **Only do exactly what is asked:** Do not do anything extra or outside the scope of the user's direct request unless you have asked for and received explicit confirmation from the user for that specific addition or change.
3. **Tests must never touch the live `user/` folder.** Every test that exercises file I/O must use either:
   - `unittest.mock.patch` to mock `save_habits`, `load_habits`, and any other file-writing function, OR
   - A `tmp_path` / `tempfile` temporary directory that is cleaned up after the test.
   - Patching at the correct import location matters: patch where the function is *used*, not where it is *defined* (e.g., `habits_tracking.save_habits`, not `habits_core.save_habits`).

## Project Overview

pyhabits is a terminal-based habit tracker.
- **Tech Stack**: Python 3.8+, pyfiglet (terminal UI), WeasyPrint (PDF generation), pytest.

**Module layout:**
- `habits_core.py` — data layer (load/save, date helpers, fuzzy matching)
- `ui_terminal.py` — ANSI terminal UI
- `habits_tracking.py` — tracking logic (`track_habit`, `undo_habit`)
- `habits_viewing.py` — view/export (today/week/month, JSON/CSV/Markdown)
- `habits_management.py` — archive/unarchive/edit
- `habits_stats.py` — streak and completion statistics (pure functions)
- `visualization.py` — HTML/PDF annual calendar reports
- `habits_config.py` — user config (`user/config.json`)
- `brand.py` — brand colour constants
- `main.py` — argparse CLI + interactive menu loop
- `pyhabits.py` — compatibility shim (entry point)

**Run tests:** `pytest tests/ -v`
