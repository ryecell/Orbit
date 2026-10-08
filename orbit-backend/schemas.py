from datetime import datetime
from typing import List, Literal, Optional
import re

from pydantic import BaseModel, EmailStr, Field, field_validator


# ---------- Auth ----------

USERNAME_PATTERN = re.compile(r"^[a-z0-9_.-]+$")


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=30)
    password: str = Field(min_length=8)
    name: Optional[str] = None
    email: Optional[EmailStr] = None  # optional at signup — can be linked later from Profile
    accept_terms: bool = False

    @field_validator("username")
    @classmethod
    def username_format(cls, v: str) -> str:
        v = v.strip().lower()
        if not USERNAME_PATTERN.match(v):
            raise ValueError("Username can only contain lowercase letters, numbers, underscores, periods, and hyphens")
        return v

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not any(c.isalpha() for c in v) or not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one letter and one number")
        return v

    @field_validator("accept_terms")
    @classmethod
    def must_accept_terms(cls, v: bool) -> bool:
        if not v:
            raise ValueError("You must agree to the Terms of Service and Privacy Policy to create an account")
        return v


class UserLogin(BaseModel):
    username: str
    password: str


class ForgotPasswordRequest(BaseModel):
    # Username, not email — email may not exist for this account at all.
    username: str


class LinkEmailRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8)

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not any(c.isalpha() for c in v) or not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one letter and one number")
        return v


class DeleteAccountRequest(BaseModel):
    # Re-entered on purpose: a stolen/left-open session alone shouldn't be able
    # to erase an account. No strength rules here — it's checked against the hash.
    password: str


class UserOut(BaseModel):
    id: str
    username: str
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    is_verified: bool

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------- Folders & Items ----------

class ItemOut(BaseModel):
    id: str
    title: str
    summary: str
    tags: List[str]
    created_at: datetime

    class Config:
        from_attributes = True


class ItemCreate(BaseModel):
    title: str
    summary: str = ""
    tags: List[str] = []


# Keep in sync with FOLDER_ICONS in the frontend's App.jsx.
FOLDER_ICON_KEYS = {
    "folder", "leaf", "sigma", "atom", "users", "wrench", "user", "file", "star", "sparkles",
    "book", "flask", "code", "calculator", "lightbulb", "graduation", "globe", "palette",
    "music", "heart", "briefcase",
}
HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")


def _clean_folder_name(v: str) -> str:
    v = " ".join(v.split())  # trims and collapses runs of whitespace/newlines
    if not v:
        raise ValueError("Folder name can't be empty")
    return v


def _check_color(v: str) -> str:
    if not HEX_COLOR.match(v):
        raise ValueError("Color must look like #00674F")
    return v


def _check_icon(v: str) -> str:
    if v not in FOLDER_ICON_KEYS:
        raise ValueError("Unknown folder icon")
    return v


class FolderCreate(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    color: str = "#00674F"
    icon: Optional[str] = None

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        return _clean_folder_name(v)

    @field_validator("color")
    @classmethod
    def _color(cls, v: str) -> str:
        return _check_color(v)

    @field_validator("icon")
    @classmethod
    def _icon(cls, v: Optional[str]) -> Optional[str]:
        return None if v is None else _check_icon(v)


class FolderUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=40)
    color: Optional[str] = None
    icon: Optional[str] = None

    @field_validator("name")
    @classmethod
    def _name(cls, v: Optional[str]) -> Optional[str]:
        return None if v is None else _clean_folder_name(v)

    @field_validator("color")
    @classmethod
    def _color(cls, v: Optional[str]) -> Optional[str]:
        return None if v is None else _check_color(v)

    @field_validator("icon")
    @classmethod
    def _icon(cls, v: Optional[str]) -> Optional[str]:
        return None if v is None else _check_icon(v)


class FolderReorder(BaseModel):
    ids: List[str] = Field(min_length=1, max_length=200)


class FolderOut(BaseModel):
    id: str
    name: str
    color: str
    icon: Optional[str] = None
    position: int = 0
    items: List[ItemOut] = []

    class Config:
        from_attributes = True


# ---------- Tasks ----------

Priority = Literal["Low", "Medium", "High"]


class TaskCreate(BaseModel):
    text: str
    priority: Priority = "Medium"
    due_date: str = ""


class TaskUpdate(BaseModel):
    text: Optional[str] = None
    priority: Optional[Priority] = None
    done: Optional[bool] = None
    due_date: Optional[str] = None


class TaskOut(BaseModel):
    id: str
    text: str
    priority: str
    done: bool
    due_date: str

    class Config:
        from_attributes = True


# ---------- Reminders ----------

class ReminderCreate(BaseModel):
    title: str
    detail: str = ""
    kind: str = "time"


class ReminderOut(BaseModel):
    id: str
    title: str
    detail: str
    kind: str

    class Config:
        from_attributes = True


# ---------- Calendar events ----------

class EventCreate(BaseModel):
    title: str
    description: str = ""
    start_time: datetime
    end_time: Optional[datetime] = None
    color: str = "#5B3FE0"


class EventUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    color: Optional[str] = None


class EventOut(BaseModel):
    id: str
    title: str
    description: str
    start_time: datetime
    end_time: Optional[datetime] = None
    color: str

    class Config:
        from_attributes = True


# ---------- Study sessions (Insights) ----------

def _clean_session_title(v: Optional[str]) -> str:
    return " ".join((v or "").split())[:60]  # trims, collapses whitespace, caps length


class StudySessionCreate(BaseModel):
    minutes: int = Field(gt=0, le=24 * 60)  # a single logged session can't exceed a full day
    title: str = ""
    note: str = ""
    started_at: Optional[datetime] = None  # defaults to now if omitted

    @field_validator("title")
    @classmethod
    def _title(cls, v: str) -> str:
        return _clean_session_title(v)


class StudySessionUpdate(BaseModel):
    title: str = ""

    @field_validator("title")
    @classmethod
    def _title(cls, v: str) -> str:
        return _clean_session_title(v)


class StudySessionOut(BaseModel):
    id: str
    minutes: int
    title: Optional[str] = None  # NULL for sessions logged before titles existed
    note: str
    started_at: datetime

    class Config:
        from_attributes = True


# ---------- Groups ----------

class GroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=60)


class JoinGroupRequest(BaseModel):
    invite_code: str


class GroupOut(BaseModel):
    id: str
    name: str
    invite_code: str
    member_count: int = 0

    class Config:
        from_attributes = True


# ---------- Group chat ----------

class MessageCreate(BaseModel):
    text: str  # sender_name is never trusted from the client — derived from the authenticated user


class MessageOut(BaseModel):
    id: str
    sender_id: Optional[str] = None  # NULL for old messages / deleted senders
    sender_name: str
    text: str
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- AI tagging ----------

class AnalyzeRequest(BaseModel):
    image_base64: str
    media_type: str = "image/jpeg"
    candidate_folders: List[str] = []


class AnalyzeResponse(BaseModel):
    title: str
    folder: str
    tags: List[str]
    summary: str
