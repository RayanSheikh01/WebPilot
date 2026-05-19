import pytest

@pytest.mark.asyncio
async def test_planner_loop():
    from webpilot.agent.planner import Planner, LoopResult
    from webpilot.agent.tools import TOOL_SCHEMAS
    from webpilot.agent.guardrails import BudgetTracker

    # Create dummy dependencies
    class DummyAgent:
        async def run(self, input): return {"answer": "final answer"}

    class DummyToolExecutor:
        async def run(self, name, input): return {"result": f"output of {name}"}

    budget_tracker = BudgetTracker({"wall_clock": 10, "tool_calls": 10, "pages": 10, "tokens": 1000})
    planner = Planner(DummyAgent(), DummyToolExecutor(), budget_tracker)

    result = await planner.run("Test prompt")
    assert isinstance(result, LoopResult)
    assert result.answer == "final answer"
    assert result.tool_calls == []

