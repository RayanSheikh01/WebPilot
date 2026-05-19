import httpx
import pytest
import respx

from webpilot.agent.search import SearchError, SearchHit, TavilyClient, TAVILY_URL


@pytest.mark.asyncio
@respx.mock
async def test_search_returns_hits():
    respx.post(TAVILY_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "results": [
                    {"title": "Paris", "url": "https://example.com/paris", "content": "capital of France"},
                    {"title": "France", "url": "https://example.com/france", "content": "country in Europe"},
                ]
            },
        )
    )
    client = TavilyClient(api_key="test-key")
    hits = await client.search("capital of France", k=2)

    assert len(hits) == 2
    assert all(isinstance(h, SearchHit) for h in hits)
    assert hits[0].title == "Paris"
    assert hits[0].url == "https://example.com/paris"
    assert hits[0].snippet == "capital of France"


@pytest.mark.asyncio
@respx.mock
async def test_search_raises_on_http_error():
    respx.post(TAVILY_URL).mock(return_value=httpx.Response(500, text="boom"))
    client = TavilyClient(api_key="test-key")
    with pytest.raises(SearchError) as exc:
        await client.search("anything")
    assert exc.value.status == 500


@pytest.mark.asyncio
@respx.mock
async def test_search_raises_on_timeout():
    respx.post(TAVILY_URL).mock(side_effect=httpx.TimeoutException("slow"))
    client = TavilyClient(api_key="test-key")
    with pytest.raises(SearchError):
        await client.search("anything")
