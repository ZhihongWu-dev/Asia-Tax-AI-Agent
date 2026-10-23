"""Local research API and optional built chat frontend."""

from __future__ import annotations

import os
import re

from fastapi import FastAPI
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from apps.api.chat import router
from fastapi import Request
from fastapi.responses import JSONResponse
import logging
import traceback

logger = logging.getLogger(__name__)

from contextlib import asynccontextmanager
from packages.runtime import application_runtime


@asynccontextmanager
async def lifespan(app):
    with application_runtime() as runtime:
        app.state.runtime = runtime
        try:
            yield
        finally:
            # Cached clients must not retain the temporary knowledge endpoint.
            from apps.api.chat import get_service, get_provider
            if get_service.cache_info().currsize:
                get_service().store.engine.dispose()
            get_service.cache_clear()
            get_provider.cache_clear()
            app.state.runtime = None


app = FastAPI(lifespan=lifespan, title="Asia Tax AI Agent — HK FSIE L0", version="0.1.0")
from apps.api.auth import router as auth_router
app.include_router(auth_router)
app.include_router(router)
from apps.api.consultation import router as consultation_router
app.include_router(consultation_router)
# Trust only this service's platform hostname, never every Render tenant.
allowed_hosts = ["127.0.0.1", "localhost", "testserver"]
render_hostname = os.environ.get("RENDER_EXTERNAL_HOSTNAME", "")
if re.fullmatch(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.onrender\.com", render_hostname):
    allowed_hosts.append(render_hostname)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)


@app.middleware("http")
async def private_responses(request: Request, call_next):
    try:
        response = await call_next(request)
    except Exception as exc:
        # Provider errors, database URLs and user input must not escape into responses.
        # Log locations and exception types only: exception messages/locals may contain secrets.
        frames = traceback.extract_tb(exc.__traceback__)
        logger.error('Request failed: %s; locations=%s', type(exc).__name__,
                     ' > '.join(f'{Path(frame.filename).name}:{frame.lineno}:{frame.name}' for frame in frames))
        response = JSONResponse({"detail": "service_unavailable"}, status_code=503)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@app.middleware('http')
async def active_workflow(request: Request, call_next):
    # Keep the old implementation available for rollback, but suspend its business entry points.
    from packages.consultation.settings import brief_enabled
    path = request.url.path
    if brief_enabled() and (path.startswith('/api/knowledge/') or path.startswith('/api/domain/') or
            re.fullmatch(r'/api/cases/[^/]+/(?:messages|facts|confirm|analyze|domain[^/]*|analyses/.*)', path)):
        return JSONResponse({'detail': 'workflow_deactivated'}, status_code=409,
                            headers={'Cache-Control': 'no-store'})
    return await call_next(request)


@app.get("/health")
def health():
    result = {"status": "ok", "release_level": "L0"}
    # Public Git revision only; never expose the rest of the runtime environment.
    revision = os.environ.get("RENDER_GIT_COMMIT", "")
    if re.fullmatch(r"[0-9a-f]{40}", revision):
        result["revision"] = revision
    runtime = getattr(app.state, 'runtime', None)
    if runtime is not None:
        result['runtime'] = runtime.public()
        if runtime.provider == 'combined' and not result['runtime']['knowledge_ready']:
            return JSONResponse({**result, 'status': 'unavailable'}, status_code=503)
    return result


@app.middleware("http")
async def fresh_frontend(request: Request, call_next):
    response = await call_next(request)
    if request.url.path in ('/', '/index.html'):
        response.headers['Cache-Control'] = 'no-store'
    return response


frontend = Path(__file__).resolve().parents[1] / "web" / "dist"
if frontend.is_dir():
    app.mount("/", StaticFiles(directory=frontend, html=True), name="chat_frontend")
