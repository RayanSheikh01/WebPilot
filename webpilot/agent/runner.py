"""End-to-end wiring for a single brief (plan §3.3 + §4.3).

Two entry points:

* :func:`run_brief_local` — used by tests and the CLI. No bus/store; just
  returns the final markdown report.
* :func:`run_brief` — production path. Persists lifecycle/events through
  ``webpilot.store`` and fans them out live via an :class:`EventBus`.
"""

from __future__ import annotations

import os
import tempfile
from datetime import datetime
from pathlib import Path

from . import reporter
from .browser import Browser
from .guardrails import BudgetTracker
from .planner import Planner
from .search import TavilyClient
from .tools import ToolExecutor


def _default_model() -> str:
    return os.environ.get("WEBPILOT_MODEL", "claude-opus-4-7")


def _build_search_client():
    """Construct a TavilyClient; if TAVILY_API_KEY is unset, defer failure to
    first use rather than crashing briefs that never search.
    """
    try:
        return TavilyClient()
    except Exception:
        return None


async def run_brief_local(
    prompt: str,
    *,
    client=None,
    screenshot_dir: Path | None = None,
    headless: bool = True,
) -> str:
    """Run a brief end-to-end and return the markdown report string."""
    if client is None:
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic()

    if screenshot_dir is None:
        screenshot_dir = Path(tempfile.mkdtemp(prefix="webpilot_shots_"))
    else:
        screenshot_dir = Path(screenshot_dir)
        screenshot_dir.mkdir(parents=True, exist_ok=True)

    tracker = BudgetTracker()
    search = _build_search_client()

    async with Browser(headless=headless) as browser:
        executor = ToolExecutor(
            browser=browser,
            search=search,
            tracker=tracker,
            screenshot_dir=screenshot_dir,
        )
        planner = Planner(
            client=client,
            executor=executor,
            tracker=tracker,
            model=_default_model(),
        )
        result = await planner.run(prompt)

    return reporter.draft(prompt, result.notes, result.sources, result.summary)


async def run_brief(
    brief_id: str,
    prompt: str,
    bus,
    store,
    *,
    client=None,
    screenshot_dir: Path | None = None,
    headless: bool = True,
) -> str:
    """Production entry: run a brief, persist events + lifecycle, fan out live.

    ``store`` is expected to be the :mod:`webpilot.store` module (or a shim
    exposing the same function surface). Events are both ``append_event``'d
    and ``bus.publish``'d via a single local ``emit`` callable.
    """
    from ..events import Event  # local import to avoid cycles

    if client is None:
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic()

    if screenshot_dir is None:
        screenshot_dir = Path(tempfile.mkdtemp(prefix=f"webpilot_{brief_id}_"))
    else:
        screenshot_dir = Path(screenshot_dir)
        screenshot_dir.mkdir(parents=True, exist_ok=True)

    def emit(kind: str, payload: dict) -> None:
        # Persist first; if persistence fails we still attempt to publish.
        try:
            store.append_event(brief_id, kind, payload)
        except Exception:
            pass
        try:
            bus.publish(brief_id, Event(kind=kind, payload=payload, ts=datetime.utcnow()))
        except Exception:
            pass

    tracker = BudgetTracker()
    search = _build_search_client()

    try:
        store.update_brief(brief_id, status="running")
        emit("status:running", {})

        async with Browser(headless=headless) as browser:
            executor = ToolExecutor(
                browser=browser,
                search=search,
                tracker=tracker,
                screenshot_dir=screenshot_dir,
                emit=emit,
            )
            planner = Planner(
                client=client,
                executor=executor,
                tracker=tracker,
                model=_default_model(),
                emit=emit,
            )
            result = await planner.run(prompt)

        markdown = reporter.draft(prompt, result.notes, result.sources, result.summary)
        store.save_report(brief_id, markdown)
        store.update_brief(
            brief_id,
            status="done",
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            tool_calls=tracker.tool_calls,
        )
        return markdown
    except Exception as e:
        try:
            emit("error", {"type": type(e).__name__, "message": str(e)})
        finally:
            try:
                store.update_brief(brief_id, status="failed")
            except Exception:
                pass
        raise
    finally:
        try:
            bus.close(brief_id)
        except Exception:
            pass
