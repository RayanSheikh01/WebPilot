from dataclasses import dataclass

import httpx

from webpilot.config import get_settings

TAVILY_URL = "https://api.tavily.com/search"


@dataclass(frozen=True)
class SearchHit:
    title: str
    url: str
    snippet: str


class SearchError(Exception):
    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


class TavilyClient:
    def __init__(self, api_key: str | None = None, timeout: float = 10.0):
        self.api_key = api_key or get_settings().tavily_api_key
        self.timeout = timeout

    async def search(self, query: str, k: int = 5) -> list[SearchHit]:
        payload = {"api_key": self.api_key, "query": query, "max_results": k}
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(TAVILY_URL, json=payload)
        except httpx.TimeoutException as e:
            raise SearchError(f"tavily timeout: {e}") from e
        except httpx.HTTPError as e:
            raise SearchError(f"tavily network error: {e}") from e

        if resp.status_code >= 400:
            raise SearchError(
                f"tavily http {resp.status_code}: {resp.text[:200]}",
                status=resp.status_code,
            )

        data = resp.json()
        return [
            SearchHit(
                title=r.get("title", ""),
                url=r.get("url", ""),
                snippet=r.get("content", ""),
            )
            for r in data.get("results", [])
        ]
