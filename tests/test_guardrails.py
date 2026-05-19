import time

from webpilot.agent.guardrails import BudgetTracker, BudgetViolation


def test_ok_when_within_limits():
    t = BudgetTracker(max_seconds=60, max_tool_calls=10, max_pages=10)
    assert t.check_before_call() is None


def test_cancellation_takes_precedence():
    t = BudgetTracker()
    t.cancel()
    v = t.check_before_call()
    assert isinstance(v, BudgetViolation)
    assert v.name == "cancelled"


def test_tool_calls_limit():
    t = BudgetTracker(max_tool_calls=2)
    t.record_tool_call()
    t.record_tool_call()
    v = t.check_before_call()
    assert v and v.name == "tool_calls"


def test_pages_limit_uses_unique_urls():
    t = BudgetTracker(max_pages=2)
    t.record_page("https://a.com/x")
    t.record_page("https://a.com/x")  # duplicate
    assert t.check_before_call() is None
    t.record_page("https://b.com/y")
    v = t.check_before_call()
    assert v and v.name == "pages"


def test_token_limit_input():
    t = BudgetTracker(max_input_tokens=100)
    t.record_usage(60, 0)
    t.record_usage(50, 0)
    v = t.check_before_call()
    assert v and v.name == "tokens"


def test_token_limit_output():
    t = BudgetTracker(max_output_tokens=50)
    t.record_usage(0, 60)
    v = t.check_before_call()
    assert v and v.name == "tokens"


def test_wall_clock():
    t = BudgetTracker(max_seconds=0.05)
    time.sleep(0.06)
    v = t.check_before_call()
    assert v and v.name == "wall_clock"
