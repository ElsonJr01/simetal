"""Rotas web (HTML renderizado no servidor: Jinja2 + HTMX)."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

import numpy as np
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import auth_service, csrf, services
from app.auth_service import AuthError, client_ip
from app.config import get_settings
from app.core import InvalidInputError, SingularSystemError, diagnose
from app.core.iteration import FlowAction, IterationAction
from app.integrations import anm, openmeteo
from app.integrations.http import IntegrationError
from app.db import get_db
from app.deps import current_user, get_owned_campanha, get_owned_usina
from app.models import Ajuste, Campanha, Usina, Usuario
from app.security import COOKIE_NAME, create_token, hash_password
from app.seed import create_cambui

router = APIRouter(include_in_schema=False, dependencies=[Depends(csrf.csrf_protect)])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))


TIP_CONTEXT = {"usinas.html": "usinas", "usina.html": "fluxograma", "campanha.html": "medidas,resultado"}


def render(request: Request, name: str, status_code: int = 200, **ctx) -> HTMLResponse:
    settings = get_settings()
    token = request.cookies.get(csrf.COOKIE) or csrf.new_token()
    base = {
        "brand": settings.brand, "settings": settings, "csrf_token": token,
        "tip_context": TIP_CONTEXT.get(name, "geral"),
    }
    response = templates.TemplateResponse(request, name, {**base, **ctx}, status_code=status_code)
    csrf.ensure_cookie(response, request, token)
    return response


def _to_float(value: str | None) -> float | None:
    if value is None or not value.strip():
        return None
    try:
        return float(value.replace(",", "."))
    except ValueError as exc:
        raise services.ServiceError(f"Valor numérico inválido: '{value}'.") from exc


def _set_cookie(response: Response, user: Usuario) -> None:
    response.set_cookie(
        COOKIE_NAME, create_token(user.id), httponly=True, samesite="lax", secure=get_settings().env == "production"
    )


# ------------------------------------------------------------------- acesso
@router.get("/")
def home() -> RedirectResponse:
    return RedirectResponse("/usinas", status_code=303)


@router.get("/login")
def login_page(request: Request):
    return render(request, "login.html", mode="login")


@router.post("/login")
def login(request: Request, email: str = Form(...), senha: str = Form(...), db: Session = Depends(get_db)):
    try:
        user = auth_service.authenticate(db, email, senha, request)
    except AuthError as exc:
        return render(request, "login.html", 401, mode="login", error=str(exc), email=email)
    resp = RedirectResponse("/usinas", status_code=303)
    _set_cookie(resp, user)
    return resp


@router.get("/registrar")
def register_page(request: Request):
    return render(request, "login.html", mode="register")


@router.post("/registrar")
def register(
    request: Request,
    nome: str = Form(...),
    email: str = Form(...),
    senha: str = Form(...),
    db: Session = Depends(get_db),
):
    if not auth_service.registration_open(db):
        return render(request, "login.html", 403, mode="register", error="O cadastro está desabilitado. Fale com o administrador.")
    email = email.strip().lower()
    erro = None
    if len(nome.strip()) < 2:
        erro = "Informe o seu nome."
    elif "@" not in email or "." not in email.rsplit("@", 1)[-1]:
        erro = "Informe um e-mail válido."
    elif len(senha) < 8:
        erro = "A senha precisa ter pelo menos 8 caracteres."
    elif db.scalar(select(Usuario).where(Usuario.email == email)):
        erro = "Este e-mail já está cadastrado."
    if erro:
        return render(request, "login.html", 409 if "cadastrado" in erro else 422, mode="register", error=erro, email=email, nome=nome)
    user = Usuario(nome=nome.strip(), email=email, senha_hash=hash_password(senha))
    db.add(user)
    db.commit()
    auth_service.audit(db, "cadastro", user=user, alvo=email, ip=client_ip(request))
    resp = RedirectResponse("/usinas", status_code=303)
    _set_cookie(resp, user)
    return resp


@router.post("/logout")
def logout() -> RedirectResponse:
    resp = RedirectResponse("/login", status_code=303)
    resp.delete_cookie(COOKIE_NAME)
    return resp


# ------------------------------------------------------------------- usinas
@router.get("/usinas")
def usinas(request: Request, q: str = "", db: Session = Depends(get_db), user: Usuario = Depends(current_user)):
    stmt = select(Usina).where(Usina.dono_id == user.id).order_by(Usina.nome)
    if q:
        stmt = stmt.where(Usina.nome.ilike(f"%{q}%"))
    return render(request, "usinas.html", user=user, usinas=list(db.scalars(stmt)), q=q)


@router.post("/usinas")
def criar_usina(nome: str = Form(...), descricao: str = Form(""), db: Session = Depends(get_db), user: Usuario = Depends(current_user)):
    usina = Usina(nome=nome.strip(), descricao=descricao.strip(), dono_id=user.id)
    db.add(usina)
    db.commit()
    return RedirectResponse(f"/usinas/{usina.id}", status_code=303)


@router.post("/usinas/exemplo")
def usina_exemplo(db: Session = Depends(get_db), user: Usuario = Depends(current_user)):
    usina = create_cambui(db, user.id)
    return RedirectResponse(f"/usinas/{usina.id}", status_code=303)


@router.get("/usinas/{usina_id}")
def usina_page(request: Request, usina_id: int, db: Session = Depends(get_db), user: Usuario = Depends(current_user)):
    return _usina_response(request, get_owned_usina(db, user, usina_id), user)


def _usina_response(request: Request, usina: Usina, user: Usuario, error: str | None = None, alerts=None, texts=None):
    flows_text, ops_text = texts or services.flowsheet_text(usina)
    sheet = services.build_flowsheet(usina)
    if alerts is None:
        alerts = sheet.validate() if usina.operacoes else []
    matrix = sheet.matrix().astype(int).tolist() if usina.operacoes else []
    return render(
        request, "usina.html", user=user, usina=usina, flows_text=flows_text, ops_text=ops_text,
        matrix=matrix, alerts=alerts, error=error, status_code=422 if error else 200,
        anm=anm.catalog(), local_warning=request.query_params.get("aviso"),
    )


@router.post("/usinas/{usina_id}/fluxograma")
def salvar_fluxograma(
    request: Request, usina_id: int, fluxos: str = Form(""), operacoes: str = Form(""),
    db: Session = Depends(get_db), user: Usuario = Depends(current_user),
):
    usina = get_owned_usina(db, user, usina_id)
    try:
        flows, ops = services.parse_flowsheet_text(fluxos, operacoes)
        alerts = services.save_flowsheet(db, usina, flows, ops)
    except services.ServiceError as exc:
        return _usina_response(request, usina, user, error=str(exc), texts=(fluxos, operacoes))
    if any(a.severity.value == "error" for a in alerts):
        return _usina_response(request, usina, user, alerts=alerts, texts=(fluxos, operacoes), error="O fluxograma não foi salvo. Corrija os erros abaixo.")
    return RedirectResponse(f"/usinas/{usina.id}", status_code=303)


@router.post("/usinas/{usina_id}/local")
def salvar_local(
    request: Request, usina_id: int, uf: str = Form(...), municipio_ibge: int = Form(...),
    latitude: str = Form(""), longitude: str = Form(""),
    db: Session = Depends(get_db), user: Usuario = Depends(current_user),
):
    usina = get_owned_usina(db, user, usina_id)
    try:
        warning = services.set_location(db, usina, uf, municipio_ibge, _to_float(latitude), _to_float(longitude))
    except services.ServiceError as exc:
        return _usina_response(request, usina, user, error=str(exc))
    suffix = f"?aviso={quote(warning)}" if warning else ""
    return RedirectResponse(f"/usinas/{usina.id}{suffix}", status_code=303)


@router.get("/usinas/{usina_id}/clima")
def clima(request: Request, usina_id: int, db: Session = Depends(get_db), user: Usuario = Depends(current_user)):
    usina = get_owned_usina(db, user, usina_id)
    if usina.latitude is None or usina.longitude is None:
        return render(request, "partials/_clima.html", usina=usina, weather=None, error=None)
    try:
        weather = openmeteo.weather(usina.latitude, usina.longitude)
        return render(request, "partials/_clima.html", usina=usina, weather=weather, error=None)
    except IntegrationError as exc:
        return render(request, "partials/_clima.html", usina=usina, weather=None, error=str(exc))


@router.post("/usinas/{usina_id}/excluir")
def excluir_usina(usina_id: int, db: Session = Depends(get_db), user: Usuario = Depends(current_user)):
    db.delete(get_owned_usina(db, user, usina_id))
    db.commit()
    return RedirectResponse("/usinas", status_code=303)


@router.post("/usinas/{usina_id}/campanhas")
def nova_campanha(usina_id: int, nome: str = Form(...), db: Session = Depends(get_db), user: Usuario = Depends(current_user)):
    usina = get_owned_usina(db, user, usina_id)
    camp = Campanha(usina_id=usina.id, nome=nome.strip())
    db.add(camp)
    db.commit()
    return RedirectResponse(f"/campanhas/{camp.id}", status_code=303)


# ---------------------------------------------------------------- campanhas
def _result_ctx(camp: Campanha, componente: str, ajuste: Ajuste | None, error: str | None = None) -> dict:
    alerts = []
    chart = None
    if ajuste is not None:
        x = np.array([r.entrada for r in ajuste.resultados])
        xa = np.array([r.ajustado for r in ajuste.resultados])
        z = np.array([r.residuo_norm for r in ajuste.resultados])
        alerts = diagnose(x, xa, z, ajuste.chi2, ajuste.graus, is_grade=componente != services.MASSA)
        chart = {"nomes": [f"{r.fluxo_numero}" for r in ajuste.resultados], "entrada": x.tolist(), "ajustado": xa.tolist()}
    return {
        "camp": camp, "componente": componente, "ajuste": ajuste, "alerts": alerts, "chart": chart,
        "error": error, "max_iter": get_settings().max_iterations,
        "is_mass": componente == services.MASSA,
    }


@router.get("/campanhas/{campanha_id}")
def campanha_page(
    request: Request, campanha_id: int, componente: str = "massa",
    db: Session = Depends(get_db), user: Usuario = Depends(current_user),
):
    camp = get_owned_campanha(db, user, campanha_id)
    componente = componente.strip() or services.MASSA
    measures = services.measures_for(camp, componente)
    components = sorted({"massa", "cinzas", componente, *(m.componente for m in camp.medidas)})
    return render(
        request, "campanha.html", user=user, measures=measures, components=components,
        **_result_ctx(camp, componente, services.last_adjustment(camp, componente)),
    )


@router.post("/campanhas/{campanha_id}/medidas")
async def salvar_medidas(request: Request, campanha_id: int, db: Session = Depends(get_db), user: Usuario = Depends(current_user)):
    camp = get_owned_campanha(db, user, campanha_id)
    form = await request.form()
    componente = str(form.get("componente", "massa")).strip() or services.MASSA
    try:
        rows = [
            {
                "fluxo_id": f.id,
                "valor": _to_float(form.get(f"valor_{f.numero}")),
                "desvio": _to_float(form.get(f"desvio_{f.numero}")),
                "nao_amostrado": form.get(f"na_{f.numero}") == "on",
            }
            for f in camp.usina.fluxos
        ]
        services.save_measures(db, camp, componente, rows)
    except services.ServiceError as exc:
        raise HTTPException(422, str(exc)) from exc
    return RedirectResponse(f"/campanhas/{camp.id}?componente={componente}", status_code=303)


@router.post("/campanhas/{campanha_id}/ajustar")
def ajustar(
    request: Request, campanha_id: int, componente: str = Form("massa"),
    db: Session = Depends(get_db), user: Usuario = Depends(current_user),
):
    camp = get_owned_campanha(db, user, campanha_id)
    try:
        ajuste, _ = services.run_adjustment(db, camp, componente)
        ctx = _result_ctx(camp, componente, ajuste)
    except (services.ServiceError, InvalidInputError, SingularSystemError) as exc:
        ctx = _result_ctx(camp, componente, services.last_adjustment(camp, componente), error=str(exc))
    return render(request, "partials/_resultado.html", **ctx)


@router.post("/campanhas/{campanha_id}/iterar")
async def iterar(request: Request, campanha_id: int, db: Session = Depends(get_db), user: Usuario = Depends(current_user)):
    camp = get_owned_campanha(db, user, campanha_id)
    form = await request.form()
    componente = str(form.get("componente", "massa"))
    try:
        actions = {
            f.numero: FlowAction(
                IterationAction(str(form.get(f"acao_{f.numero}", "manter"))),
                _to_float(form.get(f"novo_valor_{f.numero}")),
                _to_float(form.get(f"novo_desvio_{f.numero}")),
            )
            for f in camp.usina.fluxos
        }
        ajuste, _ = services.run_adjustment(db, camp, componente, actions)
        ctx = _result_ctx(camp, componente, ajuste)
    except (services.ServiceError, InvalidInputError, SingularSystemError, ValueError) as exc:
        ctx = _result_ctx(camp, componente, services.last_adjustment(camp, componente), error=str(exc))
    return render(request, "partials/_resultado.html", **ctx)
