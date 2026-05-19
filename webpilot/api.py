from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from .events import EventBus
from .store import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    app.state.event_bus = EventBus()
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/", response_class=HTMLResponse)
def read_root() -> str:
    return """<!doctype html>
<html>
    <head><title>WebPilot</title></head>
    <body>
        <h1>WebPilot</h1>
        <p>Placeholder home page.</p>
    </body>
</html>
"""
