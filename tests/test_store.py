import pytest


from webpilot.store import Session, Brief, Event, Source

def test_brief_creation():
    session = Session()
    brief = Brief(brief_text="Test brief")
    session.add(brief)
    session.commit()

    assert brief.id is not None
    assert brief.created_at is not None

def test_event_append_and_list():
    session = Session()
    brief = Brief(brief_text="Test brief for events")
    session.add(brief)
    session.commit()

    event1 = Event(brief_id=brief.id, event_type="test_event", event_data="data1")
    event2 = Event(brief_id=brief.id, event_type="test_event", event_data="data2")
    session.add_all([event1, event2])
    session.commit()

    events = session.query(Event).filter_by(brief_id=brief.id).order_by(Event.id).all()
    assert len(events) == 2
    assert events[0].event_data == "data1"
    assert events[1].event_data == "data2"


def test_source_add_and_list():
    session = Session()
    brief = Brief(brief_text="Test brief for sources")
    session.add(brief)
    session.commit()

    source1 = Source(brief_id=brief.id, source_text="Source 1")
    source2 = Source(brief_id=brief.id, source_text="Source 2")
    session.add_all([source1, source2])
    session.commit()

    sources = session.query(Source).filter_by(brief_id=brief.id).order_by(Source.id).all()
    assert len(sources) == 2
    assert sources[0].source_text == "Source 1"
    assert sources[1].source_text == "Source 2"

def test_brief_update():
    session = Session()
    brief = Brief(brief_text="Test brief for update")
    session.add(brief)
    session.commit()

    brief.result = "Updated result"
    session.commit()

    updated_brief = session.query(Brief).filter_by(id=brief.id).first()
    assert updated_brief.result == "Updated result"


def test_brief_report_path_update():
    session = Session()
    brief = Brief(brief_text="Test brief for report path")
    session.add(brief)
    session.commit()

    brief.result = "Report path updated"
    session.commit()

    updated_brief = session.query(Brief).filter_by(id=brief.id).first()
    assert updated_brief.result == "Report path updated"

def append_event(brief_id, event_type, event_data):
    session = Session()
    event = Event(brief_id=brief_id, event_type=event_type, event_data=event_data)
    session.add(event)
    session.commit()
    return event

def add_source(brief_id, source_text):
    session = Session()
    source = Source(brief_id=brief_id, source_text=source_text)
    session.add(source)
    session.commit()
    return source


def list_sources(brief_id):
    session = Session()
    sources = session.query(Source).filter_by(brief_id=brief_id).order_by(Source.id).all()
    return sources

def save_report(brief_id, markdown):
    session = Session()
    brief = session.query(Brief).filter_by(id=brief_id).first()
    if brief:
        brief.result = markdown
        session.commit()
        return True
    return False
