"""Regras da área administrativa (/admin)."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, or_, select, text
from sqlalchemy.orm import Session

from app import __version__, brand
from app.auth_service import audit, aware
from app.config import get_settings
from app.integrations import ibge, openmeteo
from app.integrations.http import IntegrationError, _request
from app.models import Ajuste, Auditoria, Campanha, Usina, Usuario
from app.security import hash_password

ROLES = ("admin", "engenheiro", "visitante")


class AdminError(Exception):
    """Operação administrativa recusada, com mensagem para o painel."""


def paginate(db: Session, stmt, page: int) -> tuple[list, int, int]:
    size = get_settings().page_size
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    pages = max((total + size - 1) // size, 1)
    page = min(max(page, 1), pages)
    items = list(db.scalars(stmt.limit(size).offset((page - 1) * size)))
    return items, page, pages


def dashboard(db: Session) -> dict:
    now = datetime.now(UTC)
    week = now - timedelta(days=7)

    def count(model, *where):
        return db.scalar(select(func.count()).select_from(model).where(*where)) or 0

    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:  # noqa: BLE001
        db_ok = False
    s = get_settings()
    return {
        "versao": __version__,
        "ambiente": s.env,
        "banco_ok": db_ok,
        "banco": s.sqlalchemy_url.split(":")[0],
        "usuarios": count(Usuario),
        "usuarios_ativos": count(Usuario, Usuario.ativo.is_(True)),
        "admins": count(Usuario, Usuario.papel == "admin"),
        "usinas": count(Usina),
        "campanhas": count(Campanha),
        "ajustes": count(Ajuste),
        "ajustes_7d": count(Ajuste, Ajuste.criado_em >= week),
        "falhas_login_7d": count(Auditoria, Auditoria.acao == "login_falha", Auditoria.criado_em >= week),
        "integracoes": s.integrations_enabled,
        "vlibras": s.vlibras_enabled,
        "mascote": s.mascot_enabled,
    }


def check_sources() -> list[dict]:
    """Teste ao vivo (ignora o cache) de IBGE e Open-Meteo."""
    out = []
    if not get_settings().integrations_enabled:
        return [{"fonte": "Integrações", "ok": False, "detalhe": "desabilitadas na configuração"}]
    probes = [
        ("IBGE - Localidades", lambda: _request(f"{ibge.BASE}/estados/PA", None)),
        ("Open-Meteo - Geocodificação", lambda: _request(openmeteo.GEOCODING, {"name": "Marabá", "count": 1, "language": "pt"})),
    ]
    for name, fn in probes:
        try:
            fn()
            out.append({"fonte": name, "ok": True, "detalhe": "respondeu normalmente"})
        except IntegrationError as exc:
            out.append({"fonte": name, "ok": False, "detalhe": str(exc)})
    return out


# ------------------------------------------------------------------- usuários
def list_users(db: Session, q: str, page: int):
    stmt = select(Usuario).order_by(Usuario.criado_em.desc())
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(Usuario.nome.ilike(like), Usuario.email.ilike(like)))
    return paginate(db, stmt, page)


def _admins_left(db: Session, excluding: int) -> int:
    return db.scalar(
        select(func.count()).select_from(Usuario).where(Usuario.papel == "admin", Usuario.ativo.is_(True), Usuario.id != excluding)
    ) or 0


def _target(db: Session, actor: Usuario, user_id: int) -> Usuario:
    user = db.get(Usuario, user_id)
    if user is None:
        raise AdminError("Usuário não encontrado.")
    return user


def set_role(db: Session, actor: Usuario, user_id: int, papel: str, ip: str) -> Usuario:
    user = _target(db, actor, user_id)
    if papel not in ROLES:
        raise AdminError("Perfil inválido.")
    if user.id == actor.id and papel != "admin":
        raise AdminError("Você não pode remover o seu próprio perfil de administrador.")
    if user.papel == "admin" and papel != "admin" and _admins_left(db, user.id) == 0:
        raise AdminError("É preciso manter ao menos um administrador ativo.")
    old, user.papel = user.papel, papel
    db.commit()
    audit(db, "perfil_alterado", user=actor, alvo=user.email, detalhe=f"{old} → {papel}", ip=ip)
    return user


def set_active(db: Session, actor: Usuario, user_id: int, ativo: bool, ip: str) -> Usuario:
    user = _target(db, actor, user_id)
    if not ativo and user.id == actor.id:
        raise AdminError("Você não pode desativar a sua própria conta.")
    if not ativo and user.papel == "admin" and _admins_left(db, user.id) == 0:
        raise AdminError("É preciso manter ao menos um administrador ativo.")
    user.ativo = ativo
    db.commit()
    audit(db, "conta_ativada" if ativo else "conta_desativada", user=actor, alvo=user.email, ip=ip)
    return user


def unlock(db: Session, actor: Usuario, user_id: int, ip: str) -> Usuario:
    user = _target(db, actor, user_id)
    user.falhas_login, user.bloqueado_ate = 0, None
    db.commit()
    audit(db, "conta_desbloqueada", user=actor, alvo=user.email, ip=ip)
    return user


def reset_password(db: Session, actor: Usuario, user_id: int, ip: str) -> tuple[Usuario, str]:
    """Gera uma senha temporária (mostrada UMA vez ao administrador)."""
    user = _target(db, actor, user_id)
    temp = secrets.token_urlsafe(9)
    user.senha_hash = hash_password(temp)
    user.falhas_login, user.bloqueado_ate = 0, None
    db.commit()
    audit(db, "senha_redefinida", user=actor, alvo=user.email, ip=ip)
    return user, temp


def delete_user(db: Session, actor: Usuario, user_id: int, ip: str) -> str:
    user = _target(db, actor, user_id)
    if user.id == actor.id:
        raise AdminError("Você não pode excluir a sua própria conta.")
    if user.papel == "admin" and _admins_left(db, user.id) == 0:
        raise AdminError("É preciso manter ao menos um administrador ativo.")
    email = user.email
    db.delete(user)  # as usinas do usuário são removidas em cascata
    db.commit()
    audit(db, "usuario_excluido", user=actor, alvo=email, ip=ip)
    return email


def is_locked(user: Usuario) -> bool:
    until = aware(user.bloqueado_ate)
    return bool(until and until > datetime.now(UTC))


# --------------------------------------------------------------------- usinas
def list_usinas(db: Session, q: str, page: int):
    stmt = select(Usina).order_by(Usina.criada_em.desc())
    if q:
        stmt = stmt.where(Usina.nome.ilike(f"%{q.strip()}%"))
    return paginate(db, stmt, page)


def delete_usina(db: Session, actor: Usuario, usina_id: int, ip: str) -> str:
    usina = db.get(Usina, usina_id)
    if usina is None:
        raise AdminError("Usina não encontrada.")
    nome = usina.nome
    db.delete(usina)
    db.commit()
    audit(db, "usina_excluida", user=actor, alvo=nome, ip=ip)
    return nome


def list_audit(db: Session, page: int, acao: str = ""):
    stmt = select(Auditoria).order_by(Auditoria.id.desc())
    if acao:
        stmt = stmt.where(Auditoria.acao == acao)
    return paginate(db, stmt, page)


def brand_status() -> list[dict]:
    return brand.status()
