# Implement FastAPI app with a lifespan that calls init_db() and attaches a singleton EventBus + BriefManager (see 5.2) to app.state. GET / renders home.html (empty list for now — proper render in Phase 6; for now serve a minimal HTML stub).

from __future__ import annotations

from fastapi import FastAPI

from .events import EventBus

app = FastAPI()

@app.on_event("startup")
def on_startup():
    # Initialize the database and attach a singleton EventBus to app.state.
    from .store import init_db
    init_db()
    app.state.event_bus = EventBus()

@app.get("/")
def read_root():
    # For now, just return a minimal HTML stub. Proper rendering in Phase 6.
    return """
    <html>
        <head><title>WebPilot</title></head>
        <body>
            <h1>Welcome to WebPilot</h1>
            <p>This is a placeholder home page.</p>
        </body>
    </html>
    """
