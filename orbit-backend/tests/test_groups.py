"""Group data is visible only to members."""


def _group(p, name="Study crew"):
    r = p.post("/groups", json={"name": name})
    assert r.status_code == 201, r.text
    return r.json()


def test_non_member_cannot_read_or_post(alice, bob):
    g = _group(alice)
    assert bob.get(f"/groups/{g['id']}/messages").status_code == 404
    assert bob.post(f"/groups/{g['id']}/messages", json={"text": "hi"}).status_code == 404
    assert bob.get(f"/groups/{g['id']}/members").status_code == 404
    assert all(x["id"] != g["id"] for x in bob.get("/groups").json())


def test_member_can_chat_after_joining(alice, bob):
    g = _group(alice)
    assert bob.post("/groups/join", json={"invite_code": g["invite_code"]}).status_code == 200
    assert bob.post(f"/groups/{g['id']}/messages", json={"text": "hello"}).status_code == 201
    msgs = alice.get(f"/groups/{g['id']}/messages").json()
    assert [m["text"] for m in msgs] == ["hello"]
    # sender is taken from the login, not from the request body
    assert msgs[0]["sender_id"] == bob.id


def test_left_group_is_off_limits(alice, bob):
    g = _group(alice)
    bob.post("/groups/join", json={"invite_code": g["invite_code"]})
    assert bob.post(f"/groups/{g['id']}/leave").status_code == 204
    assert bob.get(f"/groups/{g['id']}/messages").status_code == 404


def test_bad_invite_code(bob):
    assert bob.post("/groups/join", json={"invite_code": "nope"}).status_code == 404
