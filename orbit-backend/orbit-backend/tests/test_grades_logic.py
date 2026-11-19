import pytest

import grades as g

T15 = g.default_table("1-5")


def test_default_tables():
    assert g.default_table("percent") is None
    t = g.default_table("5-1")
    assert t[0] == {"min": 97.0, "grade": 5.0} and t[-1] == {"min": 0.0, "grade": 1.0}
    assert g.default_table("gpa4")[0]["grade"] == 4.0
    with pytest.raises(ValueError):
        g.default_table("nope")


def test_percent_to_grade_and_back():
    assert g.percent_to_grade(T15, 98, "1-5") == 1.0
    assert g.percent_to_grade(T15, 82, "1-5") == 2.25
    assert g.percent_to_grade(T15, 81.9, "1-5") == 2.5
    assert g.percent_to_grade(T15, 75, "1-5") == 3.0
    assert g.percent_to_grade(T15, 74.9, "1-5") == 5.0
    assert g.percent_to_grade(None, 74.9, "percent") == 74.9
    assert g.percent_to_grade(T15, None, "1-5") is None
    assert g.grade_to_percent(T15, 2.25, "1-5") == 82
    assert g.grade_to_percent(T15, 2.2, "1-5") == 82  # nearest row
    assert g.grade_to_percent(None, 88.5, "percent") == 88.5


def test_validate_table():
    ok = g.validate_table([{"min": 0, "grade": 5}, {"min": 75, "grade": 3}, {"min": 90, "grade": 1}], "1-5")
    assert [r["min"] for r in ok] == [90, 75, 0]  # sorted high -> low
    for bad in [[], [{"min": 50, "grade": 1}, {"min": 40, "grade": 2}], [{"min": 0, "grade": 1}, {"min": 0, "grade": 2}],
                [{"min": 0}, {"min": 1, "grade": 2}], "x", [{"min": 120, "grade": 1}, {"min": 0, "grade": 2}]]:
        with pytest.raises(ValueError):
            g.validate_table(bad, "1-5")
    assert g.validate_table(None, "percent") == []


E = lambda s, t, c=None: {"score": s, "total": t, "category_id": c}


def test_unweighted_current_percent():
    assert g.current_percent([], []) is None
    assert g.current_percent([], [E(18, 20), E(85, 100)]) == pytest.approx(103 / 120 * 100)


def test_weighted_current_percent_renormalises():
    cats = [{"id": "q", "name": "Quizzes", "weight": 20}, {"id": "e", "name": "Exams", "weight": 40}, {"id": "f", "name": "Final", "weight": 40}]
    entries = [E(9, 10, "q"), E(80, 100, "e")]
    # only quizzes (90%) and exams (80%) graded so far: (20*90 + 40*80) / 60
    assert g.current_percent(cats, entries) == pytest.approx((20 * 90 + 40 * 80) / 60)
    assert g.current_percent(cats, []) is None
    assert g.current_percent(cats, [E(5, 10, None)]) is None  # uncategorised ignored when weights exist


def test_needed_weighted():
    cats = [{"id": "q", "weight": 20}, {"id": "e", "weight": 40}, {"id": "f", "weight": 40}]
    entries = [E(90, 100, "q"), E(80, 100, "e")]
    r = g.needed_for_target(cats, entries, 85, category_id="f")
    # (20*90 + 40*80 + 40*x) / 100 = 85  ->  x = 87.5
    assert r["needed_percent"] == pytest.approx(87.5) and r["possible"] and not r["secured"]
    assert g.needed_for_target(cats, entries, 99, category_id="f")["possible"] is False   # needs > 100
    assert g.needed_for_target(cats, entries, 50, category_id="f")["secured"] is True      # already safe
    assert g.needed_for_target(cats, entries, 85, category_id="nope") is None
    assert g.needed_for_target(cats, entries, 85) is None                                  # needs a category


def test_needed_unweighted_points():
    entries = [E(80, 100)]
    r = g.needed_for_target([], entries, 90, points=100)
    assert r["needed_percent"] == pytest.approx(100.0) and r["possible"]
    assert g.needed_for_target([], entries, 95, points=100)["possible"] is False
    assert g.needed_for_target([], entries, 90) is None


def test_overall_gwa_uses_units():
    subs = [{"percent": 98, "units": 3}, {"percent": 82, "units": 1}, {"percent": None, "units": 5}]
    o = g.overall(subs, "1-5", T15)
    assert o["grade"] == pytest.approx((1.0 * 3 + 2.25 * 1) / 4)
    assert o["percent"] == pytest.approx((98 * 3 + 82) / 4)
    assert g.overall([], "1-5", T15) == {"percent": None, "grade": None}
    assert g.overall([{"percent": 90, "units": 2}], "percent", None)["grade"] == 90
