from datetime import datetime
from typing import List, Optional
import re

from pydantic import BaseModel, EmailStr, Field, field_validator


# ---------- Auth ----------

USERNAME_PATTERN = re.compile(r"^[a-z0-9_.-]+$")


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=30)
    password: str = Field(min_length=8)
    name: Optional[str] = None
    email: Optional[EmailStr] = None  # optional at signup — can be linked later from Profile

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


class FolderCreate(BaseModel):
    name: str
    color: str = "#5B3FE0"


class FolderOut(BaseModel):
    id: str
    name: str
    color: str
    items: List[ItemOut] = []

    class Config:
        from_attributes = True


# ---------- Tasks ----------

class TaskCreate(BaseModel):
    text: str
    priority: str = "Medium"
    due_date: str = ""


class TaskUpdate(BaseModel):
    text: Optional[str] = None
    priority: Optional[str] = None
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


# ---------- Group chat ----------

class MessageCreate(BaseModel):
    sender_name: str
    text: str


class MessageOut(BaseModel):
    id: str
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
