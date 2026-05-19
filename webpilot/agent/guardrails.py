"""Budget tracker per plan §2.2.

`check_before_call` returns a `BudgetViolation` or None — it never raises.
The ToolExecutor turns a violation into a `{"error": "budget_exceeded:<name>"}`
result so the planner can call `finish` gracefully.
"""

import time
from dataclasses import dataclass

VIOLATION_NAMES = ("cancelled", "wall_clock", "tool_calls", "pages", "tokens")


@dataclass(frozen=True)
class BudgetViolation:
    name: str
    limit: int | float
    observed: int | float


class BudgetTracker:
    def __init__(
        self,
        max_seconds: float = 300,
        max_tool_calls: int = 40,
        max_pages: int = 10,
        max_input_tokens: int = 200_000,
        max_output_tokens: int = 20_000,
    ):
        self.max_seconds = max_seconds
        self.max_tool_calls = max_tool_calls
        self.max_pages = max_pages
        self.max_input_tokens = max_input_tokens
        self.max_output_tokens = max_output_tokens

        self.start_ts = time.monotonic()
        self.tool_calls = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self._visited_urls: set[str] = set()
        self._cancelled = False

    @property
    def elapsed(self) -> float:
        return time.monotonic() - self.start_ts

    @property
    def pages(self) -> int:
        return len(self._visited_urls)

    def cancel(self) -> None:
        self._cancelled = True

    def record_tool_call(self) -> None:
        self.tool_calls += 1

    def record_page(self, final_url: str) -> None:
        self._visited_urls.add(final_url)

    def record_usage(self, input_tokens: int, output_tokens: int) -> None:
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens

    def check_before_call(self) -> BudgetViolation | None:
        if self._cancelled:
            return BudgetViolation("cancelled", 0, 0)
        if self.elapsed > self.max_seconds:
            return BudgetViolation("wall_clock", self.max_seconds, self.elapsed)
        if self.tool_calls >= self.max_tool_calls:
            return BudgetViolation("tool_calls", self.max_tool_calls, self.tool_calls)
        if self.pages >= self.max_pages:
            return BudgetViolation("pages", self.max_pages, self.pages)
        if self.input_tokens >= self.max_input_tokens:
            return BudgetViolation("tokens", self.max_input_tokens, self.input_tokens)
        if self.output_tokens >= self.max_output_tokens:
            return BudgetViolation("tokens", self.max_output_tokens, self.output_tokens)
        return None
