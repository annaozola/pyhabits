import sys
import os
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from habits_stats import (
    compute_current_streak,
    compute_longest_streak,
    compute_completion_rate,
    habit_stats_summary,
)


def _dates_range(start: str, end: str) -> dict:
    """Build a completion dict with True for every day from start to end inclusive."""
    s = date.fromisoformat(start)
    e = date.fromisoformat(end)
    result = {}
    d = s
    while d <= e:
        result[d.isoformat()] = True
        d += timedelta(days=1)
    return result


class TestComputeCurrentStreak:
    def test_empty_returns_zero(self):
        assert compute_current_streak({}) == 0

    def test_streak_of_one_today(self):
        today = date.today().isoformat()
        assert compute_current_streak({today: True}) == 1

    def test_streak_broken_by_gap(self):
        # yesterday and the day before — but NOT today
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        day_before = (date.today() - timedelta(days=2)).isoformat()
        completion = {yesterday: True, day_before: True}
        # Streak is 0 because today is not completed
        assert compute_current_streak(completion) == 0

    def test_consecutive_days_including_today(self):
        today = date.today()
        completion = {
            today.isoformat(): True,
            (today - timedelta(days=1)).isoformat(): True,
            (today - timedelta(days=2)).isoformat(): True,
        }
        assert compute_current_streak(completion) == 3

    def test_false_values_not_counted(self):
        today = date.today().isoformat()
        assert compute_current_streak({today: False}) == 0

    def test_gap_in_middle_breaks_streak(self):
        today = date.today()
        completion = {
            today.isoformat(): True,
            (today - timedelta(days=1)).isoformat(): False,  # gap
            (today - timedelta(days=2)).isoformat(): True,
        }
        assert compute_current_streak(completion) == 1


class TestComputeLongestStreak:
    def test_empty_returns_zero(self):
        assert compute_longest_streak({}) == 0

    def test_single_day(self):
        assert compute_longest_streak({"2025-01-01": True}) == 1

    def test_three_consecutive_days(self):
        c = _dates_range("2025-01-01", "2025-01-03")
        assert compute_longest_streak(c) == 3

    def test_longest_run_among_multiple_runs(self):
        c = _dates_range("2025-01-01", "2025-01-03")  # streak of 3
        c.update(_dates_range("2025-01-10", "2025-01-15"))  # streak of 6
        assert compute_longest_streak(c) == 6

    def test_gap_resets_streak(self):
        c = {
            "2025-01-01": True,
            "2025-01-02": True,
            "2025-01-04": True,  # gap on 3rd
            "2025-01-05": True,
        }
        assert compute_longest_streak(c) == 2

    def test_false_values_ignored(self):
        c = {"2025-01-01": True, "2025-01-02": False, "2025-01-03": True}
        assert compute_longest_streak(c) == 1


class TestComputeCompletionRate:
    def test_empty_returns_zero(self):
        assert compute_completion_rate({}) == 0.0

    def test_all_completed(self):
        c = _dates_range("2025-01-01", "2025-01-10")
        assert compute_completion_rate(c) == 1.0

    def test_half_completed(self):
        c = {}
        for i in range(10):
            d = date(2025, 1, i + 1).isoformat()
            c[d] = (i % 2 == 0)  # 5 out of 10
        rate = compute_completion_rate(c)
        assert abs(rate - 0.5) < 0.01

    def test_scoped_to_date_range(self):
        c = _dates_range("2025-01-01", "2025-01-10")
        # Only look at Jan 1–5 (all completed)
        rate = compute_completion_rate(c, start="2025-01-01", end="2025-01-05")
        assert rate == 1.0

    def test_false_values_not_counted(self):
        c = {"2025-01-01": True, "2025-01-02": False}
        rate = compute_completion_rate(c)
        assert abs(rate - 0.5) < 0.01


class TestHabitStatsSummary:
    def test_returns_all_keys(self):
        data = {"completion": {"2025-01-01": True}, "category": "Health", "icon": None, "measurement": None, "archived": False}
        stats = habit_stats_summary("Exercise", data)
        assert "current_streak" in stats
        assert "longest_streak" in stats
        assert "total_completions" in stats
        assert "completion_rate" in stats

    def test_total_completions_count(self):
        c = _dates_range("2025-01-01", "2025-01-05")
        data = {"completion": c, "category": "Health", "icon": None, "measurement": None, "archived": False}
        stats = habit_stats_summary("Exercise", data)
        assert stats["total_completions"] == 5

    def test_empty_completion(self):
        data = {"completion": {}, "category": "Health", "icon": None, "measurement": None, "archived": False}
        stats = habit_stats_summary("Exercise", data)
        assert stats["current_streak"] == 0
        assert stats["longest_streak"] == 0
        assert stats["total_completions"] == 0
        assert stats["completion_rate"] == 0.0
