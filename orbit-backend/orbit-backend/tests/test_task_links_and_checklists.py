"""Tasks linked to archive folders/items, and checklists inside items."""


def _folder_with_item(p, name="Biology"):
    f = p.post("/folders", json={"name": name}).json()
    it = p.post(f"/folders/{f['id']}/items", json={"title": "Cell notes"}).json()
    return f, it


def _item_in_listing(p, item_id):
    for f in p.get("/folders").json():
        for it in f["items"]:
            if it["id"] == item_id:
                return it


def test_task_can_link_to_item_and_gets_its_folder(alice):
    f, it = _folder_with_item(alice)
    t = alice.post("/tasks", json={"text": "re-read", "item_id": it["id"]}).json()
    assert t["item_id"] == it["id"] and t["folder_id"] == f["id"]


def test_task_can_link_to_folder_only_and_unlink(alice):
    f, _ = _folder_with_item(alice)
    t = alice.post("/tasks", json={"text": "x", "folder_id": f["id"]}).json()
    assert t["folder_id"] == f["id"] and t["item_id"] is None
    t = alice.patch(f"/tasks/{t['id']}", json={"folder_id": None, "item_id": None}).json()
    assert t["folder_id"] is None and t["item_id"] is None
    # unrelated edits leave the link alone
    t = alice.patch(f"/tasks/{alice.post('/tasks', json={'text': 'y', 'folder_id': f['id']}).json()['id']}", json={"done": True}).json()
    assert t["folder_id"] == f["id"]


def test_cannot_link_to_someone_elses_archive(alice, bob):
    f, it = _folder_with_item(alice)
    assert bob.post("/tasks", json={"text": "x", "folder_id": f["id"]}).status_code == 404
    assert bob.post("/tasks", json={"text": "x", "item_id": it["id"]}).status_code == 404
    mine = bob.post("/tasks", json={"text": "ok"}).json()
    assert bob.patch(f"/tasks/{mine['id']}", json={"item_id": it["id"]}).status_code == 404


def test_deleting_item_or_folder_keeps_tasks(alice):
    f, it = _folder_with_item(alice)
    t = alice.post("/tasks", json={"text": "about item", "item_id": it["id"]}).json()
    assert alice.delete(f"/items/{it['id']}").status_code == 204
    after = [x for x in alice.get("/tasks").json() if x["id"] == t["id"]][0]
    assert after["item_id"] is None and after["folder_id"] == f["id"]
    assert alice.delete(f"/folders/{f['id']}").status_code == 204
    after = [x for x in alice.get("/tasks").json() if x["id"] == t["id"]][0]
    assert after["folder_id"] is None


def test_checklist_lifecycle(alice):
    _, it = _folder_with_item(alice)
    a = alice.post(f"/items/{it['id']}/checklist", json={"text": "  memorize   diagram "})
    assert a.status_code == 201 and a.json()["text"] == "memorize diagram" and a.json()["done"] is False
    b = alice.post(f"/items/{it['id']}/checklist", json={"text": "second"}).json()
    listed = _item_in_listing(alice, it["id"])["checklist"]
    assert [c["text"] for c in listed] == ["memorize diagram", "second"]  # order kept
    assert alice.patch(f"/checklist/{a.json()['id']}", json={"done": True}).json()["done"] is True
    assert alice.delete(f"/checklist/{b['id']}").status_code == 204
    assert len(_item_in_listing(alice, it["id"])["checklist"]) == 1


def test_checklist_validation_and_cap(alice):
    _, it = _folder_with_item(alice)
    assert alice.post(f"/items/{it['id']}/checklist", json={"text": "   "}).status_code == 422
    for i in range(50):
        assert alice.post(f"/items/{it['id']}/checklist", json={"text": f"l{i}"}).status_code == 201
    assert alice.post(f"/items/{it['id']}/checklist", json={"text": "one too many"}).status_code == 400


def test_checklists_are_private(alice, bob):
    _, it = _folder_with_item(alice)
    e = alice.post(f"/items/{it['id']}/checklist", json={"text": "mine"}).json()
    assert bob.post(f"/items/{it['id']}/checklist", json={"text": "x"}).status_code == 404
    assert bob.patch(f"/checklist/{e['id']}", json={"done": True}).status_code == 404
    assert bob.delete(f"/checklist/{e['id']}").status_code == 404


def test_deleting_item_removes_its_checklist(alice):
    _, it = _folder_with_item(alice)
    alice.post(f"/items/{it['id']}/checklist", json={"text": "gone soon"})
    alice.delete(f"/items/{it['id']}")
    assert "gone soon" not in alice.get("/me/export").text


def test_export_and_account_deletion_cover_new_data(alice):
    f, it = _folder_with_item(alice)
    alice.post(f"/items/{it['id']}/checklist", json={"text": "check-me"})
    alice.post("/tasks", json={"text": "t", "item_id": it["id"]})
    text = alice.get("/me/export").text
    assert "check-me" in text and "Cell notes" in text
    assert alice.post("/me/delete", json={"password": "password123"}).status_code == 204
