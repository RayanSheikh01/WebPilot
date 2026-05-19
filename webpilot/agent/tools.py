"""Tool schemas (per plan §2.1) and ToolExecutor (per plan §2.3).

Schemas use the field names the system prompt assumes:
  note(text), cite(url, title, claim), finish(summary).
"""

from pathlib import Path
from typing import Any, Awaitable, Callable

from .guardrails import BudgetTracker

DEFAULT_MAX_CHARS = 8000
HARD_MAX_CHARS = 32000

TOOL_SCHEMAS: list[dict] = [
    {
        "name": "web_search",
        "description": "Search the web. Use specific queries; prefer multiple narrow searches over one broad one.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "k": {"type": "integer", "default": 5, "description": "Number of results (default 5)."},
            },
            "required": ["query"],
        },
    },
    {
        "name": "browser_goto",
        "description": "Navigate to an absolute http(s) URL from a prior search or get_links result. Returns final_url, title, status, snippet.",
        "input_schema": {
            "type": "object",
            "properties": {"url": {"type": "string"}},
            "required": ["url"],
        },
    },
    {
        "name": "browser_get_text",
        "description": "Read text from the current page. Truncates to max_chars (default 8000, hard cap 32000).",
        "input_schema": {
            "type": "object",
            "properties": {
                "selector": {"type": "string", "default": "body"},
                "max_chars": {"type": "integer", "default": DEFAULT_MAX_CHARS},
            },
            "required": [],
        },
    },
    {
        "name": "browser_get_links",
        "description": "Get http(s) links from the current page as a list of {text, href}.",
        "input_schema": {
            "type": "object",
            "properties": {"selector": {"type": "string", "default": "body"}},
            "required": [],
        },
    },
    {
        "name": "browser_screenshot",
        "description": "Take a screenshot of the current page. Use sparingly; counts against the budget.",
        "input_schema": {
            "type": "object",
            "properties": {"full_page": {"type": "boolean", "default": False}},
            "required": [],
        },
    },
    {
        "name": "browser_back",
        "description": "Return to the previous page.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "note",
        "description": "Append to private working memory. Notes do not appear in the final report.",
        "input_schema": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    },
    {
        "name": "cite",
        "description": "Record a claim with its source URL and the page title you read it on. Every substantive report statement must be backed by a cite.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string"},
                "title": {"type": "string"},
                "claim": {"type": "string"},
            },
            "required": ["url", "title", "claim"],
        },
    },
    {
        "name": "finish",
        "description": "End the run. Provide a short summary of what you found.",
        "input_schema": {
            "type": "object",
            "properties": {"summary": {"type": "string"}},
            "required": ["summary"],
        },
    },
]


class ToolExecutor:
    """Dispatches tool calls; gates each on the budget tracker."""

    def __init__(
        self,
        browser,
        search,
        tracker: BudgetTracker,
        screenshot_dir: Path,
        emit: Callable[[str, dict], Awaitable[None] | None] | None = None,
    ):
        self.browser = browser
        self.search = search
        self.tracker = tracker
        self.screenshot_dir = Path(screenshot_dir)
        self.emit = emit
        self.notes: list[str] = []
        self.sources: list[dict] = []
        self.finished: bool = False
        self.finish_summary: str | None = None
        self._screenshot_count = 0
        self._dispatch: dict[str, Callable[[dict], Awaitable[Any]]] = {
            "web_search": self._web_search,
            "browser_goto": self._browser_goto,
            "browser_get_text": self._browser_get_text,
            "browser_get_links": self._browser_get_links,
            "browser_screenshot": self._browser_screenshot,
            "browser_back": self._browser_back,
            "note": self._note,
            "cite": self._cite,
            "finish": self._finish,
        }

    async def run(self, name: str, tool_input: dict) -> Any:
        violation = self.tracker.check_before_call()
        if violation is not None:
            return {"error": f"budget_exceeded:{violation.name}"}

        handler = self._dispatch.get(name)
        if handler is None:
            return {"error": f"unknown_tool:{name}"}

        self.tracker.record_tool_call()
        try:
            return await handler(tool_input or {})
        except Exception as e:  # tool failures returned to planner, never raised
            return {"error": f"tool_failed:{type(e).__name__}:{e}"}

    async def _web_search(self, args: dict) -> dict:
        query = args["query"]
        k = int(args.get("k", 5))
        hits = await self.search.search(query, k=k)
        return {
            "results": [
                {"title": h.title, "url": h.url, "snippet": h.snippet} for h in hits
            ]
        }

    async def _browser_goto(self, args: dict) -> dict:
        url = args["url"]
        nav = await self.browser.goto(url)
        self.tracker.record_page(nav.final_url)
        return {
            "final_url": nav.final_url,
            "title": nav.title,
            "status": nav.status,
            "snippet": nav.snippet[:DEFAULT_MAX_CHARS],
        }

    async def _browser_get_text(self, args: dict) -> dict:
        selector = args.get("selector", "body")
        max_chars = min(int(args.get("max_chars", DEFAULT_MAX_CHARS)), HARD_MAX_CHARS)
        text = await self.browser.get_text(selector=selector, max_chars=max_chars)
        return {"text": text}

    async def _browser_get_links(self, args: dict) -> dict:
        selector = args.get("selector", "body")
        links = await self.browser.get_links(selector=selector)
        return {"links": links}

    async def _browser_screenshot(self, args: dict) -> dict:
        self._screenshot_count += 1
        path = self.screenshot_dir / f"{self._screenshot_count}.png"
        await self.browser.screenshot(path, full_page=bool(args.get("full_page", False)))
        return {"path": str(path)}

    async def _browser_back(self, args: dict) -> dict:
        nav = await self.browser.back()
        return {
            "final_url": nav.final_url,
            "title": nav.title,
            "status": nav.status,
            "snippet": nav.snippet[:DEFAULT_MAX_CHARS],
        }

    async def _note(self, args: dict) -> dict:
        self.notes.append(args["text"])
        return {"ok": True}

    async def _cite(self, args: dict) -> dict:
        self.sources.append(
            {"url": args["url"], "title": args["title"], "claim": args["claim"]}
        )
        return {"ok": True}

    async def _finish(self, args: dict) -> dict:
        self.finished = True
        self.finish_summary = args.get("summary", "")
        return {"finished": True, "summary": self.finish_summary}
