"""Área administrativa /admin (somente perfil 'admin')."""

from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app import admin_service as svc
from app import auth_service, csrf
from app.admin_service import AdminError
from app.auth_service import client_ip
from app.db import get_db
from app.deps import require_admin
from app.models import Usuario
from app.routers.web import render

router = APIRouter(prefix="/admin", include_in_schema=False, dependencies=[Depends(csrf.csrf_protect), Depends(require_admin)])


def _back(path: str, msg: str | None = None, erro: str | None = None) -> RedirectResponse:
    base = "/admin" + (f"/{path}" if path else "")
    qs = f"?msg={quote(msg)}" if msg else (f"?erro={quote(erro)}" if erro else "")
    return RedirectResponse(base + qs, status_code=303)


def _flash(request: Request) -> dict:
    return {"msg": request.query_params.get("msg"), "erro": request.query_params.get("erro")}


@router.get("")
def painel(request: Request, db: Session = Depends(get_db), admin: Usuario = Depends(require_admin)):
    return render(
        request, "admin/painel.html", user=admin, secao="painel", d=svc.dashboard(db),
        cadastro_aberto=auth_service.registration_open(db), **_flash(request),
    )


@router.post("/cadastro")
def alternar_cadastro(request: Request, abrir: str = Form(...), db: Session = Depends(get_db), admin: Usuario = Depends(require_admin)):
    open_ = abrir == "1"
    auth_service.set_registration(db, open_)
    auth_service.audit(db, "cadastro_aberto" if open_ else "cadastro_fechado", user=admin, ip=client_ip(request))
    return _back("", msg="Cadastro de novos usuários " + ("aberto." if open_ else "fechado."))


@router.post("/testar-fontes")
def testar_fontes(request: Request, admin: Usuario = Depends(require_admin)):
    return render(request, "admin/_fontes.html", resultados=svc.check_sources())


# ---------------------------------------------------------------- usuários
@router.get("/usuarios")
def usuarios(request: Request, q: str = "", pagina: int = 1, db: Session = Depends(get_db), admin: Usuario = Depends(require_admin)):
    items, page, pages = svc.list_users(db, q, pagina)
    return render(
        request, "admin/usuarios.html", user=admin, secao="usuarios", usuarios=items, q=q, page=page, pages=pages,
        papeis=svc.ROLES, is_locked=svc.is_locked, **_flash(request),
    )


def _act(path: str, fn, *args):
    try:
        return fn(*args), None
    except AdminError as exc:
        return None, str(exc)


@router.post("/usuarios/{user_id}/papel")
def mudar_papel(request: Request, user_id: int, papel: str = Form(...), db: Session = Depends(get_db), admin: Usuario = Depends(require_admin)):
    res, err = _act("usuarios", svc.set_role, db, admin, user_id, papel, client_ip(request))
    return _back("usuarios", msg=f"Perfil de {res.email} alterado para {papel}." if res else None, erro=err)


@router.post("/usuarios/{user_id}/ativo")
def ativar(request: Request, user_id: int, ativo: str = Form(...), db: Session = Depends(get_db), admin: Usuario = Depends(require_admin)):
    res, err = _act("usuarios", svc.set_active, db, admin, user_id, ativo == "1", client_ip(request))
    return _back("usuarios", msg=f"Conta de {res.email} {'ativada' if res.ativo else 'desativada'}." if res else None, erro=err)


@router.post("/usuarios/{user_id}/desbloquear")
def desbloquear(request: Request, user_id: int, db: Session = Depends(get_db), admin: Usuario = Depends(require_admin)):
    res, err = _act("usuarios", svc.unlock, db, admin, user_id, client_ip(request))
    return _back("usuarios", msg=f"Conta de {res.email} desbloqueada." if res else None, erro=err)


@router.post("/usuarios/{user_id}/senha")
def redefinir_senha(request: Request, user_id: int, db: Session = Depends(get_db), admin: Usuario = Depends(require_admin)):
    res, err = _act("usuarios", svc.reset_password, db, admin, user_id, client_ip(request))
    if err:
        return _back("usuarios", erro=err)
    user, temp = res
    items, page, pages = svc.list_users(db, "", 1)
    return render(
        request, "admin/usuarios.html", user=admin, secao="usuarios", usuarios=items, q="", page=page, pages=pages,
        papeis=svc.ROLES, is_locked=svc.is_locked, senha_temp=temp, senha_email=user.email, msg=None, erro=None,
    )


@router.post("/usuarios/{user_id}/excluir")
def excluir_usuario(request: Request, user_id: int, db: Session = Depends(get_db), admin: Usuario = Depends(require_admin)):
    res, err = _act("usuarios", svc.delete_user, db, admin, user_id, client_ip(request))
    return _back("usuarios", msg=f"Usuário {res} excluído, com as suas usinas." if res else None, erro=err)


# ------------------------------------------------------------------ usinas
@router.get("/usinas")
def usinas(request: Request, q: str = "", pagina: int = 1, db: Session = Depends(get_db), admin: Usuario = Depends(require_admin)):
    items, page, pages = svc.list_usinas(db, q, pagina)
    return render(request, "admin/usinas.html", user=admin, secao="usinas", usinas=items, q=q, page=page, pages=pages, **_flash(request))


@router.post("/usinas/{usina_id}/excluir")
def excluir_usina(request: Request, usina_id: int, db: Session = Depends(get_db), admin: Usuario = Depends(require_admin)):
    res, err = _act("usinas", svc.delete_usina, db, admin, usina_id, client_ip(request))
    return _back("usinas", msg=f"Usina {res} excluída." if res else None, erro=err)


# --------------------------------------------------------------- auditoria
@router.get("/auditoria")
def auditoria(request: Request, pagina: int = 1, acao: str = "", db: Session = Depends(get_db), admin: Usuario = Depends(require_admin)):
    items, page, pages = svc.list_audit(db, pagina, acao)
    return render(request, "admin/auditoria.html", user=admin, secao="auditoria", eventos=items, page=page, pages=pages, acao=acao, **_flash(request))


# ------------------------------------------------------- identidade visual
@router.get("/identidade")
def identidade(request: Request, admin: Usuario = Depends(require_admin)):
    return render(request, "admin/identidade.html", user=admin, secao="identidade", itens=svc.brand_status(), **_flash(request))
