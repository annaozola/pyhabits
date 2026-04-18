import sys
import os
from datetime import datetime, timedelta

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pyhabits as ph


class TestNormalizeHabitData:
    def test_empty_dict_gets_all_defaults(self):
        result = ph.normalize_habit_data({})
        assert result["measurement"] is None
        assert result["completion"] == {}
        assert result["archived"] is False
        assert result["category"] == "General"
        assert result["icon"] is None

    def test_non_dict_returns_full_default(self):
        for bad in [None, "string", 42, []]:
            result = ph.normalize_habit_data(bad)
            assert result["measurement"] is None
            assert result["completion"] == {}
            assert result["archived"] is False
            assert result["category"] == "General"
            assert result["icon"] is None

    def test_existing_keys_are_preserved(self):
        data = {"measurement": "30 min", "category": "Health", "archived": True, "icon": "🏃", "completion": {"2025-01-01": True}}
        result = ph.normalize_habit_data(data)
        assert result["measurement"] == "30 min"
        assert result["category"] == "Health"
        assert result["archived"] is True
        assert result["icon"] == "🏃"
        assert result["completion"] == {"2025-01-01": True}

    def test_blank_category_falls_back_to_default(self):
        result = ph.normalize_habit_data({"category": "   "})
        assert result["category"] == "General"

    def test_blank_icon_becomes_none(self):
        result = ph.normalize_habit_data({"icon": "  "})
        assert result["icon"] is None

    def test_missing_measurement_defaults_to_none(self):
        result = ph.normalize_habit_data({"category": "Health"})
        assert result["measurement"] is None

    def test_extra_keys_are_preserved(self):
        result = ph.normalize_habit_data({"custom_key": "value"})
        assert result["custom_key"] == "value"


class TestActiveHabits:
    def test_filters_out_archived(self, sample_habits):
        result = ph.active_habits(sample_habits)
        assert "Old Habit" not in result
        assert "Reading" in result
        assert "Exercise" in result

    def test_empty_habits(self):
        assert ph.active_habits({}) == {}

    def test_all_archived_returns_empty(self):
        habits = {"h": {"archived": True, "completion": {}, "category": "General", "icon": None, "measurement": None}}
        assert ph.active_habits(habits) == {}

    def test_no_archived_key_treated_as_active(self):
        habits = {"h": {"completion": {}, "category": "General", "icon": None, "measurement": None}}
        result = ph.active_habits(habits)
        assert "h" in result


class TestActiveHabitsOrdered:
    def test_sorted_by_category_then_name(self, sample_habits):
        result = ph.active_habits_ordered(sample_habits)
        names = [name for name, _ in result]
        # Health comes before Learning alphabetically
        assert names.index("Exercise") < names.index("Reading")

    def test_archived_excluded(self, sample_habits):
        names = [n for n, _ in ph.active_habits_ordered(sample_habits)]
        assert "Old Habit" not in names

    def test_empty_habits_returns_empty_list(self):
        assert ph.active_habits_ordered({}) == []

    def test_multiple_habits_same_category_sorted_by_name(self):
        habits = {
            "Zebra": {"archived": False, "category": "Health", "completion": {}, "icon": None, "measurement": None},
            "Apple": {"archived": False, "category": "Health", "completion": {}, "icon": None, "measurement": None},
        }
        result = ph.active_habits_ordered(habits)
        names = [n for n, _ in result]
        assert names == ["Apple", "Zebra"]


class TestFormatHabitLabel:
    def test_with_icon(self):
        assert ph.format_habit_label("Reading", {"icon": "📚"}) == "📚 Reading"

    def test_without_icon(self):
        assert ph.format_habit_label("Reading", {"icon": None}) == "Reading"

    def test_empty_icon_string(self):
        assert ph.format_habit_label("Reading", {"icon": ""}) == "Reading"


class TestParseHabitPick:
    def test_valid_number(self):
        assert ph.parse_habit_pick("3", 5) == 2  # 0-based

    def test_trailing_dot(self):
        assert ph.parse_habit_pick("3.", 5) == 2

    def test_lower_bound(self):
        assert ph.parse_habit_pick("1", 5) == 0

    def test_upper_bound(self):
        assert ph.parse_habit_pick("5", 5) == 4

    def test_out_of_range_high(self):
        assert ph.parse_habit_pick("6", 5) is None

    def test_out_of_range_zero(self):
        assert ph.parse_habit_pick("0", 5) is None

    def test_non_numeric(self):
        assert ph.parse_habit_pick("abc", 5) is None

    def test_empty_string(self):
        assert ph.parse_habit_pick("", 5) is None

    def test_single_item_list(self):
        assert ph.parse_habit_pick("1", 1) == 0


class TestGetCurrentWeek:
    def test_start_is_monday(self):
        start, _ = ph.get_current_week()
        d = datetime.strptime(start, "%Y-%m-%d")
        assert d.weekday() == 0  # Monday

    def test_end_is_sunday(self):
        _, end = ph.get_current_week()
        d = datetime.strptime(end, "%Y-%m-%d")
        assert d.weekday() == 6  # Sunday

    def test_span_is_six_days(self):
        start, end = ph.get_current_week()
        s = datetime.strptime(start, "%Y-%m-%d")
        e = datetime.strptime(end, "%Y-%m-%d")
        assert (e - s).days == 6


class TestGetCurrentMonth:
    def test_start_is_first_of_month(self):
        start, _ = ph.get_current_month()
        d = datetime.strptime(start, "%Y-%m-%d")
        assert d.day == 1

    def test_end_is_last_day(self):
        _, end = ph.get_current_month()
        end_d = datetime.strptime(end, "%Y-%m-%d")
        # The day after end should be the first of the next month
        next_day = end_d + timedelta(days=1)
        assert next_day.day == 1

    def test_start_and_end_same_month(self):
        start, end = ph.get_current_month()
        s = datetime.strptime(start, "%Y-%m-%d")
        e = datetime.strptime(end, "%Y-%m-%d")
        assert s.month == e.month
        assert s.year == e.year


class TestMinMaxYears:
    def test_returns_correct_min_max(self, sample_habits):
        mn, mx = ph.min_max_years_from_habits(sample_habits)
        assert mn == 2024
        assert mx == 2026

    def test_empty_habits_returns_current_year(self):
        mn, mx = ph.min_max_years_from_habits({})
        current_year = datetime.now().year
        assert mn == current_year
        assert mx == current_year

    def test_scoped_to_habit_names(self, sample_habits):
        # Only look at Reading (2025 and 2026)
        mn, mx = ph.min_max_years_from_habits(sample_habits, habit_names=["Reading"])
        assert mn == 2025
        assert mx == 2026


class TestSuggestCloseHabitNames:
    def test_finds_close_match(self):
        result = ph.suggest_close_habit_names("Readng", ["Reading", "Exercise"])
        assert "Reading" in result

    def test_exact_match_case_insensitive(self):
        result = ph.suggest_close_habit_names("reading", ["Reading", "Exercise"])
        assert "Reading" in result

    def test_no_match_returns_empty(self):
        result = ph.suggest_close_habit_names("zzzzz", ["Reading", "Exercise"])
        assert result == []

    def test_empty_names_returns_empty(self):
        assert ph.suggest_close_habit_names("Reading", []) == []

    def test_returns_at_most_three(self):
        names = [f"Habit{i}" for i in range(10)]
        result = ph.suggest_close_habit_names("Habit1", names)
        assert len(result) <= 3


class TestIsCompleted:
    def test_true_is_completed(self):
        import pyhabits as ph
        assert ph.is_completed(True) is True

    def test_positive_int_is_completed(self):
        import pyhabits as ph
        assert ph.is_completed(20) is True

    def test_positive_float_is_completed(self):
        import pyhabits as ph
        assert ph.is_completed(3.5) is True

    def test_false_is_not_completed(self):
        import pyhabits as ph
        assert ph.is_completed(False) is False

    def test_zero_is_not_completed(self):
        import pyhabits as ph
        assert ph.is_completed(0) is False

    def test_negative_is_not_completed(self):
        import pyhabits as ph
        assert ph.is_completed(-1) is False

    def test_none_is_not_completed(self):
        import pyhabits as ph
        assert ph.is_completed(None) is False


class TestFindActiveByCasefold:
    def test_finds_case_insensitive(self, sample_habits):
        assert ph.find_active_by_casefold(sample_habits, "reading") == "Reading"
        assert ph.find_active_by_casefold(sample_habits, "EXERCISE") == "Exercise"

    def test_archived_not_found(self, sample_habits):
        assert ph.find_active_by_casefold(sample_habits, "old habit") is None

    def test_nonexistent_returns_none(self, sample_habits):
        assert ph.find_active_by_casefold(sample_habits, "doesnotexist") is None
