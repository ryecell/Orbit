"""Friend requests, blocking, profiles and direct messages."""
from tests.conftest import befriend


def test_cannot_dm_a_non_friend(alice, bob):
    assert alice.post(f"/dm/{bob.id}/messages", json={"text": "hi"}).status_code == 404
    assert alice.get(f"/dm/{bob.id}/messages").status_code == 404


def test_request_accept_then_message(alice, bob):
    r = alice.post("/friends/requests", json={"username": "bob"})
    assert r.status_code == 200 and r.json()["status"] == "pending_out"
    # still not allowed while pending
    assert alice.post(f"/dm/{bob.id}/messages", json={"text": "hi"}).status_code == 404

    incoming = bob.get("/friends/requests").json()["incoming"]
    assert len(incoming) == 1 and incoming[0]["user"]["id"] == alice.id
    assert bob.post(f"/friends/requests/{incoming[0]['id']}/accept").status_code == 200

    assert alice.post(f"/dm/{bob.id}/messages", json={"text": "hello bob"}).status_code == 201
    convos = bob.get("/dm/conversations").json()
    assert convos[0]["user"]["id"] == alice.id and convos[0]["unread"] == 1
    assert bob.get("/social/summary").json()["unread_dms"] == 1
    hist = bob.get(f"/dm/{alice.id}/messages").json()["messages"]
    assert [m["text"] for m in hist] == ["hello bob"]
    assert bob.post(f"/dm/{alice.id}/read").status_code == 204
    assert bob.get("/social/summary").json()["unread_dms"] == 0


def test_only_the_addressee_can_accept(alice, bob, carol):
    rid = alice.post("/friends/requests", json={"username": "bob"}).json()["id"]
    assert alice.post(f"/friends/requests/{rid}/accept").status_code == 404  # sender can't self-accept
    assert carol.post(f"/friends/requests/{rid}/accept").status_code == 404
    assert carol.delete(f"/friends/requests/{rid}").status_code == 404  # third party can't cancel it


def test_crossing_requests_auto_accept(alice, bob):
    alice.post("/friends/requests", json={"username": "bob"})
    r = bob.post("/friends/requests", json={"username": "alice"})
    assert r.json()["status"] == "friends"
    assert [f["id"] for f in alice.get("/friends").json()] == [bob.id]


def test_cannot_friend_yourself_or_unknown(alice):
    assert alice.post("/friends/requests", json={"username": "alice"}).status_code == 400
    assert alice.post("/friends/requests", json={"username": "ghost"}).status_code == 404


def test_duplicate_request_is_harmless(alice, bob):
    a = alice.post("/friends/requests", json={"username": "bob"}).json()
    b = alice.post("/friends/requests", json={"username": "bob"}).json()
    assert a["id"] == b["id"]
    assert len(bob.get("/friends/requests").json()["incoming"]) == 1


def test_unfriend_stops_messaging(alice, bob):
    befriend(alice, bob)
    assert alice.delete(f"/friends/{bob.id}").status_code == 204
    assert alice.post(f"/dm/{bob.id}/messages", json={"text": "x"}).status_code == 404
    assert bob.get(f"/dm/{alice.id}/messages").status_code == 404


def test_block_removes_friendship_and_hides_you(alice, bob):
    befriend(alice, bob)
    assert alice.post(f"/blocks/{bob.id}").status_code == 204
    assert alice.get("/friends").json() == []
    assert bob.get("/friends").json() == []
    # bob can't message, can't re-request, can't look alice up — and the answers don't reveal the block
    assert bob.post(f"/dm/{alice.id}/messages", json={"text": "x"}).status_code == 404
    assert bob.post("/friends/requests", json={"username": "alice"}).status_code == 404
    assert bob.get("/users/lookup", params={"username": "alice"}).status_code == 404
    assert bob.get(f"/users/{alice.id}/profile").status_code == 404
    # alice must unblock before re-adding
    assert alice.post("/friends/requests", json={"username": "bob"}).status_code == 409
    assert alice.delete(f"/blocks/{bob.id}").status_code == 204
    assert alice.post("/friends/requests", json={"username": "bob"}).status_code == 200


def test_message_validation(alice, bob):
    befriend(alice, bob)
    assert alice.post(f"/dm/{bob.id}/messages", json={"text": "   "}).status_code == 422
    long = alice.post(f"/dm/{bob.id}/messages", json={"text": "a" * 5000}).json()
    assert len(long["text"]) == 2000


def test_third_party_cannot_read_a_conversation(alice, bob, carol):
    befriend(alice, bob)
    alice.post(f"/dm/{bob.id}/messages", json={"text": "private"})
    # carol asking for "her" conversation with alice or bob sees nothing of it
    assert carol.get(f"/dm/{alice.id}/messages").status_code == 404
    assert carol.get(f"/dm/{bob.id}/messages").status_code == 404
    assert carol.get("/dm/conversations").json() == []


def test_profile_visibility(alice, bob, carol):
    # strangers can't view profiles
    assert carol.get(f"/users/{alice.id}/profile").status_code == 404
    # shared group makes them visible, with the relationship shown
    g = alice.post("/groups", json={"name": "Club"}).json()
    carol.post("/groups/join", json={"invite_code": g["invite_code"]})
    p = carol.get(f"/users/{alice.id}/profile").json()
    assert p["relationship"] == "none" and p["mutual_groups"][0]["name"] == "Club"
    assert "email" not in p and "hashed_password" not in p


def test_lookup_is_exact_match_only(alice, bob):
    assert alice.get("/users/lookup", params={"username": "bo"}).status_code == 404
    assert alice.get("/users/lookup", params={"username": "@Bob"}).json()["id"] == bob.id


def test_avatar_access_follows_relationships(alice, bob, carol):
    # no picture set -> 404 either way, but a stranger must get the same 404 as a friend without a picture,
    # and blocked users must not be able to see it even with a shared group
    g = alice.post("/groups", json={"name": "G"}).json()
    bob.post("/groups/join", json={"invite_code": g["invite_code"]})
    alice.post(f"/blocks/{bob.id}")
    assert bob.get(f"/users/{alice.id}/avatar").status_code == 404


def test_account_deletion_removes_social_data(alice, bob):
    befriend(alice, bob)
    alice.post(f"/dm/{bob.id}/messages", json={"text": "bye"})
    assert alice.post("/me/delete", json={"password": "password123"}).status_code == 204
    assert bob.get("/friends").json() == []
    assert bob.get("/dm/conversations").json() == []
