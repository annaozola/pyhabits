import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pyhabits as ph


def _make_habit_data(completions=None):
    return {
        "measurement": "15 pages",
        "completion": completions or {},
        "category": "Learning",
        "icon": "📚",
        "archived": False,
    }


class TestBuildMonthCalendarHtml:
    def test_completed_date_has_completed_class(self):
        data = _make_habit_data({"2025-01-15": True})
        html = ph.build_month_calendar_html(data, 2025, 1)
        assert 'class="day completed"' in html

    def test_uncompleted_date_has_empty_class(self):
        data = _make_habit_data({})
        html = ph.build_month_calendar_html(data, 2025, 1)
        assert 'class="day empty"' in html

    def test_month_name_appears_in_output(self):
        data = _make_habit_data({})
        html = ph.build_month_calendar_html(data, 2025, 6)
        assert "June" in html

    def test_all_days_rendered(self):
        data = _make_habit_data({})
        html = ph.build_month_calendar_html(data, 2025, 1)
        # January has 31 days; each gets a <div class="day ...">
        assert html.count('class="day ') == 31

    def test_false_completion_renders_as_empty(self):
        data = _make_habit_data({"2025-01-01": False})
        html = ph.build_month_calendar_html(data, 2025, 1)
        # day 1 should be empty, not completed
        assert 'title="2025-01-01">1</div>' in html
        assert 'class="day empty" title="2025-01-01"' in html


class TestBuildHabitYearSectionHtml:
    def test_habit_name_in_output(self):
        habits = {"Reading": _make_habit_data()}
        html = ph.build_habit_year_section_html(habits, "Reading", 2025)
        assert "Reading" in html

    def test_category_in_output(self):
        habits = {"Reading": _make_habit_data()}
        html = ph.build_habit_year_section_html(habits, "Reading", 2025)
        assert "Learning" in html

    def test_measurement_in_output(self):
        habits = {"Reading": _make_habit_data()}
        html = ph.build_habit_year_section_html(habits, "Reading", 2025)
        assert "15 pages" in html

    def test_twelve_months_rendered(self):
        habits = {"Reading": _make_habit_data()}
        html = ph.build_habit_year_section_html(habits, "Reading", 2025)
        assert html.count('class="month"') == 12

    def test_first_flag_adds_first_class(self):
        habits = {"Reading": _make_habit_data()}
        html_first = ph.build_habit_year_section_html(habits, "Reading", 2025, first=True)
        html_normal = ph.build_habit_year_section_html(habits, "Reading", 2025, first=False)
        assert 'class="habit-section first"' in html_first
        assert 'class="habit-section first"' not in html_normal

    def test_archived_label_shown(self):
        data = _make_habit_data()
        data["archived"] = True
        habits = {"Reading": data}
        html = ph.build_habit_year_section_html(habits, "Reading", 2025)
        assert "archived" in html


class TestBuildVisualizationHtmlDocument:
    def test_doctype_present(self):
        doc = ph.build_visualization_html_document("My Title", "<p>body</p>")
        assert "<!DOCTYPE html>" in doc

    def test_title_injected(self):
        doc = ph.build_visualization_html_document("My Habits 2025", "<p>body</p>")
        assert "My Habits 2025" in doc

    def test_body_injected(self):
        doc = ph.build_visualization_html_document("Title", "<p>custom body</p>")
        assert "<p>custom body</p>" in doc

    def test_css_embedded(self):
        doc = ph.build_visualization_html_document("Title", "")
        assert "<style>" in doc

    def test_html_lang_en(self):
        doc = ph.build_visualization_html_document("Title", "")
        assert 'lang="en"' in doc

    def test_title_escaped(self):
        doc = ph.build_visualization_html_document("<script>", "")
        assert "<script>" not in doc.split("<title>")[1].split("</title>")[0]
