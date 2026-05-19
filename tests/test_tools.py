from webpilot.agent.tools import TOOL_SCHEMAS

EXPECTED_NAMES = {
    "web_search",
    "browser_goto",
    "browser_get_text",
    "browser_get_links",
    "browser_screenshot",
    "browser_back",
    "note",
    "cite",
    "finish",
}


def test_tool_schemas_count_and_names():
    assert len(TOOL_SCHEMAS) == 9
    assert {t["name"] for t in TOOL_SCHEMAS} == EXPECTED_NAMES


def test_each_schema_well_formed():
    for tool in TOOL_SCHEMAS:
        assert isinstance(tool["name"], str) and tool["name"]
        assert isinstance(tool["description"], str) and tool["description"]
        schema = tool["input_schema"]
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "required" in schema and isinstance(schema["required"], list)


def test_required_fields_appear_in_properties():
    for tool in TOOL_SCHEMAS:
        props = tool["input_schema"]["properties"]
        for req in tool["input_schema"]["required"]:
            assert req in props, f"{tool['name']}: required field {req!r} not in properties"


def test_no_mutating_browser_tools_exposed():
    forbidden = {"browser_click", "browser_fill", "browser_submit", "browser_eval"}
    names = {t["name"] for t in TOOL_SCHEMAS}
    assert names & forbidden == set()


import pytest

from dataclasses import dataclass

from webpilot.agent.guardrails import BudgetTracker
from webpilot.agent.search import SearchHit
from webpilot.agent.tools import ToolExecutor


@dataclass
class _Nav:
    final_url: str
    title: str
    status: int
    snippet: str


class _FakeBrowser:
    def __init__(self):
        self.calls = []

    async def goto(self, url):
        self.calls.append(("goto", url))
        return _Nav(final_url=url, title="t", status=200, snippet="snip")

    async def get_text(self, selector="body", max_chars=8000):
        return "page text"[:max_chars]

    async def get_links(self, selector="body"):
        return [{"text": "x", "href": "https://example.com/x"}]


class _FakeSearch:
    async def search(self, query, k=5):
        return [SearchHit(title="r", url="https://example.com", snippet="s")]


def _make_executor(tmp_path, **tracker_kwargs):
    tracker = BudgetTracker(**tracker_kwargs)
    return (
        ToolExecutor(
            browser=_FakeBrowser(),
            search=_FakeSearch(),
            tracker=tracker,
            screenshot_dir=tmp_path,
        ),
        tracker,
    )


@pytest.mark.asyncio
async def test_unknown_tool_returns_error(tmp_path):
    executor, _ = _make_executor(tmp_path)
    result = await executor.run("nonsense", {})
    assert result == {"error": "unknown_tool:nonsense"}


@pytest.mark.asyncio
async def test_budget_violation_blocks_dispatch(tmp_path):
    executor, tracker = _make_executor(tmp_path, max_tool_calls=0)
    tracker.record_tool_call()
    result = await executor.run("web_search", {"query": "x"})
    assert result == {"error": "budget_exceeded:tool_calls"}


@pytest.mark.asyncio
async def test_browser_goto_records_page(tmp_path):
    executor, tracker = _make_executor(tmp_path)
    result = await executor.run("browser_goto", {"url": "https://example.com/a"})
    assert result["final_url"] == "https://example.com/a"
    assert tracker.pages == 1
    assert tracker.tool_calls == 1


@pytest.mark.asyncio
async def test_note_and_cite_collected(tmp_path):
    executor, _ = _make_executor(tmp_path)
    await executor.run("note", {"text": "hello"})
    await executor.run(
        "cite", {"url": "https://x", "title": "T", "claim": "C"}
    )
    assert executor.notes == ["hello"]
    assert executor.sources == [{"url": "https://x", "title": "T", "claim": "C"}]


@pytest.mark.asyncio
async def test_finish_marks_finished(tmp_path):
    executor, _ = _make_executor(tmp_path)
    result = await executor.run("finish", {"summary": "done"})
    assert result == {"finished": True, "summary": "done"}
    assert executor.finished and executor.finish_summary == "done"


@pytest.mark.asyncio
async def test_tool_failure_returned_not_raised(tmp_path):
    executor, _ = _make_executor(tmp_path)

    async def boom(*a, **kw):
        raise RuntimeError("boom")

    executor.browser.goto = boom
    result = await executor.run("browser_goto", {"url": "https://example.com"})
    assert "error" in result and result["error"].startswith("tool_failed:RuntimeError")