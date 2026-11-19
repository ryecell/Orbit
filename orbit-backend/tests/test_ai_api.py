"""Study AI endpoints, with the model call faked (no network)."""
import pytest

import ai_providers


@pytest.fixture(autouse=True)
def fake_model(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test")
    ai_providers.text_quota._day = None
    ai_providers.text_quota._per_user = {}
    ai_providers.text_quota._total = 0
    calls = {"prompts": [], "reply": None}

    async def fake_generate(prompt, as_json=False, max_tokens=1500, env=None):
        calls["prompts"].append(prompt)
        return calls["reply"]

    monkeypatch.setattr(ai_providers, "generate", fake_generate)
    return calls


def _item(p, title="Cell notes", content="Mitochondria make ATP"):
    f = p.post("/folders", json={"name": "Biology"}).json()
    it = p.post(f"/folders/{f['id']}/items", json={"title": title, "content": content}).json()
    return f, it


def test_item_content_is_saved_listed_and_editable(alice):
    f, it = _item(alice)
    assert it["content"] == "Mitochondria make ATP"
    r = alice.patch(f"/items/{it['id']}", json={"content": "New text", "summary": "short"})
    assert r.status_code == 200 and r.json()["content"] == "New text" and r.json()["summary"] == "short"
    assert alice.patch(f"/items/{it['id']}", json={"content": "x" * 7000}).status_code == 422


def test_cannot_edit_or_use_someone_elses_item(alice, bob):
    f, it = _item(alice)
    assert bob.patch(f"/items/{it['id']}", json={"content": "hack"}).status_code == 404
    assert bob.post("/ai/summarize", json={"item_id": it["id"]}).status_code == 404
    assert bob.post("/ai/quiz", json={"item_ids": [it["id"]]}).status_code == 404
    assert bob.post("/ai/quiz", json={"folder_id": f["id"]}).status_code == 404


def test_chat_uses_only_my_notes(alice, bob, fake_model):
    _item(alice, "Secret alice notes", "alice only data")
    _item(bob, "Bob notes", "bob data about cells")
    fake_model["reply"] = "Answer [1]"
    r = bob.post("/ai/chat", json={"message": "tell me about cells"})
    assert r.status_code == 200 and r.json()["answer"] == "Answer [1]"
    assert "alice only data" not in fake_model["prompts"][0]
    assert r.json()["sources"][0]["title"] == "Bob notes"


def test_summarize_quiz_and_tasks(alice, fake_model):
    f, it = _item(alice)
    fake_model["reply"] = {"summary": "Cells make energy.", "key_points": ["ATP"]}
    assert alice.post("/ai/summarize", json={"item_id": it["id"]}).json()["summary"] == "Cells make energy."

    fake_model["reply"] = {"questions": [{"q": "Q?", "options": ["a", "b", "c", "d"], "answer": 1}]}
    r = alice.post("/ai/quiz", json={"folder_id": f["id"], "count": 3})
    assert r.status_code == 200 and r.json()["questions"][0]["answer"] == 1

    fake_model["reply"] = {"tasks": [{"text": "Review ATP", "priority": "High", "due_date": "2999-01-01"}]}
    r = alice.post("/ai/suggest-tasks", json={"item_ids": [it["id"]], "today": "2026-11-19"})
    assert r.json()["tasks"][0]["text"] == "Review ATP"


def test_empty_items_are_refused_and_bad_output_refunds(alice, fake_model):
    f, empty = _item(alice, "Empty", "")
    assert alice.post("/ai/summarize", json={"item_id": empty["id"]}).status_code == 422
    f2, it = _item(alice)
    left = alice.get("/ai/status").json()["study_left"]
    fake_model["reply"] = {"questions": []}
    assert alice.post("/ai/quiz", json={"item_ids": [it["id"]]}).status_code == 502
    assert alice.get("/ai/status").json()["study_left"] == left   # a failed answer costs nothing


def test_daily_cap(alice, fake_model, monkeypatch):
    monkeypatch.setenv("AI_TEXT_LIMIT_PER_USER", "2")
    _item(alice)
    fake_model["reply"] = "ok"
    assert alice.post("/ai/chat", json={"message": "a"}).status_code == 200
    assert alice.post("/ai/chat", json={"message": "b"}).status_code == 200
    assert alice.post("/ai/chat", json={"message": "c"}).status_code == 429
