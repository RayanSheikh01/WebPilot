import pytest
import time


@pytest.mark.asyncio
async def test_budget_tracker():
    from webpilot.agent.guardrails import BudgetTracker, BudgetExceeded

    budget = {
        "wall_clock": 1,  # 1 second
        "tool_calls": 2,
        "pages": 1,
        "tokens": 10,
    }
    tracker = BudgetTracker(budget)

    # Should allow first call
    tracker.check_before_call("browser_goto", {"url": "http://example.com"})
    tracker.record_call("browser_goto", {"url": "http://example.com"}, {}, 5)

    # Should not allow second call to browser_goto (page limit)
    with pytest.raises(BudgetExceeded, match="Page limit exceeded"):
        tracker.check_before_call("browser_goto", {"url": "http://example.org"})

    # Should allow a different tool call
    tracker.check_before_call("web_search", {"query": "test"})
    tracker.record_call("web_search", {"query": "test"}, {}, 5)

    # Should not allow any more tool calls (tool call limit)
    with pytest.raises(BudgetExceeded, match="Tool call limit exceeded"):
        tracker.check_before_call("web_search", {"query": "another test"})

    # Should not allow calls after wall clock time exceeded
    time.sleep(1.1)
    with pytest.raises(BudgetExceeded, match="Wall clock time exceeded"):
        tracker.check_before_call("web_search", {"query": "late test"})

    # Test cancellation
    tracker = BudgetTracker(budget)
    tracker.cancel()
    with pytest.raises(BudgetExceeded, match="Budget has been cancelled"):
        tracker.check_before_call("web_search", {"query": "cancelled test"})

