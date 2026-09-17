import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from database import Base


def gen_id() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=gen_id)
    # The actual login identifier now — always required, unique, lowercase.
    username = Column(String, unique=True, nullable=False, index=True)
    # Display name; defaults to the username at signup if not given, so
    # frontend code can always assume it's populated.
    name = Column(String, nullable=True)
    # No longer required at signup — can be added later from Profile
    # settings. Nullable + unique is fine in Postgres/SQLite: multiple NULLs
    # don't violate a unique constraint.
    email = Column(String, unique=True, nullable=True, index=True)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Email verification — only meaningful once an email is actually linked.
    is_verified = Column(Boolean, default=False)
    verification_token = Column(String, nullable=True)
    verification_expires = Column(DateTime, nullable=True)

    # Password reset
    reset_token = Column(String, nullable=True)
    reset_expires = Column(DateTime, nullable=True)

    # Bumped whenever the password changes; any JWT issued before this
    # timestamp is treated as invalid, even if it hasn't technically
    # expired yet — otherwise a stolen token would keep working after
    # the person "secures" their account by resetting the password.
    sessions_invalidated_at = Column(DateTime, nullable=True)

    # Account lockout after repeated failed logins
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)

    folders = relationship("Folder", back_populates="owner", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="owner", cascade="all, delete-orphan")
    reminders = relationship("Reminder", back_populates="owner", cascade="all, delete-orphan")


class RevokedToken(Base):
    """
    JWTs are stateless by design, so logging out can't normally invalidate a
    token early — this table is the exception list. On logout we record the
    token's jti here; get_current_user checks it on every request. Rows can
    be purged once expires_at is in the past (no cleanup job included here).
    """
    __tablename__ = "revoked_tokens"

    jti = Column(String, primary_key=True)
    expires_at = Column(DateTime, nullable=False)


class Folder(Base):
    __tablename__ = "folders"

    id = Column(String, primary_key=True, default=gen_id)
    name = Column(String, nullable=False)
    color = Column(String, default="#5B3FE0")
    owner_id = Column(String, ForeignKey("users.id"), nullable=False)

    owner = relationship("User", back_populates="folders")
    items = relationship("Item", back_populates="folder", cascade="all, delete-orphan")


class Item(Base):
    __tablename__ = "items"

    id = Column(String, primary_key=True, default=gen_id)
    title = Column(String, nullable=False)
    summary = Column(Text, default="")
    tags = Column(String, default="")  # comma-separated
    folder_id = Column(String, ForeignKey("folders.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    folder = relationship("Folder", back_populates="items")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(String, primary_key=True, default=gen_id)
    text = Column(String, nullable=False)
    priority = Column(String, default="Medium")  # Low | Medium | High
    done = Column(Boolean, default=False)
    due_date = Column(String, default="")
    owner_id = Column(String, ForeignKey("users.id"), nullable=False)

    owner = relationship("User", back_populates="tasks")


class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(String, primary_key=True, default=gen_id)
    title = Column(String, nullable=False)
    detail = Column(String, default="")
    kind = Column(String, default="time")  # time | location | inactivity
    owner_id = Column(String, ForeignKey("users.id"), nullable=False)

    owner = relationship("User", back_populates="reminders")


class GroupMessage(Base):
    __tablename__ = "group_messages"

    id = Column(String, primary_key=True, default=gen_id)
    group_id = Column(String, nullable=False, index=True)
    sender_name = Column(String, nullable=False)
    text = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
