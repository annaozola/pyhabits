import sys
import os
from unittest.mock import patch, MagicMock
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pyhabits as ph


def _make_habits():
    return {
        "Reading": {
            "measurement": "15 pages",
            "completion": {},
            "category": "Learning",
            "icon": "📚",
            "archived": False,
        },
        "Exercise": {
            "measurement": None,
            "completion": {},
            "category": "Health",
            "icon": None,
            "archived": False,
        },
    }


class TestIdempotencyGuard:
    """track_habit should not double-mark a habit already completed today."""

    def test_already_tracked_exits_early(self):
        habits = _make_habits()
        today = ph.get_current_date()
        habits["Reading"]["completion"][today] = True

        # Input: select habit by number "1" (Reading is first alphabetically by category)
        # The function should detect it's already tracked and print a message, not call save_habits
        # "Reading" to select habit, then "1" for today's date
        with patch("habits_tracking.save_habits") as mock_save, \
             patch("builtins.input", side_effect=["Reading", "1"]), \
             patch("builtins.print"):
            ph.track_habit(habits)
            mock_save.assert_not_called()


class TestNewHabitCreation:
    """Typing a brand-new name should create the habit via resolve_new_habit_flow."""

    def test_creates_new_habit(self):
        habits = _make_habits()
        new_name = "Meditation"
        # inputs: habit name, resolve_new_habit_flow (measurement, category, icon), then date prompt (Enter=today)
        inputs = iter([new_name, "", "", "", ""])
        with patch("habits_tracking.save_habits") as mock_save, \
             patch("builtins.input", side_effect=inputs), \
             patch("builtins.print"):
            ph.track_habit(habits)

        assert new_name in habits
        assert mock_save.called


class TestPickByNumber:
    """Entering a number should resolve to the corresponding habit."""

    def test_pick_by_number_marks_completion(self):
        habits = _make_habits()
        today = ph.get_current_date()

        # active_habits_ordered returns Exercise (Health) before Reading (Learning)
        ordered = ph.active_habits_ordered(habits)
        first_name = ordered[0][0]

        # "1" to select first habit, then "" for today's date (Enter = default)
        with patch("habits_tracking.save_habits"), \
             patch("builtins.input", side_effect=["1", ""]), \
             patch("builtins.print"):
            ph.track_habit(habits)

        assert habits[first_name]["completion"].get(today) is True


class TestArchivedHabitBlocked:
    """Typing an archived habit name should not mark it or save."""

    def test_archived_habit_not_tracked(self):
        habits = _make_habits()
        habits["OldHabit"] = {
            "measurement": None,
            "completion": {},
            "category": "General",
            "icon": None,
            "archived": True,
        }
        with patch("habits_tracking.save_habits") as mock_save, \
             patch("builtins.input", side_effect=["OldHabit", "1"]), \
             patch("builtins.print"):
            ph.track_habit(habits)
        mock_save.assert_not_called()
