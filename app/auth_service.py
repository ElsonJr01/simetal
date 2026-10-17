"""Autenticação: bloqueio por tentativas, usuário ativo, auditoria e administrador inicial."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Auditoria, Configuracao, Usuario
from app.security import hash_password, verify_password

_DUMMY_HASH = hash_password("senha-fictícia-para-igualar-o-tempo")


class AuthError(Exception):
    """Falha de autenticação, com mensagem segura para o usuário."""


def aware(dt: datetime | None) -> datetime | None:
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def client_ip(request: Request | None) -> str:
    if request is None:
        return ""
    fwd = request.headers.get("x-forwarded-for", "")
    if fwd:
        return fwd.split(",")[0].strip()[:45]
    return request.client.host[:45] if request.client else ""


def audit(db: Session, acao: str, *, user: Usuario | None = None, alvo: str = "", detalhe: str = "", ip: str = "", email: str = "") -> None:
    db.add(
        Auditoria(
            usuario_id=user.id if user else None,
            usuario_email=(user.email if user else email),
            acao=acao,
            alvo=alvo[:160],
            detalhe=detalhe,
            ip=ip,
        )
    )
    db.commit()


# ------------------------------------------------------------- flags em tempo de execução
def registration_open(db: Session) -> bool:
    row = db.get(Configuracao, "allow_registration")
    if row is None:
        return get_settings().allow_registration
    return row.valor == "1"


def set_registration(db: Session, open_: bool) -> None:
    row = db.get(Configuracao, "allow_registration")
    if row is None:
        db.add(Configuracao(chave="allow_registration", valor="1" if open_ else "0"))
    else:
        row.valor = "1" if open_ else "0"
    db.commit()


# ------------------------------------------------------------------------------- login
def authenticate(db: Session, email: str, senha: str, request: Request | None = None) -> Usuario:
    s = get_settings()
    ip = client_ip(request)
    user = db.scalar(select(Usuario).where(Usuario.email == email.strip().lower()))
    now = datetime.now(UTC)

    if user is None:
        verify_password(senha, _DUMMY_HASH)  # iguala o tempo de resposta
        audit(db, "login_falha", alvo=email.strip().lower()[:160], detalhe="usuário inexistente", ip=ip, email=email.strip().lower())
        raise AuthError("E-mail ou senha incorretos.")

    locked_until = aware(user.bloqueado_ate)
    if locked_until and locked_until > now:
        minutes = int((locked_until - now).total_seconds() // 60) + 1
        raise AuthError(f"Conta temporariamente bloqueada por excesso de tentativas. Tente novamente em {minutes} min.")

    if not verify_password(senha, user.senha_hash):
        user.falhas_login += 1
        detalhe = f"tentativa {user.falhas_login}"
        if user.falhas_login >= s.lockout_attempts:
            user.bloqueado_ate = now + timedelta(minutes=s.lockout_minutes)
            user.falhas_login = 0
            detalhe = f"conta bloqueada por {s.lockout_minutes} min"
        db.commit()
        audit(db, "login_falha", user=user, alvo=user.email, detalhe=detalhe, ip=ip)
        raise AuthError("E-mail ou senha incorretos.")

    if not user.ativo:
        audit(db, "login_negado", user=user, alvo=user.email, detalhe="conta desativada", ip=ip)
        raise AuthError("Esta conta está desativada. Fale com o administrador.")

    user.falhas_login, user.bloqueado_ate, user.ultimo_login = 0, None, now
    db.commit()
    return user


# -------------------------------------------------------------------- admin inicial
def bootstrap_admin(db: Session) -> Usuario | None:
    """Garante o administrador definido em SIMETAL_ADMIN_EMAIL/PASSWORD (a senha só vale na criação)."""
    s = get_settings()
    if not s.admin_email or not s.admin_password:
        return None
    email = s.admin_email.strip().lower()
    user = db.scalar(select(Usuario).where(Usuario.email == email))
    if user is None:
        user = Usuario(nome=s.admin_name, email=email, senha_hash=hash_password(s.admin_password), papel="admin")
        db.add(user)
        db.commit()
        audit(db, "admin_criado", user=user, alvo=email, detalhe="criado na partida (variáveis de ambiente)")
    elif user.papel != "admin" or not user.ativo:
        user.papel, user.ativo = "admin", True
        db.commit()
        audit(db, "admin_promovido", user=user, alvo=email, detalhe="promovido na partida (variáveis de ambiente)")
    return user
