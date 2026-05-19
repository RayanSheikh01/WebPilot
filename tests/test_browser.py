import pytest

from webpilot.agent import browser as browser_mod


@pytest.mark.asyncio
async def test_goto_and_get_text(static_site, browser):
    url = static_site + "/index.html"
    result = await browser.goto(url)
    assert result.final_url == url
    assert result.status == 200
    assert result.snippet
    text = await browser.get_text(selector="body", max_chars=20)
    assert len(text) <= 20


@pytest.mark.asyncio
async def test_goto_blocked_schemes(browser):
    for url in [
        "mailto:foo@bar.com",
        "javascript:alert(1)",
        "file:///etc/passwd",
        "data:text/plain;base64,SGVsbG8sIFdvcmxkIQ==",
        "tel:+1234567890",
    ]:
        with pytest.raises(browser_mod.BlockedSchemeError):
            await browser.goto(url)


@pytest.mark.asyncio
async def test_goto_404(static_site, browser):
    url = static_site + "/missing"
    result = await browser.goto(url)
    assert result.status == 404


@pytest.mark.asyncio
async def test_get_links(static_site, browser):
    url = static_site + "/links.html"
    await browser.goto(url)
    links = await browser.get_links()
    assert isinstance(links, list)
    assert len(links) > 0
    assert all("text" in link and "href" in link for link in links)
    assert all(link["href"].startswith("http") for link in links)


@pytest.mark.asyncio
async def test_per_domain_throttle(static_site, browser, monkeypatch):
    url = static_site + "/index.html"
    sleep_calls = []
    real_sleep = browser_mod.asyncio.sleep

    async def fake_sleep(duration):
        sleep_calls.append(duration)
        await real_sleep(0)

    monkeypatch.setattr(browser_mod.asyncio, "sleep", fake_sleep)

    await browser.goto(url)
    await browser.goto(url)
    assert any(d > 0.1 for d in sleep_calls), (
        f"throttle never triggered a meaningful sleep: {sleep_calls}"
    )


@pytest.mark.asyncio
async def test_navigation_timeout(static_site, browser):
    url = static_site + "/slow.html"
    with pytest.raises(browser_mod.NavTimeoutError):
        await browser.goto(url)


@pytest.mark.asyncio
async def test_navigation_timeout_returns_navresult(static_site, browser):
    url = static_site + "/slow.html"
    with pytest.raises(browser_mod.NavTimeoutError) as exc:
        await browser.goto(url)
    result = exc.value.nav_result
    assert result.status == 408
    assert result.final_url == url
    assert result.snippet == "Navigation timed out"
