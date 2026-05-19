"""End-to-end runner test using FakeAnthropic + the static_site fixture."""

import asyncio
from dataclasses import dataclass

import pytest

from webpilot import store as store_module
from webpilot.agent.runner import run_brief, run_brief_local
from webpilot.events import EventBus
from tests.test_planner_loop import FakeAnthropic, _Response, _Usage, _tool_use


@pytest.mark.asyncio
async def test_run_brief_local_produces_report_with_sources(static_site, tmp_path):
    page_url = static_site + "/index.html"
    fake = FakeAnthropic(
        [
            _Response(
                content=[_tool_use("browser_goto", {"url": page_url}, "u1")],
                usage=_Usage(50, 10),
            ),
            _Response(
                content=[
                    _tool_use(
                        "cite",
                        {"url": page_url, "title": "Index", "claim": "Static fixture page"},
                        "u2",
                    )
                ],
                usage=_Usage(20, 5),
            ),
            _Response(
                content=[_tool_use("finish", {"summary": "looked at the fixture"}, "u3")],
                usage=_Usage(10, 5),
            ),
        ]
    )

    report = await run_brief_local(
        "test brief",
        client=fake,
        screenshot_dir=tmp_path / "shots",
        headless=True,
    )

    assert report.startswith("# Research: test brief")
    assert "## Sources" in report
    assert page_url in report
    assert "looked at the fixture" in report


@pytest.mark.asyncio
async def test_run_brief_persists_events_and_publishes_to_bus(
    static_site, tmp_path, monkeypatch
):
    # Isolate DB + reports dir.
    monkeypatch.setenv("WEBPILOT_REPORTS_DIR", str(tmp_path / "reports"))
    store_module.init_db(":memory:")

    brief = store_module.create_brief("test brief")
    brief_id = brief.id

    page_url = static_site + "/index.html"
    fake = FakeAnthropic(
        [
            _Response(
                content=[_tool_use("browser_goto", {"url": page_url}, "u1")],
                usage=_Usage(50, 10),
            ),
            _Response(
                content=[
                    _tool_use(
                        "cite",
                        {"url": page_url, "title": "Index", "claim": "Static fixture page"},
                        "u2",
                    )
                ],
                usage=_Usage(20, 5),
            ),
            _Response(
                content=[_tool_use("finish", {"summary": "looked at the fixture"}, "u3")],
                usage=_Usage(10, 5),
            ),
        ]
    )

    bus = EventBus()
    collected: list = []

    async def collect():
        async for evt in bus.subscribe(brief_id):
            collected.append(evt)

    sub_task = asyncio.create_task(collect())
    # Yield so the subscriber registers before run_brief starts publishing.
    await asyncio.sleep(0)

    report = await run_brief(
        brief_id,
        "test brief",
        bus,
        store_module,
        client=fake,
        screenshot_dir=tmp_path / "shots",
        headless=True,
    )

    # bus.close() is in run_brief's finally; wait for subscriber to drain.
    await asyncio.wait_for(sub_task, timeout=2.0)

    assert "## Sources" in report
    assert page_url in report

    saved = store_module.get_brief(brief_id)
    assert saved.status == "done"
    assert saved.report_path is not None
    from pathlib import Path

    assert Path(saved.report_path).exists()

    events = store_module.list_events(brief_id)
    assert len(events) >= 3
    kinds = [e.kind for e in events]
    assert "status:running" in kinds
    assert "tool_call" in kinds
    assert "tool_result" in kinds
    assert "finish" in kinds

    assert len(collected) >= 1
