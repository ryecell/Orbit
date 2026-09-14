from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


# ---------- Auth ----------

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str = Field(min_length=8)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not any(c.isalpha() for c in v) or not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one letter and one number")
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class ForgotPasswordRequest(BaseModel):
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
    name: str
    email: EmailStr
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
