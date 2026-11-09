"""
Test setup: a throwaway SQLite database, rate limits switched off, and helpers
that create users and return ready-to-use authorized clients.

Run from the orbit-backend folder:   pip install -r requirements-dev.txt && pytest -q
"""
import os
import sys
import tempfile

# Must be set BEFORE the app is imported — database.py reads it at import time.
_tmp = tempfile.mkdtemp(prefix="orbit-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ.pop("SENTRY_DSN", None)
os.environ.pop("REDIS_URL", None)
os.environ.setdefault("ORBIT_SECRET_KEY", "test-secret-key-not-for-production-use-0123456789")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient

import main
from database import Base, engine

main.limiter.enabled = False  # otherwise tests trip the per-minute limits


@pytest.fixture(autouse=True)
def clean_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture()
def client():
    return TestClient(main.app)


class Person:
    """A signed-in user: .id, .username and a client that sends their token."""

    def __init__(self, username: str):
        self.username = username
        self.client = TestClient(main.app)
        r = self.client.post(
            "/auth/register",
            json={"username": username, "password": "password123", "accept_terms": True},
        )
        assert r.status_code == 201, r.text
        body = r.json()
        self.id = body["user"]["id"]
        self.token = body["access_token"]
        self.client.headers.update({"Authorization": f"Bearer {self.token}"})

    # short helpers so tests read like sentences
    def get(self, *a, **k): return self.client.get(*a, **k)
    def post(self, *a, **k): return self.client.post(*a, **k)
    def patch(self, *a, **k): return self.client.patch(*a, **k)
    def put(self, *a, **k): return self.client.put(*a, **k)
    def delete(self, *a, **k): return self.client.delete(*a, **k)


@pytest.fixture()
def make_person():
    return Person


@pytest.fixture()
def alice():
    return Person("alice")


@pytest.fixture()
def bob():
    return Person("bob")


@pytest.fixture()
def carol():
    return Person("carol")


def befriend(a: Person, b: Person):
    r = a.post("/friends/requests", json={"username": b.username})
    assert r.status_code in (200, 201), r.text
    req_id = r.json()["id"]
    r = b.post(f"/friends/requests/{req_id}/accept")
    assert r.status_code == 200, r.text
