"""Aplicação FastAPI do SIMETAL."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.config import get_settings
from app.db import init_db
from app.deps import LoginRequired
from app.routers import api, web


@asynccontextmanager
async def lifespan(_: FastAPI):
    if get_settings().auto_create_tables:
        init_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="SIMETAL",
        description="Ajuste e fechamento de balanço de massas e metalúrgico (mínimos quadrados com restrições).",
        version=__version__,
        lifespan=lifespan,
    )
    app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")
    app.include_router(api.router)
    app.include_router(web.router)

    @app.exception_handler(LoginRequired)
    async def _login_required(_: Request, __: LoginRequired) -> RedirectResponse:
        return RedirectResponse("/login", status_code=303)

    return app


app = create_app()
