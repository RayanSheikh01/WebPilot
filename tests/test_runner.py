"""End-to-end runner test using FakeAnthropic + the static_site fixture."""

from dataclasses import dataclass

import pytest

from webpilot.agent.runner import run_brief_local
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
