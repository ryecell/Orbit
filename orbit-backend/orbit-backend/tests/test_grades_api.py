"""Grades tracker endpoints: private to the owner, and the numbers come out right."""


def _setup(p, scale="1-5"):
    r = p.put("/grades/settings", json={"scale": scale})
    assert r.status_code == 200, r.text
    return r.json()


def _subject(p, name="Math", units=3):
    r = p.post("/grades/subjects", json={"name": name, "units": units})
    assert r.status_code == 201, r.text
    return r.json()["subjects"][-1]


def test_needs_login(client):
    assert client.get("/grades").status_code == 401


def test_starts_without_a_scale(alice):
    snap = alice.get("/grades").json()
    assert snap["settings"]["scale"] is None and snap["subjects"] == []


def test_choose_scale_and_defaults(alice):
    s = _setup(alice, "1-5")["settings"]
    assert s["scale"] == "1-5" and s["passing_percent"] == 75.0 and s["table"][0] == {"min": 97.0, "grade": 1.0}
    assert alice.put("/grades/settings", json={"scale": "weird"}).status_code == 422
    s = alice.put("/grades/settings", json={"scale": "gpa4", "passing_percent": 60}).json()["settings"]
    assert s["scale"] == "gpa4" and s["passing_percent"] == 60 and s["table"][0]["grade"] == 4.0


def test_custom_table_validated(alice):
    bad = alice.put("/grades/settings", json={"scale": "1-5", "table": [{"min": 50, "grade": 1}, {"min": 40, "grade": 2}]})
    assert bad.status_code == 422
    ok = alice.put("/grades/settings", json={"scale": "1-5", "table": [{"min": 90, "grade": 1}, {"min": 0, "grade": 5}]})
    assert ok.status_code == 200 and len(ok.json()["settings"]["table"]) == 2


def test_scores_convert_to_the_users_scale(alice):
    _setup(alice, "1-5")
    sub = _subject(alice)
    snap = alice.post(f"/grades/subjects/{sub['id']}/entries", json={"title": "Quiz 1", "score": 82, "total": 100}).json()
    s = snap["subjects"][0]
    assert round(s["percent"]) == 82 and s["grade"] == 2.25
    assert snap["overall"]["grade"] == 2.25
    # same raw score, different scale: nothing lost
    snap = alice.put("/grades/settings", json={"scale": "percent"}).json()
    assert round(snap["subjects"][0]["percent"]) == 82 and round(snap["subjects"][0]["grade"]) == 82


def test_weighted_categories_and_needed(alice):
    _setup(alice, "percent")
    sub = _subject(alice)
    for name, w in [("Quizzes", 20), ("Exams", 40), ("Final", 40)]:
        snap = alice.post(f"/grades/subjects/{sub['id']}/categories", json={"name": name, "weight": w}).json()
    cats = {c["name"]: c["id"] for c in snap["subjects"][0]["categories"]}
    alice.post(f"/grades/subjects/{sub['id']}/entries", json={"title": "q", "score": 90, "total": 100, "category_id": cats["Quizzes"]})
    alice.post(f"/grades/subjects/{sub['id']}/entries", json={"title": "e", "score": 80, "total": 100, "category_id": cats["Exams"]})
    r = alice.get(f"/grades/subjects/{sub['id']}/needed", params={"target_grade": 85, "category_id": cats["Final"]}).json()
    assert abs(r["needed_percent"] - 87.5) < 1e-6 and r["possible"]
    assert alice.get(f"/grades/subjects/{sub['id']}/needed", params={"target_grade": 85}).status_code == 422


def test_final_grade_override(alice):
    _setup(alice, "1-5")
    sub = _subject(alice)
    snap = alice.patch(f"/grades/subjects/{sub['id']}", json={"final_grade": 1.75}).json()
    assert snap["subjects"][0]["grade"] == 1.75 and snap["subjects"][0]["has_final_override"]
    snap = alice.patch(f"/grades/subjects/{sub['id']}", json={"final_grade": None}).json()
    assert snap["subjects"][0]["grade"] is None


def test_validation_and_caps(alice):
    _setup(alice)
    sub = _subject(alice)
    base = f"/grades/subjects/{sub['id']}/entries"
    assert alice.post(base, json={"title": "x", "score": 5, "total": 0}).status_code == 422
    assert alice.post(base, json={"title": "x", "score": -1, "total": 10}).status_code == 422
    assert alice.post(base, json={"title": "x", "score": 500, "total": 10}).status_code == 422
    assert alice.post(base, json={"title": "x", "score": 5, "total": 10, "date": "yesterday"}).status_code == 422
    assert alice.post(base, json={"title": "x", "score": 5, "total": 10, "category_id": "nope"}).status_code == 404
    assert alice.post("/grades/subjects", json={"name": "   "}).status_code == 422


def test_deleting_category_keeps_scores(alice):
    _setup(alice)
    sub = _subject(alice)
    snap = alice.post(f"/grades/subjects/{sub['id']}/categories", json={"name": "Quizzes", "weight": 50}).json()
    cid = snap["subjects"][0]["categories"][0]["id"]
    alice.post(f"/grades/subjects/{sub['id']}/entries", json={"title": "q", "score": 9, "total": 10, "category_id": cid})
    snap = alice.delete(f"/grades/categories/{cid}").json()
    assert snap["subjects"][0]["categories"] == [] and len(snap["subjects"][0]["entries"]) == 1


def test_grades_are_private(alice, bob):
    _setup(alice)
    sub = _subject(alice, "Secret subject")
    e = alice.post(f"/grades/subjects/{sub['id']}/entries", json={"title": "x", "score": 1, "total": 2}).json()["subjects"][0]["entries"][0]
    assert bob.get("/grades").json()["subjects"] == []
    assert bob.patch(f"/grades/subjects/{sub['id']}", json={"name": "hacked"}).status_code == 404
    assert bob.delete(f"/grades/subjects/{sub['id']}").status_code == 404
    assert bob.post(f"/grades/subjects/{sub['id']}/entries", json={"title": "x", "score": 1, "total": 2}).status_code == 404
    assert bob.patch(f"/grades/entries/{e['id']}", json={"score": 2}).status_code == 404
    assert bob.delete(f"/grades/entries/{e['id']}").status_code == 404
    assert "Secret subject" not in bob.get("/me/export").text


def test_cannot_link_someone_elses_folder(alice, bob):
    f = alice.post("/folders", json={"name": "Math notes"}).json()
    _setup(bob)
    assert bob.post("/grades/subjects", json={"name": "Math", "folder_id": f["id"]}).status_code == 404


def test_friends_cannot_see_grades(alice, bob):
    from tests.conftest import befriend
    befriend(alice, bob)
    _setup(alice)
    _subject(alice, "Private")
    assert bob.get("/grades").json()["subjects"] == []


def test_export_and_account_deletion(alice):
    _setup(alice)
    sub = _subject(alice, "Chem-export-test")
    alice.post(f"/grades/subjects/{sub['id']}/entries", json={"title": "Lab", "score": 9, "total": 10})
    assert "Chem-export-test" in alice.get("/me/export").text
    assert alice.post("/me/delete", json={"password": "password123"}).status_code == 204
