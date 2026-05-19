"""Tests for webpilot.store — SQLModel persistence layer."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest
from sqlmodel import Session, select

from webpilot import store
from webpilot.store import (
    Brief,
    Event,
    Source,
    add_source,
    append_event,
    create_brief,
    get_brief,
    init_db,
    list_briefs,
    list_events,
    list_sources,
    save_report,
    session_scope,
    update_brief,
)


@pytest.fixture(autouse=True)
def _db():
    """Fresh in-memory DB for every test."""
    engine = init_db(":memory:")
    yield engine
    store.engine = None


def test_init_db_creates_tables():
    # All three tables should exist; querying them should not error.
    with session_scope() as s:
        assert s.exec(select(Brief)).all() == []
        assert s.exec(select(Event)).all() == []
        assert s.exec(select(Source)).all() == []


def test_create_brief_returns_brief_with_id_status_timestamps():
    brief = create_brief("research foo")
    assert isinstance(brief.id, str)
    assert len(brief.id) == 32  # uuid4 hex
    assert brief.prompt == "research foo"
    assert brief.status == "queued"
    assert isinstance(brief.created_at, datetime)
    assert isinstance(brief.updated_at, datetime)
    assert brief.report_path is None


def test_update_brief_persists_and_returns_updated():
    brief = create_brief("hello")
    updated = update_brief(brief.id, status="running")
    assert updated.status == "running"

    again = get_brief(brief.id)
    assert again is not None
    assert again.status == "running"


def test_get_brief_returns_none_for_missing():
    assert get_brief("does-not-exist") is None


def test_list_briefs_most_recent_first():
    b1 = create_brief("first")
    b2 = create_brief("second")
    b3 = create_brief("third")
    result = list_briefs(limit=10)
    ids = [b.id for b in result]
    assert ids == [b3.id, b2.id, b1.id]


def test_list_briefs_respects_limit():
    for i in range(5):
        create_brief(f"b{i}")
    result = list_briefs(limit=2)
    assert len(result) == 2


def test_append_event_writes_event_with_auto_id_and_ts():
    brief = create_brief("p")
    evt = append_event(brief.id, "status", {"value": "running"})
    assert isinstance(evt.id, int)
    assert evt.brief_id == brief.id
    assert evt.kind == "status"
    assert json.loads(evt.payload) == {"value": "running"}
    assert isinstance(evt.ts, datetime)


def test_list_events_id_order():
    brief = create_brief("p")
    e1 = append_event(brief.id, "a", {"i": 1})
    e2 = append_event(brief.id, "b", {"i": 2})
    e3 = append_event(brief.id, "c", {"i": 3})
    result = list_events(brief.id)
    assert [e.id for e in result] == [e1.id, e2.id, e3.id]


def test_list_events_after_id_filters():
    brief = create_brief("p")
    e1 = append_event(brief.id, "a", {})
    e2 = append_event(brief.id, "b", {})
    e3 = append_event(brief.id, "c", {})
    result = list_events(brief.id, after_id=e1.id)
    assert [e.id for e in result] == [e2.id, e3.id]


def test_list_events_isolates_by_brief():
    b1 = create_brief("one")
    b2 = create_brief("two")
    append_event(b1.id, "x", {})
    append_event(b2.id, "y", {})
    assert len(list_events(b1.id)) == 1
    assert len(list_events(b2.id)) == 1


def test_add_source_and_list_sources():
    brief = create_brief("p")
    s1 = add_source(brief.id, "https://a.com", "A", "claim a")
    s2 = add_source(brief.id, "https://b.com", "B", "claim b")
    assert isinstance(s1.id, int)
    sources = list_sources(brief.id)
    assert [s.id for s in sources] == [s1.id, s2.id]
    assert sources[0].url == "https://a.com"
    assert sources[0].title == "A"
    assert sources[0].claim == "claim a"


def test_save_report_writes_file_and_updates_brief(tmp_path, monkeypatch):
    monkeypatch.setenv("WEBPILOT_REPORTS_DIR", str(tmp_path))
    brief = create_brief("p")
    path = save_report(brief.id, "# Hello\n\nbody")
    assert isinstance(path, Path)
    assert path.exists()
    assert path.read_text(encoding="utf-8") == "# Hello\n\nbody"
    assert path.parent == tmp_path
    assert path.name == f"{brief.id}.md"

    updated = get_brief(brief.id)
    assert updated is not None
    assert updated.report_path == str(path)
