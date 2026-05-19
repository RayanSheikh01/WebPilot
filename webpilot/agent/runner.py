"""End-to-end wiring for a single brief (plan §3.3).

`run_brief_local` builds real Browser/Search/Executor/Planner/Reporter
when called with no overrides; tests can inject a fake Anthropic `client`
and an alternate `screenshot_dir` to avoid real network calls.
"""

import uuid
from pathlib import Path

from anthropic import AsyncAnthropic

from . import reporter
from .browser import Browser
from .guardrails import BudgetTracker
from .planner import Planner
from .search import TavilyClient
from .tools import ToolExecutor


async def run_brief_local(
    brief: str,
    *,
    client=None,
    screenshot_dir: Path | None = None,
    headless: bool = True,
    model: str = "claude-opus-4-7",
    max_seconds: float = 300,
    max_tool_calls: int = 40,
    max_pages: int = 10,
) -> str:
    anthropic_client = client or AsyncAnthropic()
    brief_id = uuid.uuid4().hex[:12]
    shot_dir = Path(screenshot_dir or Path("data") / "screenshots" / brief_id)
    shot_dir.mkdir(parents=True, exist_ok=True)

    tracker = BudgetTracker(
        max_seconds=max_seconds,
        max_tool_calls=max_tool_calls,
        max_pages=max_pages,
    )
    search = TavilyClient()

    async with Browser(headless=headless) as browser:
        executor = ToolExecutor(
            browser=browser,
            search=search,
            tracker=tracker,
            screenshot_dir=shot_dir,
        )
        planner = Planner(
            client=anthropic_client,
            executor=executor,
            tracker=tracker,
            model=model,
        )
        loop_result = await planner.run(brief)

    return reporter.draft(
        brief=brief,
        notes=loop_result.notes,
        sources=loop_result.sources,
        summary=loop_result.summary,
    )
