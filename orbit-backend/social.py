"""
Friends, blocking, friend profiles and direct messages.

Policy (kept deliberately conservative — this is a student app):
  * Direct messages only work between accepted friends.
  * People are found by EXACT username (rate-limited, so the user list can't be
    scraped) or from a group they share with you.
  * Blocking removes any friendship/request and silently stops requests and DMs.
    Anything that would reveal "this person blocked you" answers with a plain 404.

Wired up from main.py:  app.include_router(social.build_router(limiter))
"""
from datetime import datetime
from typing import Dict, List, Optional, Set

from fastapi import APIRouter, Depends, HTTPException, Query, Request, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

import auth
import models
from database import SessionLocal, get_db

MAX_DM_LENGTH = 2000
MAX_PENDING_OUTGOING = 50


# ---------- small pure helpers (easy to unit-test) ----------

def normalize_username(raw: str) -> str:
    return (raw or "").strip().lstrip("@").strip().lower()


def clean_dm_text(raw: str) -> str:
    text = (raw or "").strip()
    if not text:
        raise ValueError("Message can't be empty")
    return text[:MAX_DM_LENGTH]


def parse_before(raw: Optional[str]) -> Optional[datetime]:
    """Accepts an ISO timestamp (with or without Z/offset); returns naive UTC."""
    if not raw:
        return None
    s = raw.strip()
    if s.endswith("Z"):
        s = s[:-1]
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is not None:
        dt = (dt - dt.utcoffset()).replace(tzinfo=None)
    return dt


# ---------- schemas ----------

class FriendRequestCreate(BaseModel):
    user_id: Optional[str] = Field(default=None, max_length=64)
    username: Optional[str] = Field(default=None, max_length=64)


class DMCreate(BaseModel):
    text: str = Field(max_length=10_000)


# ---------- live push (one socket set per user) ----------

class UserSockets:
    def __init__(self):
        self.active: Dict[str, Set[WebSocket]] = {}

    async def connect(self, user_id: str, ws: WebSocket):
        await ws.accept()
        self.active.setdefault(user_id, set()).add(ws)

    def disconnect(self, user_id: str, ws: WebSocket):
        socks = self.active.get(user_id)
        if socks:
            socks.discard(ws)
            if not socks:
                self.active.pop(user_id, None)

    async def push(self, user_id: str, payload: dict):
        for ws in list(self.active.get(user_id, ())):
            try:
                await ws.send_json(payload)
            except Exception:
                self.disconnect(user_id, ws)


sockets = UserSockets()


# ---------- relationship helpers ----------

def _pair(db: Session, a: str, b: str) -> Optional[models.Friendship]:
    return (
        db.query(models.Friendship)
        .filter(
            or_(
                and_(models.Friendship.requester_id == a, models.Friendship.addressee_id == b),
                and_(models.Friendship.requester_id == b, models.Friendship.addressee_id == a),
            )
        )
        .first()
    )


def are_friends(db: Session, a: str, b: str) -> bool:
    f = _pair(db, a, b)
    return bool(f and f.status == "accepted")


def blocked_by(db: Session, blocker: str, blocked: str) -> bool:
    return (
        db.query(models.UserBlock.id)
        .filter(models.UserBlock.blocker_id == blocker, models.UserBlock.blocked_id == blocked)
        .first()
        is not None
    )


def blocked_either(db: Session, a: str, b: str) -> bool:
    return blocked_by(db, a, b) or blocked_by(db, b, a)


def _group_ids(db: Session, user_id: str):
    return db.query(models.GroupMembership.group_id).filter(models.GroupMembership.user_id == user_id)


def shares_group(db: Session, a: str, b: str) -> bool:
    return (
        db.query(models.GroupMembership.id)
        .filter(models.GroupMembership.user_id == b, models.GroupMembership.group_id.in_(_group_ids(db, a)))
        .first()
        is not None
    )


def relationship_of(db: Session, me: str, other: str) -> str:
    """self | friends | pending_out | pending_in | blocked | none"""
    if me == other:
        return "self"
    if blocked_by(db, me, other):
        return "blocked"
    f = _pair(db, me, other)
    if not f:
        return "none"
    if f.status == "accepted":
        return "friends"
    return "pending_out" if f.requester_id == me else "pending_in"


def can_see_user(db: Session, viewer: str, target: str) -> bool:
    """May `viewer` see `target`'s profile / picture? Self, friends, a pending
    request either way, or a shared group — and never across a block."""
    if viewer == target:
        return True
    if blocked_either(db, viewer, target):
        return False
    if _pair(db, viewer, target):
        return True
    return shares_group(db, viewer, target)


def _live_user(db: Session, user_id: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.id == user_id, models.User.deleted_at.is_(None)).first()


def _brief(u: models.User) -> dict:
    return {
        "id": u.id,
        "username": u.username,
        "name": u.name or u.username,
        "has_avatar": u.has_avatar,
        "avatar_version": u.avatar_version,
    }


def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() + "Z" if dt else None


def _dm_out(m: models.DirectMessage) -> dict:
    return {
        "id": m.id,
        "sender_id": m.sender_id,
        "recipient_id": m.recipient_id,
        "text": m.text,
        "created_at": _iso(m.created_at),
        "read_at": _iso(m.read_at),
    }


def _friend_ids(db: Session, me: str) -> List[str]:
    rows = (
        db.query(models.Friendship)
        .filter(
            models.Friendship.status == "accepted",
            or_(models.Friendship.requester_id == me, models.Friendship.addressee_id == me),
        )
        .all()
    )
    return [r.addressee_id if r.requester_id == me else r.requester_id for r in rows]


def _not_found():
    return HTTPException(status_code=404, detail="User not found")


def _resolve_target(db: Session, me: models.User, user_id: Optional[str], username: Optional[str]) -> models.User:
    target = None
    if user_id:
        target = _live_user(db, user_id)
    elif username:
        uname = normalize_username(username)
        if uname:
            target = (
                db.query(models.User)
                .filter(models.User.username == uname, models.User.deleted_at.is_(None))
                .first()
            )
    if not target or target.id == me.id or blocked_by(db, target.id, me.id):
        raise _not_found()
    return target


# ---------- router ----------

def build_router(limiter) -> APIRouter:
    router = APIRouter()

    # ----- discovery -----

    @router.get("/users/lookup")
    @limiter.limit("30/minute")
    def lookup_user(
        request: Request,
        username: str = Query(max_length=64),
        me: models.User = Depends(auth.get_current_user),
        db: Session = Depends(get_db),
    ):
        uname = normalize_username(username)
        target = (
            db.query(models.User).filter(models.User.username == uname, models.User.deleted_at.is_(None)).first()
            if uname
            else None
        )
        if not target or target.id == me.id or blocked_by(db, target.id, me.id):
            raise _not_found()
        return {**_brief(target), "relationship": relationship_of(db, me.id, target.id)}

    @router.get("/groups/{group_id}/members")
    def group_members(group_id: str, me: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
        is_member = (
            db.query(models.GroupMembership.id)
            .filter(models.GroupMembership.group_id == group_id, models.GroupMembership.user_id == me.id)
            .first()
        )
        if not is_member:
            raise HTTPException(status_code=404, detail="Group not found")
        members = (
            db.query(models.User)
            .join(models.GroupMembership, models.GroupMembership.user_id == models.User.id)
            .filter(models.GroupMembership.group_id == group_id, models.User.deleted_at.is_(None))
            .order_by(models.GroupMembership.joined_at.asc())
            .all()
        )
        out = []
        for u in members:
            if u.id != me.id and blocked_by(db, u.id, me.id):
                continue
            out.append({**_brief(u), "relationship": relationship_of(db, me.id, u.id)})
        return out

    # ----- friends & requests -----

    @router.get("/friends")
    def list_friends(me: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
        ids = _friend_ids(db, me.id)
        if not ids:
            return []
        users = db.query(models.User).filter(models.User.id.in_(ids), models.User.deleted_at.is_(None)).all()
        users.sort(key=lambda u: (u.name or u.username).lower())
        return [_brief(u) for u in users]

    @router.get("/friends/requests")
    def list_requests(me: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
        rows = (
            db.query(models.Friendship)
            .filter(
                models.Friendship.status == "pending",
                or_(models.Friendship.requester_id == me.id, models.Friendship.addressee_id == me.id),
            )
            .order_by(models.Friendship.created_at.desc())
            .all()
        )
        incoming, outgoing = [], []
        for r in rows:
            other_id = r.addressee_id if r.requester_id == me.id else r.requester_id
            other = _live_user(db, other_id)
            if not other or blocked_either(db, me.id, other_id):
                continue
            item = {"id": r.id, "created_at": _iso(r.created_at), "user": _brief(other)}
            (outgoing if r.requester_id == me.id else incoming).append(item)
        return {"incoming": incoming, "outgoing": outgoing}

    @router.post("/friends/requests")
    @limiter.limit("20/minute")
    async def send_request(
        request: Request,
        payload: FriendRequestCreate,
        me: models.User = Depends(auth.get_current_user),
        db: Session = Depends(get_db),
    ):
        if not payload.user_id and not payload.username:
            raise HTTPException(status_code=422, detail="Provide a username")
        if payload.username and normalize_username(payload.username) == me.username:
            raise HTTPException(status_code=400, detail="That's you!")
        target = _resolve_target(db, me, payload.user_id, payload.username)
        if blocked_by(db, me.id, target.id):
            raise HTTPException(status_code=409, detail="You blocked this person. Unblock them first.")

        existing = _pair(db, me.id, target.id)
        if existing:
            if existing.status == "accepted":
                raise HTTPException(status_code=409, detail="You're already friends")
            if existing.requester_id == me.id:
                return {"status": "pending_out", "id": existing.id}
            # They already asked us — sending a request back just accepts theirs.
            existing.status = "accepted"
            existing.responded_at = datetime.utcnow()
            db.commit()
            await sockets.push(target.id, {"type": "friend_accepted", "user": _brief(me)})
            return {"status": "friends", "id": existing.id}

        pending = (
            db.query(func.count(models.Friendship.id))
            .filter(models.Friendship.requester_id == me.id, models.Friendship.status == "pending")
            .scalar()
        )
        if pending >= MAX_PENDING_OUTGOING:
            raise HTTPException(status_code=429, detail="Too many pending requests. Cancel some first.")

        fr = models.Friendship(requester_id=me.id, addressee_id=target.id, status="pending")
        db.add(fr)
        db.commit()
        db.refresh(fr)
        await sockets.push(target.id, {"type": "friend_request", "user": _brief(me)})
        return {"status": "pending_out", "id": fr.id}

    @router.post("/friends/requests/{request_id}/accept")
    async def accept_request(request_id: str, me: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
        fr = (
            db.query(models.Friendship)
            .filter(
                models.Friendship.id == request_id,
                models.Friendship.addressee_id == me.id,
                models.Friendship.status == "pending",
            )
            .first()
        )
        if not fr or blocked_either(db, me.id, fr.requester_id) or not _live_user(db, fr.requester_id):
            raise HTTPException(status_code=404, detail="Request not found")
        fr.status = "accepted"
        fr.responded_at = datetime.utcnow()
        db.commit()
        await sockets.push(fr.requester_id, {"type": "friend_accepted", "user": _brief(me)})
        return {"status": "friends"}

    @router.delete("/friends/requests/{request_id}", status_code=status.HTTP_204_NO_CONTENT)
    def cancel_or_decline(request_id: str, me: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
        fr = (
            db.query(models.Friendship)
            .filter(
                models.Friendship.id == request_id,
                models.Friendship.status == "pending",
                or_(models.Friendship.requester_id == me.id, models.Friendship.addressee_id == me.id),
            )
            .first()
        )
        if not fr:
            raise HTTPException(status_code=404, detail="Request not found")
        db.delete(fr)
        db.commit()

    @router.delete("/friends/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
    def unfriend(user_id: str, me: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
        fr = _pair(db, me.id, user_id)
        if not fr or fr.status != "accepted":
            raise HTTPException(status_code=404, detail="Not friends")
        db.delete(fr)
        db.commit()

    # ----- blocking -----

    @router.get("/blocks")
    def list_blocks(me: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
        rows = db.query(models.UserBlock).filter(models.UserBlock.blocker_id == me.id).all()
        out = []
        for b in rows:
            u = _live_user(db, b.blocked_id)
            if u:
                out.append(_brief(u))
        return out

    @router.post("/blocks/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
    @limiter.limit("30/minute")
    def block_user(request: Request, user_id: str, me: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
        if user_id == me.id:
            raise HTTPException(status_code=400, detail="You can't block yourself")
        if not _live_user(db, user_id):
            raise _not_found()
        if not blocked_by(db, me.id, user_id):
            db.add(models.UserBlock(blocker_id=me.id, blocked_id=user_id))
        fr = _pair(db, me.id, user_id)
        if fr:
            db.delete(fr)
        db.commit()

    @router.delete("/blocks/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
    def unblock_user(user_id: str, me: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
        db.query(models.UserBlock).filter(
            models.UserBlock.blocker_id == me.id, models.UserBlock.blocked_id == user_id
        ).delete(synchronize_session=False)
        db.commit()

    # ----- friend profile -----

    @router.get("/users/{user_id}/profile")
    def user_profile(user_id: str, me: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
        target = _live_user(db, user_id)
        if not target or not can_see_user(db, me.id, user_id):
            raise _not_found()
        rel = relationship_of(db, me.id, user_id)
        data = {
            **_brief(target),
            "joined_at": _iso(target.created_at),
            "relationship": rel,
            "friends_since": None,
            "mutual_groups": [],
            "mutual_friends": 0,
        }
        if rel == "self":
            return data
        fr = _pair(db, me.id, user_id)
        if fr and fr.status == "accepted":
            data["friends_since"] = _iso(fr.responded_at or fr.created_at)
        if fr and fr.status == "pending":
            data["request_id"] = fr.id
        groups = (
            db.query(models.Group)
            .join(models.GroupMembership, models.GroupMembership.group_id == models.Group.id)
            .filter(
                models.GroupMembership.user_id == user_id,
                models.Group.id.in_(_group_ids(db, me.id)),
            )
            .all()
        )
        data["mutual_groups"] = [{"id": g.id, "name": g.name} for g in groups]
        data["mutual_friends"] = len(set(_friend_ids(db, me.id)) & set(_friend_ids(db, user_id)))
        return data

    # ----- direct messages -----

    def _require_dm_partner(db: Session, me: models.User, user_id: str) -> models.User:
        other = _live_user(db, user_id)
        if not other or user_id == me.id or blocked_either(db, me.id, user_id) or not are_friends(db, me.id, user_id):
            raise HTTPException(status_code=404, detail="Conversation not found")
        return other

    @router.get("/dm/conversations")
    def conversations(me: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
        friend_ids = set(_friend_ids(db, me.id))
        if not friend_ids:
            return []
        recent = (
            db.query(models.DirectMessage)
            .filter(or_(models.DirectMessage.sender_id == me.id, models.DirectMessage.recipient_id == me.id))
            .order_by(models.DirectMessage.created_at.desc())
            .limit(1000)
            .all()
        )
        last: Dict[str, models.DirectMessage] = {}
        for m in recent:
            partner = m.recipient_id if m.sender_id == me.id else m.sender_id
            if partner in friend_ids and partner not in last:
                last[partner] = m
        unread_rows = (
            db.query(models.DirectMessage.sender_id, func.count(models.DirectMessage.id))
            .filter(models.DirectMessage.recipient_id == me.id, models.DirectMessage.read_at.is_(None))
            .group_by(models.DirectMessage.sender_id)
            .all()
        )
        unread = {sid: n for sid, n in unread_rows}
        out = []
        for pid, msg in last.items():
            u = _live_user(db, pid)
            if not u or blocked_either(db, me.id, pid):
                continue
            out.append({"user": _brief(u), "last_message": _dm_out(msg), "unread": unread.get(pid, 0)})
        out.sort(key=lambda c: c["last_message"]["created_at"], reverse=True)
        return out

    @router.get("/dm/{user_id}/messages")
    def dm_history(
        user_id: str,
        before: Optional[str] = Query(default=None, max_length=40),
        limit: int = Query(default=50, ge=1, le=100),
        me: models.User = Depends(auth.get_current_user),
        db: Session = Depends(get_db),
    ):
        _require_dm_partner(db, me, user_id)
        q = db.query(models.DirectMessage).filter(
            or_(
                and_(models.DirectMessage.sender_id == me.id, models.DirectMessage.recipient_id == user_id),
                and_(models.DirectMessage.sender_id == user_id, models.DirectMessage.recipient_id == me.id),
            )
        )
        cutoff = parse_before(before)
        if cutoff:
            q = q.filter(models.DirectMessage.created_at < cutoff)
        rows = q.order_by(models.DirectMessage.created_at.desc()).limit(limit + 1).all()
        has_more = len(rows) > limit
        rows = list(reversed(rows[:limit]))
        return {"messages": [_dm_out(m) for m in rows], "has_more": has_more}

    @router.post("/dm/{user_id}/messages", status_code=status.HTTP_201_CREATED)
    @limiter.limit("60/minute")
    async def dm_send(
        request: Request,
        user_id: str,
        payload: DMCreate,
        me: models.User = Depends(auth.get_current_user),
        db: Session = Depends(get_db),
    ):
        _require_dm_partner(db, me, user_id)
        try:
            text = clean_dm_text(payload.text)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        msg = models.DirectMessage(sender_id=me.id, recipient_id=user_id, text=text)
        db.add(msg)
        db.commit()
        db.refresh(msg)
        out = _dm_out(msg)
        await sockets.push(user_id, {"type": "dm", "message": out, "from": _brief(me)})
        return out

    @router.post("/dm/{user_id}/read", status_code=status.HTTP_204_NO_CONTENT)
    def dm_mark_read(user_id: str, me: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
        db.query(models.DirectMessage).filter(
            models.DirectMessage.sender_id == user_id,
            models.DirectMessage.recipient_id == me.id,
            models.DirectMessage.read_at.is_(None),
        ).update({"read_at": datetime.utcnow()}, synchronize_session=False)
        db.commit()

    @router.get("/social/summary")
    def social_summary(me: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
        friend_ids = _friend_ids(db, me.id)
        unread = 0
        if friend_ids:
            unread = (
                db.query(func.count(models.DirectMessage.id))
                .filter(
                    models.DirectMessage.recipient_id == me.id,
                    models.DirectMessage.read_at.is_(None),
                    models.DirectMessage.sender_id.in_(friend_ids),
                )
                .scalar()
            )
        incoming = (
            db.query(func.count(models.Friendship.id))
            .filter(models.Friendship.addressee_id == me.id, models.Friendship.status == "pending")
            .scalar()
        )
        return {"unread_dms": unread or 0, "incoming_requests": incoming or 0}

    # ----- live push socket -----

    @router.websocket("/ws/me")
    async def my_socket(websocket: WebSocket, token: Optional[str] = Query(default=None)):
        """Personal push channel: new DMs and friend activity. Same token-in-query
        handshake as the group chat socket. The client sends {"type":"ping"} now
        and then; we answer {"type":"pong"}."""
        if not token:
            await websocket.close(code=4401)
            return
        db = SessionLocal()
        try:
            user = auth.get_current_user(token=token, db=db)
            user_id = user.id
        except HTTPException:
            await websocket.close(code=4401)
            return
        finally:
            db.close()

        await sockets.connect(user_id, websocket)
        try:
            while True:
                await websocket.receive_text()
                await websocket.send_json({"type": "pong"})
        except WebSocketDisconnect:
            pass
        except Exception:
            pass
        finally:
            sockets.disconnect(user_id, websocket)

    return router


# ---------- account deletion / export helpers (called from main.py) ----------

def erase_social_data(db: Session, user_id: str) -> None:
    db.query(models.DirectMessage).filter(
        or_(models.DirectMessage.sender_id == user_id, models.DirectMessage.recipient_id == user_id)
    ).delete(synchronize_session=False)
    db.query(models.Friendship).filter(
        or_(models.Friendship.requester_id == user_id, models.Friendship.addressee_id == user_id)
    ).delete(synchronize_session=False)
    db.query(models.UserBlock).filter(
        or_(models.UserBlock.blocker_id == user_id, models.UserBlock.blocked_id == user_id)
    ).delete(synchronize_session=False)


def export_social_data(db: Session, user_id: str) -> dict:
    friends = [u for u in db.query(models.User).filter(models.User.id.in_(_friend_ids(db, user_id))).all()] if _friend_ids(db, user_id) else []
    sent = (
        db.query(models.DirectMessage)
        .filter(models.DirectMessage.sender_id == user_id)
        .order_by(models.DirectMessage.created_at.asc())
        .all()
    )
    names: Dict[str, str] = {}
    for m in sent:
        if m.recipient_id not in names:
            u = db.query(models.User).filter(models.User.id == m.recipient_id).first()
            names[m.recipient_id] = u.username if u else "(deleted user)"
    return {
        "friends": [{"username": u.username, "name": u.name} for u in friends],
        "direct_messages_sent": [
            {"to": names.get(m.recipient_id), "text": m.text, "sent_at": m.created_at} for m in sent
        ],
    }
