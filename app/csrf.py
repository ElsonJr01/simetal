"""Proteção CSRF por 'double submit cookie' para as rotas web (formulários e HTMX)."""

from __future__ import annotations

import hmac
import secrets

from fastapi import HTTPException, Request, Response, status

from app.config import get_settings

COOKIE = "simetal_csrf"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def new_token() -> str:
    return secrets.token_urlsafe(32)


def ensure_cookie(response: Response, request: Request, token: str) -> None:
    if request.cookies.get(COOKIE) != token:
        response.set_cookie(
            COOKIE, token, httponly=True, samesite="lax", secure=get_settings().env == "production", max_age=60 * 60 * 24 * 7
        )


async def csrf_protect(request: Request) -> None:
    """Dependência de router: exige token igual ao do cookie (campo `csrf_token` ou cabeçalho X-CSRF-Token)."""
    if request.method in SAFE_METHODS:
        return
    cookie = request.cookies.get(COOKIE)
    sent = request.headers.get("x-csrf-token")
    if not sent:
        form = await request.form()
        sent = form.get("csrf_token")
    if not cookie or not sent or not hmac.compare_digest(cookie, str(sent)):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Sessão expirada ou formulário inválido. Recarregue a página e tente de novo.")
