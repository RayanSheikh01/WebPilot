"""Planner loop tests with a scripted FakeAnthropic."""

from dataclasses import dataclass

from webpilot.agent.guardrails import BudgetTracker
from webpilot.agent.planner import Planner


@dataclass
class _Block:
    type: str
    text: str = ""
    name: str = ""
    input: dict | None = None
    id: str = ""


@dataclass
class _Usage:
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass
class _Response:
    content: list
    usage: _Usage


class _Messages:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls: list[dict] = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        return self._responses.pop(0)


class FakeAnthropic:
    def __init__(self, responses):
        self.messages = _Messages(responses)


class FakeExecutor:
    def __init__(self, results_by_name: dict, finish_on: str = "finish"):
        self.results_by_name = results_by_name
        self.finish_on = finish_on
        self.calls: list[tuple[str, dict]] = []
        self.notes: list[str] = []
        self.sources: list[dict] = []
        self.finished = False
        self.finish_summary: str | None = None

    async def run(self, name: str, tool_input: dict):
        self.calls.append((name, tool_input))
        if name == self.finish_on:
            self.finished = True
            self.finish_summary = tool_input.get("summary", "")
            return {"finished": True, "summary": self.finish_summary}
        return self.results_by_name.get(name, {"ok": True})


def _tool_use(name: str, tool_input: dict, block_id: str = "id1") -> _Block:
    return _Block(type="tool_use", name=name, input=tool_input, id=block_id)


def _text(text: str) -> _Block:
    return _Block(type="text", text=text)


async def test_happy_path_search_then_finish():
    fake = FakeAnthropic(
        [
            _Response(
                content=[_tool_use("web_search", {"query": "anthropic"}, "u1")],
                usage=_Usage(100, 20),
            ),
            _Response(
                content=[_tool_use("finish", {"summary": "done"}, "u2")],
                usage=_Usage(50, 10),
            ),
        ]
    )
    executor = FakeExecutor(results_by_name={"web_search": {"results": []}})
    tracker = BudgetTracker()
    planner = Planner(fake, executor, tracker, model="test-model")

    result = await planner.run("research brief")

    assert result.terminated_reason == "finish"
    assert result.summary == "done"
    assert [c[0] for c in executor.calls] == ["web_search", "finish"]
    assert tracker.input_tokens == 150
    assert tracker.output_tokens == 30


async def test_no_tool_use_terminates():
    fake = FakeAnthropic([_Response(content=[_text("hello")], usage=_Usage(10, 5))])
    executor = FakeExecutor(results_by_name={})
    planner = Planner(fake, executor, BudgetTracker(), model="m")

    result = await planner.run("brief")
    assert result.terminated_reason == "no_tool_use"


async def test_multiple_tool_uses_in_one_response():
    fake = FakeAnthropic(
        [
            _Response(
                content=[
                    _tool_use("note", {"text": "a"}, "u1"),
                    _tool_use("note", {"text": "b"}, "u2"),
                ],
                usage=_Usage(20, 10),
            ),
            _Response(
                content=[_tool_use("finish", {"summary": "ok"}, "u3")],
                usage=_Usage(10, 5),
            ),
        ]
    )
    executor = FakeExecutor(results_by_name={"note": {"ok": True}})
    planner = Planner(fake, executor, BudgetTracker(), model="m")

    result = await planner.run("brief")
    assert result.terminated_reason == "finish"
    assert [c[0] for c in executor.calls] == ["note", "note", "finish"]
    user_results = [m for m in result.messages if m["role"] == "user"][1]
    assert len(user_results["content"]) == 2


async def test_cache_markers_present_in_request():
    fake = FakeAnthropic(
        [_Response(content=[_tool_use("finish", {"summary": "x"}, "u1")], usage=_Usage(1, 1))]
    )
    executor = FakeExecutor(results_by_name={})
    planner = Planner(fake, executor, BudgetTracker(), model="m")
    await planner.run("brief")

    req = fake.messages.calls[0]
    assert req["system"][-1]["cache_control"] == {"type": "ephemeral"}
    assert req["tools"][-1]["cache_control"] == {"type": "ephemeral"}


async def test_planner_emits_events_in_order():
    fake = FakeAnthropic(
        [
            _Response(
                content=[_tool_use("web_search", {"query": "x"}, "u1")],
                usage=_Usage(10, 5),
            ),
            _Response(
                content=[_tool_use("finish", {"summary": "ok"}, "u2")],
                usage=_Usage(5, 5),
            ),
        ]
    )
    executor = FakeExecutor(results_by_name={"web_search": {"results": []}})
    events: list[tuple[str, dict]] = []

    def emit(kind, payload):
        events.append((kind, payload))

    planner = Planner(fake, executor, BudgetTracker(), model="m", emit=emit)
    await planner.run("brief")

    kinds = [k for k, _ in events]
    assert kinds[0] == "status:running"
    assert "tool_call" in kinds
    assert "tool_result" in kinds
    assert "finish" in kinds
    assert kinds.index("tool_call") < kinds.index("tool_result")
    assert kinds[-1] == "finish"


async def test_budget_violation_breaks_loop_before_call():
    fake = FakeAnthropic([])
    executor = FakeExecutor(results_by_name={})
    tracker = BudgetTracker(max_tool_calls=0)
    tracker.record_tool_call()
    planner = Planner(fake, executor, tracker, model="m")

    result = await planner.run("brief")
    assert result.terminated_reason.startswith("budget:")
    assert fake.messages.calls == []
