import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./orbit.db")

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

is_sqlite = DATABASE_URL.startswith("sqlite")
connect_args = {"check_same_thread": False} if is_sqlite else {}

engine_kwargs = {"connect_args": connect_args}
if not is_sqlite:
    # pool_pre_ping issues a lightweight check on every checkout and
    # transparently replaces dead connections. This is the actual fix:
    # Neon (free tier) suspends idle compute and Render (free tier)
    # sleeps the container; both silently close server-side connections
    # that SQLAlchemy would otherwise hand out as if they were live.
    engine_kwargs["pool_pre_ping"] = True
    # Belt-and-braces: recycle before Neon's ~5 min idle cutoff so most
    # checkouts never hit a stale connection in the first place.
    engine_kwargs["pool_recycle"] = 300

engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()