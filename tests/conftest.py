import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
import pytest_asyncio

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "site"


class _Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(FIXTURE_DIR), **kwargs)

    def do_GET(self):
        if self.path.startswith("/slow"):
            time.sleep(5)
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><body>slow</body></html>")
            return
        super().do_GET()

    def log_message(self, *args, **kwargs):
        pass


@pytest.fixture(scope="session")
def static_site():
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://localhost:{port}"
    server.shutdown()


@pytest_asyncio.fixture
async def browser():
    from webpilot.agent.browser import Browser
    async with Browser(headless=True, nav_timeout_ms=1500) as b:
        yield b
