import sys
from unittest.mock import MagicMock

# Mock both PDF backends so imports don't fail in test environments
sys.modules.setdefault("pdfkit", MagicMock())
sys.modules.setdefault("weasyprint", MagicMock())

import pytest


@pytest.fixture
def sample_habits():
    """A representative habits dict covering active, measurement, and archived cases."""
    return {
        "Reading": {
            "measurement": "15 pages",
            "completion": {
                "2025-01-10": True,
                "2025-01-11": True,
                "2025-01-12": False,
                "2026-04-16": True,
                "2026-04-17": True,
            },
            "category": "Learning",
            "icon": "📚",
            "archived": False,
        },
        "Exercise": {
            "measurement": None,
            "completion": {
                "2025-03-01": True,
                "2025-03-02": True,
                "2025-03-03": True,
                "2026-04-17": True,
            },
            "category": "Health",
            "icon": "🏃",
            "archived": False,
        },
        "Old Habit": {
            "measurement": None,
            "completion": {
                "2024-06-01": True,
            },
            "category": "General",
            "icon": None,
            "archived": True,
        },
    }
