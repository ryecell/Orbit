"""
One-way sync from Orbit's calendar to the person's Google Calendar.

Orbit events are pushed to their *primary* Google calendar when they're
created, edited or deleted in Orbit. Nothing is read back from Google.

Configuration (environment variables — never commit real values):
  GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET  OAuth client from Google Cloud Console
  ORBIT_TOKEN_KEY                         any long random string; encrypts stored refresh tokens
  GOOGLE_REDIRECT_URI                     optional; defaults to <ORBIT_PUBLIC_API_URL>/integrations/google/callback
If any of the first three is missing, the feature simply reports itself as not configured.
"""
import base64
import hashlib
import json
import os
import time
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import urlencode
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx
from cryptography.fernet import Fernet, InvalidToken

from logging_config import logger

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
REVOKE_URL = "https://oauth2.googleapis.com/revoke"
CAL_BASE = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
CALENDAR_SCOPE = "https://www.googleapis.com/auth/calendar.events"
SCOPES = f"openid email {CALENDAR_SCOPE}"
TIMEOUT = 8.0


class GoogleError(Exception):
    """A Google call failed in a way that may be worth retrying later."""


class GoogleAuthError(GoogleError):
    """Google rejected the stored credentials — the person must reconnect."""


def _client_id() -> str:
    return os.environ.get("GOOGLE_CLIENT_ID", "")


def _client_secret() -> str:
    return os.environ.get("GOOGLE_CLIENT_SECRET", "")


def _token_key() -> str:
    return os.environ.get("ORBIT_TOKEN_KEY", "")


def redirect_uri() -> str:
    explicit = os.environ.get("GOOGLE_REDIRECT_URI")
    if explicit:
        return explicit
    api = os.environ.get("ORBIT_PUBLIC_API_URL", "http://localhost:8000").rstrip("/")
    return f"{api}/integrations/google/callback"


def is_configured() -> bool:
    return bool(_client_id() and _client_secret() and _token_key())


# ---------- token encryption ----------

def _fernet() -> Fernet:
    # Derive a valid Fernet key from whatever long secret the operator set.
    digest = hashlib.sha256(_token_key().encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt(plain: str) -> str:
    return _fernet().encrypt(plain.encode("utf-8")).decode("ascii")


def decrypt(token: str) -> str:
    try:
        return _fernet().decrypt(token.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        # Key was changed or the value is corrupt — treat like a revoked grant.
        raise GoogleAuthError("Stored Google token can't be decrypted") from exc


# ---------- helpers ----------

def valid_timezone(name: Optional[str]) -> str:
    """Returns name if it's a real IANA zone, otherwise 'UTC'."""
    if name and len(name) <= 64:
        try:
            ZoneInfo(name)
            return name
        except (ZoneInfoNotFoundError, ValueError, OSError):
            pass
    return "UTC"


def build_auth_url(state: str) -> str:
    params = {
        "client_id": _client_id(),
        "redirect_uri": redirect_uri(),
        "response_type": "code",
        "scope": SCOPES,
        "access_type": "offline",   # we need a refresh token
        "prompt": "consent",        # …and Google only issues one when consent is shown
        "state": state,
    }
    return f"{AUTH_URL}?{urlencode(params)}"


def _email_from_id_token(id_token: Optional[str]) -> Optional[str]:
    # The id_token comes straight from Google's token endpoint over TLS, so
    # reading its payload without re-verifying the signature is fine here.
    if not id_token:
        return None
    try:
        payload = id_token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload)).get("email")
    except Exception:
        return None


def exchange_code(code: str) -> dict:
    """Trades the one-time code for tokens. Returns refresh_token, email, scope."""
    try:
        r = httpx.post(
            TOKEN_URL,
            data={
                "code": code,
                "client_id": _client_id(),
                "client_secret": _client_secret(),
                "redirect_uri": redirect_uri(),
                "grant_type": "authorization_code",
            },
            timeout=TIMEOUT,
        )
    except httpx.HTTPError as exc:
        raise GoogleError(f"Token exchange failed: {exc}") from exc
    if r.status_code != 200:
        logger.warning("Google code exchange rejected (HTTP %s)", r.status_code)
        raise GoogleError("Google rejected the sign-in")
    data = r.json()
    return {
        "refresh_token": data.get("refresh_token"),
        "scope": data.get("scope", ""),
        "email": _email_from_id_token(data.get("id_token")),
    }


# Short-lived access tokens, cached per process so a burst of edits doesn't
# refresh every time. Losing this on restart is harmless.
_access_cache: dict = {}


def forget_access_token(user_id: str) -> None:
    _access_cache.pop(user_id, None)


def _access_token(user_id: str, refresh_token_enc: str) -> str:
    cached = _access_cache.get(user_id)
    if cached and cached[1] > time.time() + 30:
        return cached[0]
    refresh = decrypt(refresh_token_enc)
    try:
        r = httpx.post(
            TOKEN_URL,
            data={
                "client_id": _client_id(),
                "client_secret": _client_secret(),
                "refresh_token": refresh,
                "grant_type": "refresh_token",
            },
            timeout=TIMEOUT,
        )
    except httpx.HTTPError as exc:
        raise GoogleError(f"Token refresh failed: {exc}") from exc
    if r.status_code in (400, 401):
        # invalid_grant: revoked by the person, or a "Testing"-mode token past its 7 days.
        raise GoogleAuthError("Google no longer accepts this connection")
    if r.status_code != 200:
        raise GoogleError(f"Token refresh returned HTTP {r.status_code}")
    data = r.json()
    token = data["access_token"]
    _access_cache[user_id] = (token, time.time() + int(data.get("expires_in", 3000)))
    return token


def revoke(refresh_token_enc: str) -> None:
    """Best-effort: tells Google to drop the grant. Never raises."""
    try:
        httpx.post(REVOKE_URL, data={"token": decrypt(refresh_token_enc)}, timeout=TIMEOUT)
    except Exception:
        logger.info("Could not revoke Google token (already invalid or unreachable)")


# ---------- calendar events ----------

def google_id_for(event_id: str) -> str:
    # Google lets us choose the event id (chars 0-9 a-v). Using the Orbit id makes
    # every push idempotent — a retry or a reconnect can never create a duplicate.
    return event_id.replace("-", "").lower()


def _body(event, tz: str) -> dict:
    start = event.start_time.replace(microsecond=0, tzinfo=None)
    end = event.end_time.replace(microsecond=0, tzinfo=None) if event.end_time else None
    if end is None or end <= start:
        end = start + timedelta(hours=1)
    return {
        "summary": event.title,
        "description": event.description or "",
        "start": {"dateTime": start.isoformat(), "timeZone": tz},
        "end": {"dateTime": end.isoformat(), "timeZone": tz},
        "status": "confirmed",
    }


def _call(method: str, url: str, token: str, **kw) -> httpx.Response:
    try:
        r = httpx.request(method, url, headers={"Authorization": f"Bearer {token}"}, timeout=TIMEOUT, **kw)
    except httpx.HTTPError as exc:
        raise GoogleError(f"Google Calendar request failed: {exc}") from exc
    if r.status_code in (401, 403) and "insufficientPermissions" in r.text:
        raise GoogleAuthError("Calendar permission was removed")
    if r.status_code == 401:
        raise GoogleAuthError("Google rejected the access token")
    return r


def upsert_event(conn, event) -> str:
    """Creates or updates the Google copy of an Orbit event. Returns the Google event id."""
    token = _access_token(conn.user_id, conn.refresh_token_enc)
    gid = google_id_for(event.id)
    body = _body(event, valid_timezone(conn.timezone))

    if event.google_event_id:
        r = _call("PATCH", f"{CAL_BASE}/{gid}", token, json=body)
        if r.status_code == 404:
            r = _call("POST", CAL_BASE, token, json={**body, "id": gid})
    else:
        r = _call("POST", CAL_BASE, token, json={**body, "id": gid})
        if r.status_code == 409:  # already there from an earlier connection — just update it
            r = _call("PATCH", f"{CAL_BASE}/{gid}", token, json=body)
    if r.status_code >= 400:
        logger.warning("Google Calendar upsert failed (HTTP %s)", r.status_code)
        raise GoogleError(f"Google Calendar returned HTTP {r.status_code}")
    return gid


def delete_event(conn, google_event_id: str) -> None:
    token = _access_token(conn.user_id, conn.refresh_token_enc)
    r = _call("DELETE", f"{CAL_BASE}/{google_event_id}", token)
    if r.status_code in (200, 204, 404, 410):
        return
    logger.warning("Google Calendar delete failed (HTTP %s)", r.status_code)
    raise GoogleError(f"Google Calendar returned HTTP {r.status_code}")
