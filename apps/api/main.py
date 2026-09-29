"""Local research API and optional built chat frontend."""

from __future__ import annotations

from fastapi import FastAPI
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from apps.api.chat import router
from fastapi import Request
from fastapi.responses import JSONResponse

app = FastAPI(title="Asia Tax AI Agent — HK FSIE L0", version="0.1.0")
from apps.api.auth import router as auth_router
app.include_router(auth_router)
app.include_router(router)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "testserver"])


@app.middleware("http")
async def private_responses(request: Request, call_next):
    try:
        response = await call_next(request)
    except Exception:
        # Provider errors, database URLs and user input must not escape into responses.
        response = JSONResponse({"detail": "service_unavailable"}, status_code=503)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "release_level": "L0"}


frontend = Path(__file__).resolve().parents[1] / "web" / "dist"
if frontend.is_dir():
    app.mount("/", StaticFiles(directory=frontend, html=True), name="chat_frontend")
