import asyncio

from dotenv import load_dotenv

from webpilot.agent.browser import Browser
from webpilot.agent.search import TavilyClient


async def smoke_phase1() -> None:
    load_dotenv()

    client = TavilyClient()
    hits = await client.search("anthropic claude", k=3)

    print(f"Top {len(hits)} search results:")
    for i, hit in enumerate(hits, start=1):
        print(f"  {i}. {hit.title}")
        print(f"     {hit.url}")
        print(f"     {hit.snippet[:120]}")

    if not hits:
        print("No search results; aborting browser step.")
        return

    first_url = hits[0].url
    print(f"\nFetching: {first_url}")

    async with Browser(headless=True) as browser:
        nav = await browser.goto(first_url)
        text = await browser.get_text(max_chars=200)

    print(f"  status: {nav.status}")
    print(f"  title:  {nav.title}")
    print(f"  text:   {text!r}")


if __name__ == "__main__":
    asyncio.run(smoke_phase1())
    print("\nSmoke test phase 1 passed.")
