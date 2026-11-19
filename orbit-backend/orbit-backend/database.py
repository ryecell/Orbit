import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Local dev: SQLite file, zero setup required.
# Production: set DATABASE_URL to a real Postgres instance — SQLite's
# single-file storage gets wiped on every deploy/restart on most hosting
# platforms, so it's not viable once real user data is at stake.
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./orbit.db")

# Some platforms (Render, Heroku) hand out "postgres://" URLs, but
# SQLAlchemy + psycopg2 expect "postgresql://".
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# SQLite needs this flag for use with FastAPI's threaded request handling;
# Postgres doesn't use or accept it.
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
