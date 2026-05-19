import asyncio
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from playwright.async_api import (
    TimeoutError as PlaywrightTimeoutError,
    async_playwright,
)


@dataclass
class NavResult:
    final_url: str
    title: str
    status: int
    snippet: str


class BlockedSchemeError(Exception):
    pass


class NavTimeoutError(Exception):
    def __init__(self, message: str, nav_result: NavResult):
        super().__init__(message)
        self.nav_result = nav_result


class Browser:
    BLOCKED_SCHEMES = ("mailto:", "tel:", "javascript:", "file://", "data:")

    def __init__(
        self,
        headless: bool = True,
        user_agent: str = "WebPilot/0.1",
        nav_timeout_ms: int = 15000,
    ):
        self.headless = headless
        self.user_agent = user_agent
        self.nav_timeout_ms = nav_timeout_ms
        self._playwright = None
        self._browser = None
        self._context = None
        self.page = None
        self._last_hit: dict[str, float] = {}

    async def __aenter__(self):
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=self.headless)
        self._context = await self._browser.new_context(
            user_agent=self.user_agent, accept_downloads=False
        )
        self.page = await self._context.new_page()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    def _check_scheme(self, url: str) -> None:
        low = url.lower()
        for scheme in self.BLOCKED_SCHEMES:
            if low.startswith(scheme):
                raise BlockedSchemeError(url)

    async def _throttle(self, host: str) -> None:
        last = self._last_hit.get(host)
        if last is not None:
            wait = 1.0 - (time.monotonic() - last)
            if wait > 0:
                await asyncio.sleep(wait)
        self._last_hit[host] = time.monotonic()

    async def goto(self, url: str) -> NavResult:
        self._check_scheme(url)
        host = urlparse(url).hostname or ""
        await self._throttle(host)
        try:
            response = await self.page.goto(
                url, timeout=self.nav_timeout_ms, wait_until="domcontentloaded"
            )
        except PlaywrightTimeoutError as e:
            nav_result = NavResult(
                final_url=url, title="", status=408, snippet="Navigation timed out"
            )
            raise NavTimeoutError(f"timeout navigating to {url}", nav_result) from e

        status = response.status if response else 0
        final_url = self.page.url
        title = await self.page.title()
        body_text = await self.page.evaluate(
            "() => document.body ? document.body.innerText : ''"
        )
        return NavResult(
            final_url=final_url, title=title, status=status, snippet=body_text[:200]
        )

    async def get_text(self, selector: str = "body", max_chars: int = 8000) -> str:
        text = await self.page.evaluate(
            "(sel) => { const el = document.querySelector(sel); return el ? el.innerText : ''; }",
            selector,
        )
        return text[:max_chars]

    async def get_links(self, selector: str = "body") -> list[dict]:
        return await self.page.evaluate(
            """(sel) => {
                const root = document.querySelector(sel);
                if (!root) return [];
                return Array.from(root.querySelectorAll('a'))
                    .filter(a => a.href.startsWith('http'))
                    .map(a => ({text: a.innerText, href: a.href}));
            }""",
            selector,
        )

    async def screenshot(self, path: Path, full_page: bool = False) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        await self.page.screenshot(path=str(path), full_page=full_page)
        return path

    async def back(self) -> NavResult:
        await self.page.go_back(timeout=self.nav_timeout_ms)
        final_url = self.page.url
        title = await self.page.title()
        body_text = await self.page.evaluate(
            "() => document.body ? document.body.innerText : ''"
        )
        return NavResult(
            final_url=final_url, title=title, status=0, snippet=body_text[:200]
        )
