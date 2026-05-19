"""Persistence layer for WebPilot.

SQLModel-backed SQLite store for briefs, events, and sources, plus filesystem
I/O for markdown reports.
"""
from __future__ import annotations

import json
import os
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterator, Optional

from sqlalchemy.engine import Engine
from sqlmodel import Field, Session, SQLModel, create_engine, select


# --- Models -----------------------------------------------------------------


class Brief(SQLModel, table=True):
    __tablename__ = "brief"

    id: str = Field(primary_key=True)
    prompt: str
    status: str = "queued"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    report_path: Optional[str] = None
    input_tokens: int = 0
    output_tokens: int = 0
    tool_calls: int = 0


class Event(SQLModel, table=True):
    __tablename__ = "event"

    id: Optional[int] = Field(default=None, primary_key=True)
    brief_id: str = Field(index=True)
    kind: str
    payload: str
    ts: datetime = Field(default_factory=datetime.utcnow)


class Source(SQLModel, table=True):
    __tablename__ = "source"

    id: Optional[int] = Field(default=None, primary_key=True)
    brief_id: str = Field(index=True)
    url: str
    title: str
    claim: str
    ts: datetime = Field(default_factory=datetime.utcnow)


# --- Engine / sessions ------------------------------------------------------


engine: Optional[Engine] = None


def init_db(path: str | None = None) -> Engine:
    """Create (or reset) the module-level engine and ensure tables exist.

    `path` may be a filesystem path or ``":memory:"``. If ``None``, reads
    ``WEBPILOT_DB_PATH`` env or defaults to ``data/webpilot.db``.
    """
    global engine

    if path is None:
        path = os.environ.get("WEBPILOT_DB_PATH", "data/webpilot.db")

    if path == ":memory:":
        url = "sqlite://"
        # In-memory: use a single shared connection so tables persist across sessions.
        from sqlalchemy.pool import StaticPool

        engine = create_engine(
            url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    else:
        db_path = Path(path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        url = f"sqlite:///{db_path}"
        engine = create_engine(url, connect_args={"check_same_thread": False})

    SQLModel.metadata.create_all(engine)
    return engine


def _get_engine() -> Engine:
    if engine is None:
        init_db()
    assert engine is not None
    return engine


@contextmanager
def session_scope() -> Iterator[Session]:
    """Yield a Session, commit on success, rollback on exception, always close."""
    session = Session(_get_engine(), expire_on_commit=False)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# --- Brief CRUD -------------------------------------------------------------


def create_brief(prompt: str) -> Brief:
    now = datetime.utcnow()
    brief = Brief(
        id=uuid.uuid4().hex,
        prompt=prompt,
        status="queued",
        created_at=now,
        updated_at=now,
    )
    with session_scope() as s:
        s.add(brief)
        s.commit()
        s.refresh(brief)
    return brief


def update_brief(id: str, **fields) -> Brief:
    with session_scope() as s:
        brief = s.get(Brief, id)
        if brief is None:
            raise KeyError(f"brief not found: {id}")
        for k, v in fields.items():
            setattr(brief, k, v)
        brief.updated_at = datetime.utcnow()
        s.add(brief)
        s.commit()
        s.refresh(brief)
    return brief


def get_brief(id: str) -> Brief | None:
    with session_scope() as s:
        brief = s.get(Brief, id)
        if brief is not None:
            s.refresh(brief)
        return brief


def list_briefs(limit: int = 20) -> list[Brief]:
    with session_scope() as s:
        stmt = select(Brief).order_by(Brief.created_at.desc()).limit(limit)
        return list(s.exec(stmt).all())


# --- Events -----------------------------------------------------------------


def append_event(brief_id: str, kind: str, payload: dict) -> Event:
    evt = Event(
        brief_id=brief_id,
        kind=kind,
        payload=json.dumps(payload),
        ts=datetime.utcnow(),
    )
    with session_scope() as s:
        s.add(evt)
        s.commit()
        s.refresh(evt)
    return evt


def list_events(brief_id: str, after_id: int | None = None) -> list[Event]:
    with session_scope() as s:
        stmt = select(Event).where(Event.brief_id == brief_id)
        if after_id is not None:
            stmt = stmt.where(Event.id > after_id)
        stmt = stmt.order_by(Event.id)
        return list(s.exec(stmt).all())


# --- Sources ----------------------------------------------------------------


def add_source(brief_id: str, url: str, title: str, claim: str) -> Source:
    src = Source(
        brief_id=brief_id,
        url=url,
        title=title,
        claim=claim,
        ts=datetime.utcnow(),
    )
    with session_scope() as s:
        s.add(src)
        s.commit()
        s.refresh(src)
    return src


def list_sources(brief_id: str) -> list[Source]:
    with session_scope() as s:
        stmt = select(Source).where(Source.brief_id == brief_id).order_by(Source.id)
        return list(s.exec(stmt).all())


# --- Reports ----------------------------------------------------------------


def save_report(brief_id: str, markdown: str) -> Path:
    """Write the markdown report to disk and set ``brief.report_path``.

    Honors ``WEBPILOT_REPORTS_DIR`` env (default ``data/reports``).
    """
    reports_dir = Path(os.environ.get("WEBPILOT_REPORTS_DIR", "data/reports"))
    reports_dir.mkdir(parents=True, exist_ok=True)
    path = reports_dir / f"{brief_id}.md"
    path.write_text(markdown, encoding="utf-8")

    with session_scope() as s:
        brief = s.get(Brief, brief_id)
        if brief is not None:
            brief.report_path = str(path)
            brief.updated_at = datetime.utcnow()
            s.add(brief)
            s.commit()

    return path
