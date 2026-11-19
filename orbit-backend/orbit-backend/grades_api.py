"""Grades tracker endpoints. Everything here is private to the signed-in user — grades are never
visible to friends or group members. The maths lives in grades.py."""
import json
import re
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session, selectinload

import auth
import grades
import models
from database import get_db

MAX_SUBJECTS = 30
MAX_CATEGORIES = 10
MAX_ENTRIES = 200
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _name(v: str) -> str:
    v = " ".join((v or "").split())[:60]
    if not v:
        raise ValueError("Name can't be empty")
    return v


class SettingsIn(BaseModel):
    scale: str
    passing_percent: Optional[float] = Field(default=None, ge=0, le=100)
    table: Optional[list] = None

    @field_validator("scale")
    @classmethod
    def _scale(cls, v):
        if v not in grades.SCALES:
            raise ValueError("Unknown grading scale")
        return v


class SubjectIn(BaseModel):
    name: str = Field(max_length=200)
    units: float = Field(default=1.0, gt=0, le=30)
    folder_id: Optional[str] = Field(default=None, max_length=64)

    @field_validator("name")
    @classmethod
    def _clean_name(cls, v):
        return _name(v)


class SubjectPatch(BaseModel):
    name: Optional[str] = Field(default=None, max_length=200)
    units: Optional[float] = Field(default=None, gt=0, le=30)
    folder_id: Optional[str] = Field(default=None, max_length=64)
    final_grade: Optional[float] = Field(default=None, ge=0, le=100)  # in the user's own scale; null clears it

    @field_validator("name")
    @classmethod
    def _n(cls, v):
        return None if v is None else _name(v)


class CategoryIn(BaseModel):
    name: str = Field(max_length=200)
    weight: float = Field(default=0.0, ge=0, le=100)

    @field_validator("name")
    @classmethod
    def _clean_name(cls, v):
        return _name(v)


class CategoryPatch(BaseModel):
    name: Optional[str] = Field(default=None, max_length=200)
    weight: Optional[float] = Field(default=None, ge=0, le=100)

    @field_validator("name")
    @classmethod
    def _n(cls, v):
        return None if v is None else _name(v)


class EntryIn(BaseModel):
    title: str = Field(max_length=200)
    score: float = Field(ge=0, le=100000)
    total: float = Field(gt=0, le=100000)
    category_id: Optional[str] = Field(default=None, max_length=64)
    date: str = ""

    @field_validator("title")
    @classmethod
    def _clean_name(cls, v):
        return _name(v)

    @field_validator("date")
    @classmethod
    def _d(cls, v):
        v = (v or "").strip()
        if v and not DATE_RE.match(v):
            raise ValueError("Date must look like 2026-11-09")
        return v


class EntryPatch(BaseModel):
    title: Optional[str] = Field(default=None, max_length=200)
    score: Optional[float] = Field(default=None, ge=0, le=100000)
    total: Optional[float] = Field(default=None, gt=0, le=100000)
    category_id: Optional[str] = Field(default=None, max_length=64)
    date: Optional[str] = None

    @field_validator("title")
    @classmethod
    def _n(cls, v):
        return None if v is None else _name(v)

    @field_validator("date")
    @classmethod
    def _d(cls, v):
        if v is None:
            return v
        v = v.strip()
        if v and not DATE_RE.match(v):
            raise ValueError("Date must look like 2026-11-09")
        return v


def _settings(db: Session, user: models.User) -> Optional[models.GradeSettings]:
    return db.query(models.GradeSettings).filter(models.GradeSettings.user_id == user.id).first()


def _table(settings: Optional[models.GradeSettings]):
    if not settings:
        return None
    if settings.table_json:
        try:
            return json.loads(settings.table_json)
        except ValueError:
            pass
    return grades.default_table(settings.scale)


def _owned_subject(db: Session, user: models.User, subject_id: str) -> models.GradeSubject:
    s = db.query(models.GradeSubject).filter(models.GradeSubject.id == subject_id, models.GradeSubject.owner_id == user.id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Subject not found")
    return s


def _check_folder(db: Session, user: models.User, folder_id: Optional[str]) -> Optional[str]:
    if not folder_id:
        return None
    ok = db.query(models.Folder.id).filter(models.Folder.id == folder_id, models.Folder.owner_id == user.id).first()
    if not ok:
        raise HTTPException(status_code=404, detail="Folder not found")
    return folder_id


def _entry_dict(e: models.GradeEntry) -> dict:
    return {"id": e.id, "title": e.title, "score": e.score, "total": e.total, "category_id": e.category_id, "date": e.date or ""}


def _subject_view(s: models.GradeSubject, scale: Optional[str], table) -> dict:
    cats = [{"id": c.id, "name": c.name, "weight": c.weight} for c in s.categories]
    ents = [_entry_dict(e) for e in s.entries]
    computed = grades.current_percent(cats, ents)
    percent = s.final_percent if s.final_percent is not None else computed
    return {
        "id": s.id,
        "name": s.name,
        "units": s.units,
        "folder_id": s.folder_id,
        "percent": percent,
        "grade": grades.percent_to_grade(table, percent, scale) if scale else None,
        "has_final_override": s.final_percent is not None,
        "categories": grades.category_stats(cats, ents),
        "entries": ents,
    }


def snapshot(db: Session, user: models.User) -> dict:
    st = _settings(db, user)
    scale = st.scale if st else None
    table = _table(st)
    subs = (
        db.query(models.GradeSubject)
        .options(selectinload(models.GradeSubject.categories), selectinload(models.GradeSubject.entries))
        .filter(models.GradeSubject.owner_id == user.id)
        .order_by(models.GradeSubject.created_at.asc())
        .all()
    )
    views = [_subject_view(s, scale, table) for s in subs]
    return {
        "settings": {
            "scale": scale,
            "passing_percent": st.passing_percent if st else None,
            "table": table,
        },
        "subjects": views,
        "overall": grades.overall(views, scale, table) if scale else {"percent": None, "grade": None},
    }


def build_router() -> APIRouter:
    router = APIRouter(prefix="/grades")

    @router.get("")
    def get_grades(user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
        return snapshot(db, user)

    @router.put("/settings")
    def put_settings(payload: SettingsIn, user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
        try:
            table = grades.validate_table(payload.table, payload.scale) if payload.table else None
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        st = _settings(db, user)
        if not st:
            st = models.GradeSettings(user_id=user.id, scale=payload.scale)
            db.add(st)
        elif st.scale != payload.scale and payload.table is None:
            st.table_json = None  # a new scale starts from its own default table
        st.scale = payload.scale
        st.passing_percent = payload.passing_percent if payload.passing_percent is not None else grades.DEFAULT_PASSING[payload.scale]
        if table is not None:
            st.table_json = json.dumps(table)
        db.commit()
        return snapshot(db, user)

    # ----- subjects -----

    @router.post("/subjects", status_code=status.HTTP_201_CREATED)
    def add_subject(payload: SubjectIn, user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
        count = db.query(models.GradeSubject).filter(models.GradeSubject.owner_id == user.id).count()
        if count >= MAX_SUBJECTS:
            raise HTTPException(status_code=400, detail=f"You can track up to {MAX_SUBJECTS} subjects")
        s = models.GradeSubject(owner_id=user.id, name=payload.name, units=payload.units, folder_id=_check_folder(db, user, payload.folder_id))
        db.add(s)
        db.commit()
        return snapshot(db, user)

    @router.patch("/subjects/{subject_id}")
    def patch_subject(subject_id: str, payload: SubjectPatch, user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
        s = _owned_subject(db, user, subject_id)
        sent = payload.model_fields_set
        if "name" in sent and payload.name is not None:
            s.name = payload.name
        if "units" in sent and payload.units is not None:
            s.units = payload.units
        if "folder_id" in sent:
            s.folder_id = _check_folder(db, user, payload.folder_id)
        if "final_grade" in sent:
            if payload.final_grade is None:
                s.final_percent = None
            else:
                st = _settings(db, user)
                if not st:
                    raise HTTPException(status_code=400, detail="Choose a grading scale first")
                s.final_percent = grades.grade_to_percent(_table(st), payload.final_grade, st.scale)
        db.commit()
        return snapshot(db, user)

    @router.delete("/subjects/{subject_id}")
    def delete_subject(subject_id: str, user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
        db.delete(_owned_subject(db, user, subject_id))
        db.commit()
        return snapshot(db, user)

    # ----- categories -----

    @router.post("/subjects/{subject_id}/categories", status_code=status.HTTP_201_CREATED)
    def add_category(subject_id: str, payload: CategoryIn, user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
        s = _owned_subject(db, user, subject_id)
        if len(s.categories) >= MAX_CATEGORIES:
            raise HTTPException(status_code=400, detail=f"A subject can have up to {MAX_CATEGORIES} categories")
        db.add(models.GradeCategory(subject_id=s.id, name=payload.name, weight=payload.weight))
        db.commit()
        return snapshot(db, user)

    def _owned_category(db, user, category_id):
        c = (
            db.query(models.GradeCategory)
            .join(models.GradeSubject, models.GradeCategory.subject_id == models.GradeSubject.id)
            .filter(models.GradeCategory.id == category_id, models.GradeSubject.owner_id == user.id)
            .first()
        )
        if not c:
            raise HTTPException(status_code=404, detail="Category not found")
        return c

    @router.patch("/categories/{category_id}")
    def patch_category(category_id: str, payload: CategoryPatch, user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
        c = _owned_category(db, user, category_id)
        for field, value in payload.model_dump(exclude_unset=True, exclude_none=True).items():
            setattr(c, field, value)
        db.commit()
        return snapshot(db, user)

    @router.delete("/categories/{category_id}")
    def delete_category(category_id: str, user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
        c = _owned_category(db, user, category_id)
        db.query(models.GradeEntry).filter(models.GradeEntry.category_id == c.id).update({"category_id": None}, synchronize_session=False)
        db.delete(c)
        db.commit()
        return snapshot(db, user)

    # ----- entries -----

    def _check_category(db, subject: models.GradeSubject, category_id: Optional[str]):
        if category_id and category_id not in {c.id for c in subject.categories}:
            raise HTTPException(status_code=404, detail="Category not found")
        return category_id or None

    @router.post("/subjects/{subject_id}/entries", status_code=status.HTTP_201_CREATED)
    def add_entry(subject_id: str, payload: EntryIn, user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
        s = _owned_subject(db, user, subject_id)
        if len(s.entries) >= MAX_ENTRIES:
            raise HTTPException(status_code=400, detail=f"A subject can have up to {MAX_ENTRIES} scores")
        if payload.score > payload.total * 2:
            raise HTTPException(status_code=422, detail="That score is far above the total — check the numbers")
        db.add(models.GradeEntry(
            subject_id=s.id, title=payload.title, score=payload.score, total=payload.total,
            category_id=_check_category(db, s, payload.category_id), date=payload.date,
        ))
        db.commit()
        return snapshot(db, user)

    def _owned_entry(db, user, entry_id):
        e = (
            db.query(models.GradeEntry)
            .join(models.GradeSubject, models.GradeEntry.subject_id == models.GradeSubject.id)
            .filter(models.GradeEntry.id == entry_id, models.GradeSubject.owner_id == user.id)
            .first()
        )
        if not e:
            raise HTTPException(status_code=404, detail="Score not found")
        return e

    @router.patch("/entries/{entry_id}")
    def patch_entry(entry_id: str, payload: EntryPatch, user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
        e = _owned_entry(db, user, entry_id)
        sent = payload.model_fields_set
        for field in ("title", "score", "total", "date"):
            if field in sent and getattr(payload, field) is not None:
                setattr(e, field, getattr(payload, field))
        if "category_id" in sent:
            e.category_id = _check_category(db, e.subject, payload.category_id)
        if e.score > e.total * 2:
            raise HTTPException(status_code=422, detail="That score is far above the total — check the numbers")
        db.commit()
        return snapshot(db, user)

    @router.delete("/entries/{entry_id}")
    def delete_entry(entry_id: str, user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
        db.delete(_owned_entry(db, user, entry_id))
        db.commit()
        return snapshot(db, user)

    # ----- "what do I need?" -----

    @router.get("/subjects/{subject_id}/needed")
    def needed(
        subject_id: str,
        target_grade: float = Query(ge=0, le=100),
        category_id: Optional[str] = Query(default=None, max_length=64),
        points: Optional[float] = Query(default=None, gt=0, le=100000),
        user: models.User = Depends(auth.get_current_user),
        db: Session = Depends(get_db),
    ):
        st = _settings(db, user)
        if not st:
            raise HTTPException(status_code=400, detail="Choose a grading scale first")
        s = _owned_subject(db, user, subject_id)
        table = _table(st)
        target_percent = grades.grade_to_percent(table, target_grade, st.scale)
        cats = [{"id": c.id, "name": c.name, "weight": c.weight} for c in s.categories]
        res = grades.needed_for_target(cats, [_entry_dict(e) for e in s.entries], target_percent, category_id, points)
        if res is None:
            raise HTTPException(status_code=422, detail="Pick the category that's still to come (or enter the points of the next assessment)")
        return {
            **res,
            "target_percent": target_percent,
            "needed_grade": grades.percent_to_grade(table, res["needed_percent"], st.scale),
        }

    return router


def erase_grades(db: Session, user_id: str) -> None:
    sub_ids = [r[0] for r in db.query(models.GradeSubject.id).filter(models.GradeSubject.owner_id == user_id).all()]
    if sub_ids:
        db.query(models.GradeEntry).filter(models.GradeEntry.subject_id.in_(sub_ids)).delete(synchronize_session=False)
        db.query(models.GradeCategory).filter(models.GradeCategory.subject_id.in_(sub_ids)).delete(synchronize_session=False)
        db.query(models.GradeSubject).filter(models.GradeSubject.id.in_(sub_ids)).delete(synchronize_session=False)
    db.query(models.GradeSettings).filter(models.GradeSettings.user_id == user_id).delete(synchronize_session=False)


def export_grades(db: Session, user: models.User) -> dict:
    snap = snapshot(db, user)
    return {
        "scale": snap["settings"]["scale"],
        "passing_percent": snap["settings"]["passing_percent"],
        "subjects": [
            {
                "name": s["name"], "units": s["units"],
                "categories": [{"name": c["name"], "weight": c["weight"]} for c in s["categories"]],
                "scores": [{"title": e["title"], "score": e["score"], "total": e["total"], "date": e["date"]} for e in s["entries"]],
            }
            for s in snap["subjects"]
        ],
    }
