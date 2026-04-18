from datetime import date, timedelta

from habits_core import is_completed


def _truthy_dates(completion: dict) -> list[date]:
    """Return sorted list of date objects where completion value is truthy."""
    result = []
    for d, v in completion.items():
        if is_completed(v):
            try:
                result.append(date.fromisoformat(d))
            except ValueError:
                continue
    result.sort()
    return result


def compute_current_streak(completion: dict) -> int:
    """Consecutive days up to today (inclusive) where completion is truthy."""
    truthy = _truthy_dates(completion)
    if not truthy:
        return 0

    today = date.today()
    streak = 0
    cursor = today
    # Walk backwards; allow today to be absent (not yet logged today)
    truthy_set = set(truthy)

    while cursor in truthy_set:
        streak += 1
        cursor -= timedelta(days=1)

    return streak


def compute_longest_streak(completion: dict) -> int:
    """Longest consecutive run of truthy days in history."""
    truthy = _truthy_dates(completion)
    if not truthy:
        return 0

    best = 1
    current = 1
    for i in range(1, len(truthy)):
        if (truthy[i] - truthy[i - 1]).days == 1:
            current += 1
            best = max(best, current)
        else:
            current = 1

    return best


def compute_completion_rate(completion: dict, start: str = None, end: str = None) -> float:
    """Fraction of days in [start, end] where completion is truthy.

    If start/end are None, the span of recorded completion keys is used.
    Returns 0.0 if there are no days to evaluate.
    """
    if not completion:
        return 0.0

    all_dates = []
    for d in completion:
        try:
            all_dates.append(date.fromisoformat(d))
        except ValueError:
            continue

    if not all_dates:
        return 0.0

    start_d = date.fromisoformat(start) if start else min(all_dates)
    end_d = date.fromisoformat(end) if end else max(all_dates)

    total_days = (end_d - start_d).days + 1
    if total_days <= 0:
        return 0.0

    truthy_set = set(_truthy_dates(completion))
    completed = sum(
        1 for i in range(total_days)
        if (start_d + timedelta(days=i)) in truthy_set
    )
    return completed / total_days


def habit_stats_summary(name: str, data: dict) -> dict:
    """Return stats dict for one habit."""
    completion = data.get("completion", {})
    truthy = _truthy_dates(completion)
    return {
        "name": name,
        "current_streak": compute_current_streak(completion),
        "longest_streak": compute_longest_streak(completion),
        "total_completions": len(truthy),
        "completion_rate": compute_completion_rate(completion),
    }
