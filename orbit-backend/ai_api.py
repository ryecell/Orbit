"""
Study AI endpoints: summaries, quizzes, chat over your own notes, and task ideas.
Prompt building and result validation live in study_ai.py; the provider call is ai_providers.generate.

Nothing here writes to the database. Results go back to the browser, which saves what the
person chooses to keep (a summary via PATCH /items/{id}, suggested tasks via POST /tasks).
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

import ai_providers
import auth
import models
import study_ai
from database import get_db

MAX_ITEMS_PER_REQUEST = 10
CHAT_CONTEXT_POOL = 200   # newest notes considered when answering a chat question


class ChatTurn(BaseModel):
    role: str = Field(max_length=12)
    text: str = Field(max_length=1000)


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    history: List[ChatTurn] = Field(default=[], max_length=12)
    folder_id: Optional[str] = Field(default=None, max_length=64)


class SummarizeIn(BaseModel):
    item_id: str = Field(max_length=64)


class QuizIn(BaseModel):
    item_ids: List[str] = Field(default=[], max_length=MAX_ITEMS_PER_REQUEST)
    folder_id: Optional[str] = Field(default=None, max_length=64)
    count: int = Field(default=5, ge=3, le=10)
    kind: str = Field(default="mcq", pattern="^(mcq|flashcards)$")


class TasksIn(BaseModel):
    item_ids: List[str] = Field(default=[], max_length=MAX_ITEMS_PER_REQUEST)
    folder_id: Optional[str] = Field(default=None, max_length=64)
    goal: str = Field(default="", max_length=200)
    today: Optional[str] = Field(default=None, max_length=10)


def _item_dict(item: models.Item) -> dict:
    return {
        "id": item.id,
        "title": item.title,
        "summary": item.summary or "",
        "content": item.content or "",
        "tags": [t for t in (item.tags or "").split(",") if t],
        "folder": item.folder.name if item.folder else "",
        "checklist": [c.text for c in item.checklist],
    }


def _owned_items(db: Session, user: models.User, item_ids=(), folder_id=None, limit=MAX_ITEMS_PER_REQUEST) -> List[dict]:
    """The caller's own items only — by ids, or a whole folder (newest first). 404 if anything isn't theirs."""
    q = db.query(models.Item).join(models.Folder).filter(models.Folder.owner_id == user.id)
    if item_ids:
        ids = list(dict.fromkeys(item_ids))
        rows = q.filter(models.Item.id.in_(ids)).all()
        if len(rows) != len(ids):
            raise HTTPException(status_code=404, detail="Item not found")
    elif folder_id:
        if not db.query(models.Folder).filter(models.Folder.id == folder_id, models.Folder.owner_id == user.id).first():
            raise HTTPException(status_code=404, detail="Folder not found")
        rows = q.filter(models.Item.folder_id == folder_id).order_by(models.Item.created_at.desc()).limit(limit).all()
    else:
        rows = q.order_by(models.Item.created_at.desc()).limit(limit).all()
    return [_item_dict(r) for r in rows[:limit]]


def build_router(limiter) -> APIRouter:
    router = APIRouter(prefix="/ai")

    def _ready():
        if not ai_providers.provider_name():
            raise HTTPException(status_code=503, detail="AI isn't set up on this server yet.")

    async def _run(user: models.User, prompt: str, as_json: bool, max_tokens: int):
        """Spend one study request, call the model, refund on failure."""
        per_user, total = ai_providers.text_limits()
        denied = ai_providers.text_quota.try_consume(user.id, per_user, total)
        if denied:
            raise HTTPException(status_code=429, detail=denied)
        try:
            return await ai_providers.generate(prompt, as_json=as_json, max_tokens=max_tokens)
        except ai_providers.AIError as exc:
            ai_providers.text_quota.refund(user.id)
            raise HTTPException(status_code=exc.status, detail=str(exc))

    def _refund_bad_output(user: models.User):
        ai_providers.text_quota.refund(user.id)
        raise HTTPException(status_code=502, detail="The AI gave an unusable answer. Please try again.")

    @router.get("/status")
    def status(user: models.User = Depends(auth.get_current_user)):
        per_user, _ = ai_providers.text_limits()
        return {
            "enabled": bool(ai_providers.provider_name()),
            "study_left": ai_providers.text_quota.remaining(user.id, per_user),
            "study_limit": per_user,
        }

    @router.post("/chat")
    @limiter.limit("20/minute")
    async def chat(request: Request, payload: ChatIn, user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
        _ready()
        pool = _owned_items(db, user, folder_id=payload.folder_id, limit=CHAT_CONTEXT_POOL)
        picked = study_ai.pick_items(payload.message, pool)
        prompt = study_ai.build_chat_prompt(payload.message, [t.model_dump() for t in payload.history], picked)
        answer = await _run(user, prompt, as_json=False, max_tokens=700)
        if not answer:
            _refund_bad_output(user)
        return {"answer": answer[:3000],
                "sources": [{"id": it["id"], "title": it["title"]} for it in picked]}

    @router.post("/summarize")
    @limiter.limit("15/minute")
    async def summarize(request: Request, payload: SummarizeIn, user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
        _ready()
        item = _owned_items(db, user, item_ids=[payload.item_id])[0]
        if not study_ai.has_material(item):
            raise HTTPException(status_code=422, detail="Add some notes to this item first, then I can summarize them.")
        data = await _run(user, study_ai.build_summary_prompt(item), as_json=True, max_tokens=700)
        try:
            return study_ai.normalize_summary(data)
        except ValueError:
            _refund_bad_output(user)

    @router.post("/quiz")
    @limiter.limit("10/minute")
    async def quiz(request: Request, payload: QuizIn, user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
        _ready()
        items = [i for i in _owned_items(db, user, payload.item_ids, payload.folder_id) if study_ai.has_material(i)]
        if not items:
            raise HTTPException(status_code=422, detail="Pick notes that have some content first — a quiz needs something to ask about.")
        data = await _run(user, study_ai.build_quiz_prompt(items, payload.count, payload.kind),
                          as_json=True, max_tokens=2200)
        try:
            return study_ai.normalize_quiz(data, payload.kind, payload.count)
        except ValueError:
            _refund_bad_output(user)

    @router.post("/suggest-tasks")
    @limiter.limit("10/minute")
    async def suggest_tasks(request: Request, payload: TasksIn, user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
        _ready()
        items = [i for i in _owned_items(db, user, payload.item_ids, payload.folder_id) if study_ai.has_material(i)]
        if not items and not payload.goal.strip():
            raise HTTPException(status_code=422, detail="Pick some notes or type a goal so I know what to plan.")
        today = study_ai.safe_today(payload.today)
        existing = [t.text for t in db.query(models.Task).filter(models.Task.owner_id == user.id, models.Task.done == False).limit(50).all()]  # noqa: E712
        data = await _run(user, study_ai.build_tasks_prompt(items, payload.goal, today, existing),
                          as_json=True, max_tokens=900)
        try:
            return {"tasks": study_ai.normalize_tasks(data, today, existing)}
        except ValueError:
            _refund_bad_output(user)

    return router
