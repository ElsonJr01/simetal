"""Aplicação FastAPI do SIMETAL."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import __version__
from app.auth_service import bootstrap_admin
from app.config import get_settings
from app.db import SessionLocal, init_db
from app.deps import LoginRequired
from app.middleware import RequestMiddleware
from app.routers import admin, api, help, web

log = logging.getLogger("simetal")


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    if settings.auto_create_tables:
        init_db()
    if settings.admin_email:
        try:
            with SessionLocal() as db:
                bootstrap_admin(db)
        except Exception:  # noqa: BLE001  (não derruba o app se as tabelas ainda não existem)
            log.exception("Não foi possível garantir o administrador inicial.")
    yield


def _wants_html(request: Request) -> bool:
    return "text/html" in request.headers.get("accept", "") and not request.url.path.startswith("/api/")


def create_app() -> FastAPI:
    app = FastAPI(
        title="SIMETAL",
        description="Ajuste e fechamento de balanço de massas e metalúrgico (mínimos quadrados com restrições).",
        version=__version__,
        lifespan=lifespan,
    )
    app.add_middleware(RequestMiddleware)
    app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")
    app.include_router(api.router)
    app.include_router(web.router)
    app.include_router(help.router)
    app.include_router(admin.router)

    @app.exception_handler(LoginRequired)
    async def _login_required(_: Request, __: LoginRequired) -> RedirectResponse:
        return RedirectResponse("/login", status_code=303)

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(request: Request, exc: StarletteHTTPException):
        if _wants_html(request) and exc.status_code in (403, 404, 405):
            return web.render(request, "error.html", exc.status_code, codigo=exc.status_code, mensagem=str(exc.detail), user=getattr(request.state, "user", None))
        return await http_exception_handler(request, exc)

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception):
        rid = getattr(request.state, "request_id", "-")
        log.exception("Erro não tratado rid=%s %s %s", rid, request.method, request.url.path)
        if _wants_html(request):
            return web.render(request, "error.html", 500, codigo=500, mensagem="Ocorreu um erro inesperado. Tente de novo em instantes.", request_id=rid)
        return JSONResponse({"detail": "Erro interno do servidor.", "request_id": rid}, status_code=500)

    return app


app = create_app()
