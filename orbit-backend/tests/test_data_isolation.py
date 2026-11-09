"""One user must never be able to read, change or delete another user's data."""
import pytest


def _make_folder(p, name="Secret"):
    r = p.post("/folders", json={"name": name})
    assert r.status_code == 201, r.text
    return r.json()


def test_requires_login_everywhere(client):
    for method, path in [
        ("get", "/folders"), ("get", "/tasks"), ("get", "/reminders"), ("get", "/events"),
        ("get", "/study-sessions"), ("get", "/groups"), ("get", "/friends"), ("get", "/me"),
        ("get", "/dm/conversations"), ("get", "/me/export"),
    ]:
        assert getattr(client, method)(path).status_code == 401, path


def test_folders_are_private(alice, bob):
    f = _make_folder(alice)
    assert all(x["id"] != f["id"] for x in bob.get("/folders").json())
    assert bob.patch(f"/folders/{f['id']}", json={"name": "Hacked"}).status_code in (403, 404)
    assert bob.delete(f"/folders/{f['id']}").status_code in (403, 404)
    assert bob.post(f"/folders/{f['id']}/items", json={"title": "x"}).status_code in (403, 404)
    # still intact for the owner
    names = [x["name"] for x in alice.get("/folders").json()]
    assert "Secret" in names


def test_items_cannot_be_deleted_by_others(alice, bob):
    f = _make_folder(alice)
    item = alice.post(f"/folders/{f['id']}/items", json={"title": "diary", "summary": "private"}).json()
    assert bob.delete(f"/items/{item['id']}").status_code in (403, 404)
    folder = [x for x in alice.get("/folders").json() if x["id"] == f["id"]][0]
    assert any(i["id"] == item["id"] for i in folder["items"])


def test_tasks_are_private(alice, bob):
    t = alice.post("/tasks", json={"text": "alice only"}).json()
    assert bob.get("/tasks").json() == []
    assert bob.patch(f"/tasks/{t['id']}", json={"done": True}).status_code in (403, 404)
    assert bob.delete(f"/tasks/{t['id']}").status_code in (403, 404)
    assert alice.get("/tasks").json()[0]["done"] is False


def test_events_are_private(alice, bob):
    e = alice.post("/events", json={"title": "dentist", "start_time": "2026-12-01T09:00:00"}).json()
    assert bob.get("/events").json() == []
    assert bob.patch(f"/events/{e['id']}", json={"title": "x"}).status_code in (403, 404)
    assert bob.delete(f"/events/{e['id']}").status_code in (403, 404)


def test_study_sessions_are_private(alice, bob):
    s = alice.post("/study-sessions", json={"minutes": 30, "title": "math"}).json()
    assert bob.get("/study-sessions").json() == []
    assert bob.patch(f"/study-sessions/{s['id']}", json={"title": "x"}).status_code in (403, 404)
    assert bob.delete(f"/study-sessions/{s['id']}").status_code in (403, 404)


def test_reminders_are_private(alice, bob):
    alice.post("/reminders", json={"title": "secret reminder"})
    assert bob.get("/reminders").json() == []


def test_export_contains_only_own_data(alice, bob):
    alice.post("/tasks", json={"text": "alice-task-xyz"})
    bob.post("/tasks", json={"text": "bob-task-xyz"})
    data = bob.get("/me/export").text
    assert "bob-task-xyz" in data
    assert "alice-task-xyz" not in data


def test_forged_or_garbage_tokens_rejected(client):
    for token in ["abc", "Bearer", "a.b.c", ""]:
        r = client.get("/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 401


def test_deleted_account_token_stops_working(alice):
    r = alice.post("/me/delete", json={"password": "password123"})
    assert r.status_code == 204, r.text
    assert alice.get("/me").status_code == 401
