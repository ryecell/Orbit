import json
import os
from datetime import datetime
from typing import List, Optional

import httpx
from fastapi import Depends, FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

import auth
import models
import schemas
from database import Base, SessionLocal, engine, get_db
from logging_config import logger

# --- Error monitoring (optional) ----------------------------------------------
# Only activates if SENTRY_DSN is set, so this is a no-op in local dev.
SENTRY_DSN = os.environ.get("SENTRY_DSN")
if SENTRY_DSN:
    import sentry_sdk

    sentry_sdk.init(dsn=SENTRY_DSN, traces_sample_rate=0.1, send_default_pii=False)
    logger.info("Sentry error monitoring enabled")

Base.metadata.create_all(bind=engine)
# ^ Convenience for local SQLite dev only. In any environment managed by
# Alembic (i.e. anywhere using DATABASE_URL/Postgres), `alembic upgrade head`
# is the real source of truth for the schema — this call becomes a harmless
# no-op once those tables already exist.

app = FastAPI(title="Orbit API", version="1.0.0")

# --- Rate limiting -----------------------------------------------------------
# Keyed by client IP. Applied to auth endpoints (brute-force / credential
# stuffing protection) and the AI endpoint (it costs money per call).
# In-memory by default (fine for one process); set REDIS_URL once you run
# more than one server instance, or limits won't be shared across them.
_redis_url = os.environ.get("REDIS_URL")
limiter = Limiter(key_func=get_remote_address, storage_uri=_redis_url or "memory://")
if not _redis_url:
    logger.info("REDIS_URL not set — rate limiting is in-memory (per process only).")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """
    Without this, an unhandled exception falls through to Starlette's
    default ServerErrorMiddleware, which sits OUTSIDE CORSMiddleware in the
    stack — so its response never gets CORS headers added. The browser then
    reports it as a CORS failure ("No Access-Control-Allow-Origin header"),
    which is misleading: the real problem is a server crash, not CORS. This
    handler runs INSIDE the CORS layer instead, so error responses get
    proper CORS headers, a clean JSON body instead of a raw traceback, and
    get logged / sent to Sentry if configured.
    """
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    if SENTRY_DSN:
        import sentry_sdk as _sentry_sdk

        _sentry_sdk.capture_exception(exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})

# --- CORS ----------------------------------------------------------------------
# Default to the local Vite dev server only — NOT a wildcard — so a forgotten
# env var fails safely instead of quietly allowing every origin on the internet.
_raw_origins = os.environ.get("ORBIT_ALLOWED_ORIGINS")
if _raw_origins:
    allowed_origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]
    if "*" in allowed_origins:
        print("[orbit] WARNING: ORBIT_ALLOWED_ORIGINS includes '*'. Fine for local testing, unsafe in production.")
else:
    allowed_origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
    print(
        "[orbit] ORBIT_ALLOWED_ORIGINS is not set — defaulting to the local Vite dev "
        "server only (http://localhost:5173). Set it explicitly for any other frontend origin."
    )

# Diagnostic: prints the exact parsed list on every startup, so a CORS
# mismatch can be confirmed by reading logs instead of guessing whether the
# env var actually took effect, has a typo, or has hidden whitespace.
print(f"[orbit] CORS allowed origins (parsed): {allowed_origins!r}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    # Only meaningful over HTTPS — browsers ignore it on plain HTTP, so it's
    # harmless to always send but won't do anything until you're behind TLS.
    response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    return response

DEFAULT_FOLDERS = [
    ("Biology", "#0E9F6E"),
    ("Math 21", "#5B3FE0"),
    ("Physics", "#E2456B"),
    ("Group Project", "#A855F7"),
    ("Workshops", "#D68A0C"),
    ("Personal", "#0891B2"),
]


# ============================== AUTH ==============================

@app.post("/auth/register", response_model=schemas.Token, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def register(request: Request, payload: schemas.UserCreate, db: Session = Depends(get_db)):
    if db.query(models.User).filter(models.User.username == payload.username).first():
        raise HTTPException(status_code=400, detail="That username is already taken")

    if payload.email and db.query(models.User).filter(models.User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="An account with this email already exists")

    user = models.User(
        username=payload.username,
        name=payload.name or payload.username,
        email=payload.email,
        hashed_password=auth.hash_password(payload.password),
        is_verified=False,
    )

    # Only generate a verification token if there's actually an email to
    # verify — most new accounts won't have one yet, and that's fine.
    if payload.email:
        verification_token, verification_expires = auth.generate_verification_token()
        user.verification_token = verification_token
        user.verification_expires = verification_expires

    db.add(user)
    db.commit()
    db.refresh(user)

    # Seed default folders so the archive isn't empty on first login.
    for name, color in DEFAULT_FOLDERS:
        db.add(models.Folder(name=name, color=color, owner_id=user.id))
    db.commit()

    if payload.email:
        auth.send_verification_email(user.email, user.verification_token)

    token = auth.create_access_token({"sub": user.id})
    return schemas.Token(access_token=token, user=user)


@app.get("/auth/verify")
def verify_email(token: str, db: Session = Depends(get_db)):
    from fastapi.responses import HTMLResponse

    user = db.query(models.User).filter(models.User.verification_token == token).first()
    if not user or not user.verification_expires or user.verification_expires < datetime.utcnow():
        return HTMLResponse("<h3>This verification link is invalid or has expired.</h3>", status_code=400)

    user.is_verified = True
    user.verification_token = None
    user.verification_expires = None
    db.commit()
    return HTMLResponse("<h3>Email verified — you can close this tab and return to Orbit.</h3>")


@app.post("/auth/resend-verification", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("3/minute")
def resend_verification(request: Request, user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    if not user.email:
        raise HTTPException(status_code=400, detail="No email is linked to this account yet.")
    if user.is_verified:
        return {"detail": "Already verified"}
    token, expires = auth.generate_verification_token()
    user.verification_token = token
    user.verification_expires = expires
    db.commit()
    auth.send_verification_email(user.email, token)
    return {"detail": "Verification email sent"}


@app.patch("/me/email", response_model=schemas.UserOut)
@limiter.limit("3/minute")
def link_email(
    request: Request,
    payload: schemas.LinkEmailRequest,
    user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    """Add or change the email linked to an existing account. Always requires re-verification."""
    existing = db.query(models.User).filter(models.User.email == payload.email, models.User.id != user.id).first()
    if existing:
        raise HTTPException(status_code=400, detail="That email is already linked to another account")

    token, expires = auth.generate_verification_token()
    user.email = payload.email
    user.is_verified = False
    user.verification_token = token
    user.verification_expires = expires
    db.commit()
    db.refresh(user)

    auth.send_verification_email(user.email, token)
    logger.info("Email linked to account %s, pending verification", user.username)
    return user


@app.post("/auth/login", response_model=schemas.Token)
@limiter.limit("10/minute")
def login(request: Request, payload: schemas.UserLogin, db: Session = Depends(get_db)):
    username = payload.username.strip().lower()
    user = db.query(models.User).filter(models.User.username == username).first()

    # Same generic error whether the username doesn't exist or the password
    # is wrong — distinguishing the two lets an attacker enumerate accounts.
    generic_error = HTTPException(status_code=401, detail="Incorrect username or password")

    if not user:
        raise generic_error

    if auth.is_locked(user):
        minutes_left = max(1, int((user.locked_until - datetime.utcnow()).total_seconds() // 60) + 1)
        raise HTTPException(
            status_code=423,
            detail=f"Too many failed attempts. Try again in about {minutes_left} minute(s).",
        )

    if not auth.verify_password(payload.password, user.hashed_password):
        auth.register_failed_login(user, db)
        raise generic_error

    auth.register_successful_login(user, db)
    token = auth.create_access_token({"sub": user.id})
    return schemas.Token(access_token=token, user=user)


@app.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    token: str = Depends(auth.oauth2_scheme),
    user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    auth.revoke_token(token, db)
    logger.info("Token revoked on logout: %s", user.username)


@app.post("/auth/forgot-password", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("3/minute")
def forgot_password(request: Request, payload: schemas.ForgotPasswordRequest, db: Session = Depends(get_db)):
    """
    Identified by username now, not email — email may not exist for this
    account. Always returns the same generic response regardless of whether
    the username exists or has an email linked, to prevent enumeration.
    """
    generic_response = {"detail": "If that account has an email on file, a reset link has been sent to it."}

    username = payload.username.strip().lower()
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user or not user.email:
        return generic_response

    token, expires = auth.generate_password_reset_token()
    user.reset_token = token
    user.reset_expires = expires
    db.commit()

    auth.send_password_reset_email(user.email, token)
    logger.info("Password reset requested for %s", user.username)
    return generic_response


@app.post("/auth/reset-password", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("5/minute")
def reset_password(request: Request, payload: schemas.ResetPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.reset_token == payload.token).first()
    if not user or not user.reset_expires or user.reset_expires < datetime.utcnow():
        raise HTTPException(status_code=400, detail="This reset link is invalid or has expired.")

    user.hashed_password = auth.hash_password(payload.new_password)
    user.reset_token = None
    user.reset_expires = None
    # Also clear any lockout — a successful reset is a legitimate way back
    # into the account, it shouldn't stay locked from the failed attempts
    # that led here.
    user.failed_login_attempts = 0
    user.locked_until = None
    # Invalidate every token issued before this moment, including the one
    # in the browser that's still "logged in" from before the reset.
    user.sessions_invalidated_at = datetime.utcnow()
    db.commit()

    logger.info("Password reset completed for %s", user.email)


@app.get("/me", response_model=schemas.UserOut)
def me(current_user: models.User = Depends(auth.get_current_user)):
    return current_user


# ============================== FOLDERS & ITEMS ==============================

def _item_out(item: models.Item) -> dict:
    return {
        "id": item.id,
        "title": item.title,
        "summary": item.summary,
        "tags": [t for t in item.tags.split(",") if t],
        "created_at": item.created_at,
    }


def _folder_out(folder: models.Folder) -> dict:
    return {
        "id": folder.id,
        "name": folder.name,
        "color": folder.color,
        "items": [_item_out(i) for i in folder.items],
    }


@app.get("/folders", response_model=List[schemas.FolderOut])
def list_folders(db: Session = Depends(get_db), user: models.User = Depends(auth.get_current_user)):
    folders = db.query(models.Folder).filter(models.Folder.owner_id == user.id).all()
    return [_folder_out(f) for f in folders]


@app.post("/folders", response_model=schemas.FolderOut, status_code=status.HTTP_201_CREATED)
def create_folder(payload: schemas.FolderCreate, db: Session = Depends(get_db), user: models.User = Depends(auth.get_current_user)):
    folder = models.Folder(name=payload.name, color=payload.color, owner_id=user.id)
    db.add(folder)
    db.commit()
    db.refresh(folder)
    return _folder_out(folder)


def _get_owned_folder(folder_id: str, db: Session, user: models.User) -> models.Folder:
    folder = (
        db.query(models.Folder)
        .filter(models.Folder.id == folder_id, models.Folder.owner_id == user.id)
        .first()
    )
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")
    return folder


@app.post("/folders/{folder_id}/items", response_model=schemas.ItemOut, status_code=status.HTTP_201_CREATED)
def add_item(folder_id: str, payload: schemas.ItemCreate, db: Session = Depends(get_db), user: models.User = Depends(auth.get_current_user)):
    folder = _get_owned_folder(folder_id, db, user)
    item = models.Item(
        title=payload.title,
        summary=payload.summary,
        tags=",".join(payload.tags),
        folder_id=folder.id,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _item_out(item)


@app.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(item_id: str, db: Session = Depends(get_db), user: models.User = Depends(auth.get_current_user)):
    item = (
        db.query(models.Item)
        .join(models.Folder)
        .filter(models.Item.id == item_id, models.Folder.owner_id == user.id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    db.delete(item)
    db.commit()


# ============================== TASKS ==============================

@app.get("/tasks", response_model=List[schemas.TaskOut])
def list_tasks(db: Session = Depends(get_db), user: models.User = Depends(auth.get_current_user)):
    return db.query(models.Task).filter(models.Task.owner_id == user.id).all()


@app.post("/tasks", response_model=schemas.TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(payload: schemas.TaskCreate, db: Session = Depends(get_db), user: models.User = Depends(auth.get_current_user)):
    task = models.Task(
        text=payload.text, priority=payload.priority, due_date=payload.due_date, owner_id=user.id
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@app.patch("/tasks/{task_id}", response_model=schemas.TaskOut)
def update_task(task_id: str, payload: schemas.TaskUpdate, db: Session = Depends(get_db), user: models.User = Depends(auth.get_current_user)):
    task = db.query(models.Task).filter(models.Task.id == task_id, models.Task.owner_id == user.id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    for field, value in payload.dict(exclude_unset=True).items():
        setattr(task, field, value)
    db.commit()
    db.refresh(task)
    return task


@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: str, db: Session = Depends(get_db), user: models.User = Depends(auth.get_current_user)):
    task = db.query(models.Task).filter(models.Task.id == task_id, models.Task.owner_id == user.id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(task)
    db.commit()


# ============================== REMINDERS ==============================

@app.get("/reminders", response_model=List[schemas.ReminderOut])
def list_reminders(db: Session = Depends(get_db), user: models.User = Depends(auth.get_current_user)):
    return db.query(models.Reminder).filter(models.Reminder.owner_id == user.id).all()


@app.post("/reminders", response_model=schemas.ReminderOut, status_code=status.HTTP_201_CREATED)
def create_reminder(payload: schemas.ReminderCreate, db: Session = Depends(get_db), user: models.User = Depends(auth.get_current_user)):
    reminder = models.Reminder(
        title=payload.title, detail=payload.detail, kind=payload.kind, owner_id=user.id
    )
    db.add(reminder)
    db.commit()
    db.refresh(reminder)
    return reminder


# ============================== GROUP CHAT ==============================

@app.get("/groups/{group_id}/messages", response_model=List[schemas.MessageOut])
def list_messages(group_id: str, db: Session = Depends(get_db), user: models.User = Depends(auth.get_current_user)):
    return (
        db.query(models.GroupMessage)
        .filter(models.GroupMessage.group_id == group_id)
        .order_by(models.GroupMessage.created_at.asc())
        .all()
    )


@app.post("/groups/{group_id}/messages", response_model=schemas.MessageOut, status_code=status.HTTP_201_CREATED)
def post_message(group_id: str, payload: schemas.MessageCreate, db: Session = Depends(get_db), user: models.User = Depends(auth.get_current_user)):
    # sender_name comes from the authenticated user, never from the request body —
    # trusting a client-supplied name would let anyone post as anyone else.
    msg = models.GroupMessage(group_id=group_id, sender_name=user.name, text=payload.text[:2000])
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


class ConnectionManager:
    def __init__(self):
        self.active: dict[str, list[WebSocket]] = {}

    async def connect(self, group_id: str, ws: WebSocket):
        await ws.accept()
        self.active.setdefault(group_id, []).append(ws)

    def disconnect(self, group_id: str, ws: WebSocket):
        if ws in self.active.get(group_id, []):
            self.active[group_id].remove(ws)

    async def broadcast(self, group_id: str, message: dict):
        for ws in self.active.get(group_id, []):
            await ws.send_json(message)


manager = ConnectionManager()


@app.websocket("/ws/groups/{group_id}")
async def group_chat_ws(websocket: WebSocket, group_id: str, token: Optional[str] = Query(default=None)):
    """
    Real-time chat, now authenticated. Connect with:
        /ws/groups/{group_id}?token=<the same JWT used for REST calls>
    Browsers can't set custom headers on a WebSocket handshake, so the token
    travels as a query param instead of an Authorization header — this is
    the standard workaround, but it does mean the token can end up in
    server access logs, so keep those logs access-controlled.

    The connection is validated BEFORE it's accepted: if the token is
    missing or invalid, we close the handshake instead of letting the
    client in and only then checking. sender_name is taken from the
    authenticated user, never from the client message, to prevent identity
    spoofing in the chat.
    """
    if not token:
        await websocket.close(code=4401)
        return

    db = SessionLocal()
    try:
        user = auth.get_current_user(token=token, db=db)
    except HTTPException:
        await websocket.close(code=4401)
        db.close()
        return

    await manager.connect(group_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            text = (data.get("text") or "").strip()
            if not text:
                continue
            msg = models.GroupMessage(
                group_id=group_id,
                sender_name=user.name,
                text=text[:2000],
            )
            db.add(msg)
            db.commit()
            db.refresh(msg)
            await manager.broadcast(
                group_id,
                {
                    "id": msg.id,
                    "sender_name": msg.sender_name,
                    "text": msg.text,
                    "created_at": msg.created_at.isoformat(),
                },
            )
    except WebSocketDisconnect:
        manager.disconnect(group_id, websocket)
    finally:
        db.close()


# ============================== AI AUTO-TAGGING ==============================

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = "claude-sonnet-4-6"


@app.post("/ai/analyze", response_model=schemas.AnalyzeResponse)
@limiter.limit("15/minute")
async def analyze_image(request: Request, payload: schemas.AnalyzeRequest, user: models.User = Depends(auth.get_current_user)):
    """
    Server-side AI tagging: the image never needs to expose your Anthropic API
    key to the browser. Set ANTHROPIC_API_KEY as an environment variable.
    """
    if not ANTHROPIC_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="ANTHROPIC_API_KEY is not set on the server. Export it before starting the app.",
        )

    # Cap payload size before it reaches Anthropic — otherwise a huge image
    # (accidental or malicious) costs you money and ties up a worker for no
    # reason. Base64 is ~4/3 the size of the raw bytes.
    MAX_IMAGE_BYTES = 8 * 1024 * 1024  # 8 MB
    approx_bytes = len(payload.image_base64) * 3 / 4
    if approx_bytes > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Image is too large (max 8MB).")

    folders = payload.candidate_folders or [name for name, _ in DEFAULT_FOLDERS]
    prompt = (
        "You are the AI auto-tagging engine inside a digital archive app called Orbit. "
        "Look at this image \u2014 it may be handwritten notes, a printed document, a diagram, or a photo \u2014 "
        "and respond with ONLY raw JSON, no markdown fences, no preamble, in exactly this shape: "
        '{"title": "short descriptive title, max 6 words", '
        f'"folder": "best matching folder from this list: {", ".join(folders)}", '
        '"tags": ["3 to 5 short lowercase keyword tags"], '
        '"summary": "one sentence, max 22 words, summarizing the content"}'
    )

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": ANTHROPIC_MODEL,
                "max_tokens": 500,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": payload.media_type,
                                    "data": payload.image_base64,
                                },
                            },
                            {"type": "text", "text": prompt},
                        ],
                    }
                ],
            },
        )

    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Anthropic API error: {resp.text}")

    data = resp.json()
    text = "".join(block.get("text", "") for block in data.get("content", []))
    cleaned = text.replace("```json", "").replace("```", "").strip()

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        raise HTTPException(status_code=502, detail="AI response was not valid JSON")

    return schemas.AnalyzeResponse(
        title=parsed.get("title", "Untitled note"),
        folder=parsed.get("folder", "Personal"),
        tags=parsed.get("tags", []),
        summary=parsed.get("summary", ""),
    )


@app.get("/health")
def health():
    return {"status": "ok"}
