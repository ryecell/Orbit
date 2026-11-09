"""
Grade maths for Orbit's grades tracker — pure functions, no database, fully unit-tested.

Everything is stored as raw points and converted to the student's own grading
scale only for display, so switching scales never loses data.

Scales
  "1-5"      1.0 is the best grade, 5.0 fails         (common in the Philippines)
  "5-1"      5.0 is the best grade, 1.0 fails
  "gpa4"     4.0 is the best grade, 0.0 fails
  "percent"  0–100

A conversion table is a list of {"min": percent, "grade": value} rows, highest
`min` first, ending with a row whose min is 0. Schools differ, so users can edit it.
"""
from typing import Dict, List, Optional

SCALES = ("1-5", "5-1", "gpa4", "percent")

_ONE_TO_FIVE = [
    (97, 1.0), (94, 1.25), (91, 1.5), (88, 1.75), (85, 2.0),
    (82, 2.25), (79, 2.5), (76, 2.75), (75, 3.0), (0, 5.0),
]
_GPA4 = [
    (93, 4.0), (90, 3.7), (87, 3.3), (83, 3.0), (80, 2.7),
    (77, 2.3), (73, 2.0), (70, 1.7), (67, 1.3), (65, 1.0), (0, 0.0),
]

DEFAULT_PASSING = {"1-5": 75.0, "5-1": 75.0, "gpa4": 65.0, "percent": 75.0}


def default_table(scale: str) -> Optional[List[Dict[str, float]]]:
    if scale == "1-5":
        rows = _ONE_TO_FIVE
    elif scale == "5-1":
        rows = [(m, round(6.0 - g, 2)) for m, g in _ONE_TO_FIVE]  # mirror: 1.0 -> 5.0, 3.0 -> 3.0, 5.0 -> 1.0
    elif scale == "gpa4":
        rows = _GPA4
    elif scale == "percent":
        return None
    else:
        raise ValueError("Unknown grading scale")
    return [{"min": float(m), "grade": float(g)} for m, g in rows]


def validate_table(rows, scale: str) -> List[Dict[str, float]]:
    """Cleans a user-edited table or raises ValueError with a message safe to show."""
    if scale == "percent":
        return []
    if not isinstance(rows, list) or not (2 <= len(rows) <= 20):
        raise ValueError("The conversion table needs between 2 and 20 rows")
    cleaned = []
    for r in rows:
        try:
            m, g = float(r["min"]), float(r["grade"])
        except (KeyError, TypeError, ValueError):
            raise ValueError("Each table row needs a minimum percent and a grade")
        if not (0 <= m <= 100) or not (0 <= g <= 100):
            raise ValueError("Table values are out of range")
        cleaned.append({"min": m, "grade": g})
    cleaned.sort(key=lambda r: -r["min"])
    mins = [r["min"] for r in cleaned]
    if len(set(mins)) != len(mins):
        raise ValueError("Two rows have the same minimum percent")
    if cleaned[-1]["min"] != 0:
        raise ValueError("The lowest row must start at 0%")
    return cleaned


def percent_to_grade(table, pct: Optional[float], scale: str) -> Optional[float]:
    if pct is None:
        return None
    if scale == "percent" or not table:
        return round(pct, 2)
    for row in table:  # highest min first
        if pct + 1e-9 >= row["min"]:
            return row["grade"]
    return table[-1]["grade"]


def grade_to_percent(table, grade: float, scale: str) -> float:
    """The percent a typed-in grade stands for: the lower bound of the nearest table row."""
    if scale == "percent" or not table:
        return float(grade)
    row = min(table, key=lambda r: abs(r["grade"] - grade))
    return row["min"]


def best_is_low(scale: str) -> bool:
    return scale == "1-5"


def entries_percent(entries) -> Optional[float]:
    """Points earned over points possible (pooled), as a percent."""
    total = sum(e["total"] for e in entries)
    if total <= 0:
        return None
    return sum(e["score"] for e in entries) / total * 100.0


def category_stats(categories, entries):
    """Per-category pooled percent. entries: dicts with score,total,category_id."""
    stats = []
    for c in categories:
        mine = [e for e in entries if e.get("category_id") == c["id"]]
        stats.append({**c, "percent": entries_percent(mine), "count": len(mine)})
    return stats


def current_percent(categories, entries) -> Optional[float]:
    """
    No weighted categories  -> all entries pooled together.
    Weighted categories     -> weighted average of the categories that have scores so far
                               (weights are re-normalised over what's been graded).
                               Entries without a category are ignored in that case.
    """
    weighted = [c for c in categories if (c.get("weight") or 0) > 0]
    if not weighted:
        return entries_percent(entries)
    num = den = 0.0
    for s in category_stats(weighted, entries):
        if s["percent"] is not None:
            num += s["weight"] * s["percent"]
            den += s["weight"]
    return num / den if den else None


def needed_for_target(categories, entries, target_percent: float, category_id: Optional[str] = None, points: Optional[float] = None):
    """
    "What do I need on the rest?"  Returns {"needed_percent", "possible", "secured"} or None if it can't be worked out.

    Weighted subject: pass category_id of the category still to come (e.g. the final exam).
        final = (sum(w_i * pct_i over graded categories) + w_c * x) / (sum of those weights + w_c)
    Unweighted subject: pass `points` = total points of the next assessment.
        x = (target * (total_so_far + points) - score_so_far) / points
    """
    weighted = [c for c in categories if (c.get("weight") or 0) > 0]
    if weighted and category_id:
        target_cat = next((c for c in weighted if c["id"] == category_id), None)
        if not target_cat:
            return None
        others = [s for s in category_stats([c for c in weighted if c["id"] != category_id], entries) if s["percent"] is not None]
        g = sum(s["weight"] * s["percent"] for s in others)
        w_all = sum(s["weight"] for s in others) + target_cat["weight"]
        # If the target category already has scores, treat the new work as pooled into it
        # by solving for its overall percent — an approximation that's clear to the user.
        x = (target_percent * w_all - g) / target_cat["weight"]
    elif not weighted and points:
        if points <= 0:
            return None
        score = sum(e["score"] for e in entries)
        total = sum(e["total"] for e in entries)
        x = (target_percent / 100.0 * (total + points) - score) / points * 100.0
    else:
        return None
    return {"needed_percent": max(x, 0.0), "possible": x <= 100.0 + 1e-9, "secured": x <= 0.0}


def overall(subjects, scale: str, table) -> Dict[str, Optional[float]]:
    """
    Units-weighted average across subjects that have a grade. For table scales the
    average is taken over the grade values themselves (a GWA); for percent, over percents.
    subjects: dicts with percent (or None) and units.
    """
    graded = [s for s in subjects if s.get("percent") is not None and (s.get("units") or 0) > 0]
    if not graded:
        return {"percent": None, "grade": None}
    units = sum(s["units"] for s in graded)
    pct = sum(s["percent"] * s["units"] for s in graded) / units
    if scale == "percent" or not table:
        return {"percent": pct, "grade": round(pct, 2)}
    gwa = sum(percent_to_grade(table, s["percent"], scale) * s["units"] for s in graded) / units
    return {"percent": pct, "grade": gwa}
