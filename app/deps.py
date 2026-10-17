"""Dependências FastAPI: usuário autenticado e posse de recursos."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Campanha, Usina, Usuario
from app.security import COOKIE_NAME, decode_token


class LoginRequired(Exception):
    """Levantada nas rotas web para redirecionar ao login."""


def _token_from(request: Request) -> str | None:
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:]
    return request.cookies.get(COOKIE_NAME)


def current_user(request: Request, db: Session = Depends(get_db)) -> Usuario:
    token = _token_from(request)
    user_id = decode_token(token) if token else None
    user = db.get(Usuario, user_id) if user_id else None
    if user is None:
        if "text/html" in request.headers.get("accept", ""):
            raise LoginRequired
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Autenticação necessária.")
    return user


def get_owned_usina(db: Session, user: Usuario, usina_id: int) -> Usina:
    usina = db.get(Usina, usina_id)
    if usina is None or (usina.dono_id != user.id and user.papel != "admin"):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usina não encontrada.")
    return usina


def get_owned_campanha(db: Session, user: Usuario, campanha_id: int) -> Campanha:
    campanha = db.get(Campanha, campanha_id)
    if campanha is None or (campanha.usina.dono_id != user.id and user.papel != "admin"):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Campanha não encontrada.")
    return campanha
