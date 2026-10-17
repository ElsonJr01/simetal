"""API REST /api/v1 (JSON). Documentação automática em /docs."""

from __future__ import annotations

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import services
from app.config import get_settings
from app.content.tips import get_tips
from app.integrations import anm, ibge, openmeteo
from app.integrations.http import IntegrationError
from app.core import Alert, InvalidInputError, SingularSystemError, mean_std, reconcile
from app.core.iteration import FlowAction, IterationAction
from app.db import get_db
from app.deps import current_user, get_owned_campanha, get_owned_usina
from app.models import Ajuste, Campanha, Usina, Usuario
from app.schemas import (
    AjusteIn,
    AjusteOut,
    AlertaOut,
    CampanhaIn,
    CampanhaOut,
    FluxogramaIn,
    FluxogramaOut,
    LocalIn,
    LoginIn,
    MedidaIn,
    OperacaoIn,
    ReconcileIn,
    RegistroIn,
    ResultadoOut,
    TokenOut,
    UsinaIn,
    UsinaOut,
)
from app.security import COOKIE_NAME, create_token, hash_password, verify_password

router = APIRouter(prefix="/api/v1")


def _alerts(alerts: list[Alert]) -> list[AlertaOut]:
    return [AlertaOut(severidade=a.severity.value, mensagem=a.message, fluxo=a.flow) for a in alerts]


def _ajuste_out(ajuste: Ajuste, alerts: list[Alert]) -> AjusteOut:
    return AjusteOut(
        id=ajuste.id,
        componente=ajuste.componente,
        iteracao=ajuste.iteracao,
        chi2=ajuste.chi2,
        graus_liberdade=ajuste.graus,
        convergiu=ajuste.convergiu,
        resultados=[
            ResultadoOut(
                fluxo=r.fluxo_numero,
                nome=r.fluxo_nome,
                entrada=r.entrada,
                desvio=r.desvio,
                ajustado=r.ajustado,
                residuo_normalizado=r.residuo_norm,
                percentual=r.percentual,
                acao=r.acao,
            )
            for r in ajuste.resultados
        ],
        alertas=_alerts(alerts),
    )


def _fail(exc: Exception) -> HTTPException:
    return HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))


@router.get("/health", tags=["sistema"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/dicas", tags=["sistema"])
def dicas(contexto: str | None = None, nivel: str | None = None) -> list[dict]:
    """API aberta (sem login): dicas e curiosidades do mascote. `contexto` aceita lista separada por vírgula."""
    return [dict(t) for t in get_tips(contexto.split(",") if contexto else None, nivel)]


# ------------------------------------------------------- dados públicos (fontes abertas)
@router.get("/fontes", tags=["dados públicos"])
def fontes() -> dict:
    """Catálogo das fontes públicas usadas e links verificados dos dados abertos da ANM (sem login)."""
    return {
        "ibge": {"nome": "IBGE - API de Localidades", "url": "https://servicodados.ibge.gov.br/api/docs/localidades", "uso": "estado e município da usina"},
        "open_meteo": {"nome": "Open-Meteo", "url": "https://open-meteo.com", "uso": "temperatura e chuva no local da usina",
                       "licenca": "gratuito para uso não comercial; atribuição obrigatória"},
        "anm": anm.catalog(),
    }


@router.get("/ibge/estados", tags=["dados públicos"])
def ibge_estados(_: Usuario = Depends(current_user)) -> list[dict]:
    try:
        return ibge.estados()
    except IntegrationError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc


@router.get("/ibge/estados/{uf}/municipios", tags=["dados públicos"])
def ibge_municipios(uf: str, _: Usuario = Depends(current_user)) -> list[dict]:
    try:
        return ibge.municipios(uf)
    except IntegrationError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc


@router.put("/usinas/{usina_id}/local", response_model=UsinaOut, tags=["dados públicos"])
def definir_local(usina_id: int, data: LocalIn, db: Session = Depends(get_db), user: Usuario = Depends(current_user)):
    usina = get_owned_usina(db, user, usina_id)
    try:
        services.set_location(db, usina, data.uf, data.municipio_ibge, data.latitude, data.longitude)
    except services.ServiceError as exc:
        raise _fail(exc) from exc
    return usina


@router.get("/usinas/{usina_id}/clima", tags=["dados públicos"])
def clima_da_usina(usina_id: int, db: Session = Depends(get_db), user: Usuario = Depends(current_user)) -> dict:
    usina = get_owned_usina(db, user, usina_id)
    if usina.latitude is None or usina.longitude is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Defina o local da usina para consultar o clima.")
    try:
        w = openmeteo.weather(usina.latitude, usina.longitude)
    except IntegrationError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc
    return {
        "local": f"{usina.municipio_nome}/{usina.uf}",
        "temperatura_c": w.temperature_c,
        "chuva_agora_mm": w.rain_now_mm,
        "chuva_ultimos_7_dias_mm": w.rain_last_7d_mm,
        "alerta_chuva": w.rain_alert,
        "limite_alerta_mm": w.alert_threshold_mm,
        "dias": [{"data": d.date, "tmax": d.tmax, "tmin": d.tmin, "chuva_mm": d.rain_mm} for d in w.days],
        "atribuicao": "Dados meteorológicos: Open-Meteo.com",
    }


# ------------------------------------------------------------------ auth (UC01)
@router.post("/auth/registro", response_model=TokenOut, status_code=201, tags=["auth"])
def registro(data: RegistroIn, response: Response, db: Session = Depends(get_db)) -> TokenOut:
    if not get_settings().allow_registration:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cadastro desabilitado.")
    if db.scalar(select(Usuario).where(Usuario.email == data.email.lower())):
        raise HTTPException(status.HTTP_409_CONFLICT, "E-mail já cadastrado.")
    user = Usuario(nome=data.nome, email=data.email.lower(), senha_hash=hash_password(data.senha))
    db.add(user)
    db.commit()
    token = create_token(user.id)
    response.set_cookie(COOKIE_NAME, token, httponly=True, samesite="lax", secure=get_settings().env == "production")
    return TokenOut(access_token=token)


@router.post("/auth/login", response_model=TokenOut, tags=["auth"])
def login(data: LoginIn, response: Response, db: Session = Depends(get_db)) -> TokenOut:
    user = db.scalar(select(Usuario).where(Usuario.email == data.email.lower()))
    if user is None or not verify_password(data.senha, user.senha_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "E-mail ou senha incorretos.")
    token = create_token(user.id)
    response.set_cookie(COOKIE_NAME, token, httponly=True, samesite="lax", secure=get_settings().env == "production")
    return TokenOut(access_token=token)


@router.post("/auth/logout", status_code=204, response_class=Response, response_model=None, tags=["auth"])
def logout(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME)


# ------------------------------------------------------------------ usinas (UC02)
@router.get("/usinas", response_model=list[UsinaOut], tags=["usinas"])
def listar_usinas(q: str | None = None, db: Session = Depends(get_db), user: Usuario = Depends(current_user)):
    stmt = select(Usina).where(Usina.dono_id == user.id).order_by(Usina.nome)
    if q:
        stmt = stmt.where(Usina.nome.ilike(f"%{q}%"))
    return list(db.scalars(stmt))


@router.post("/usinas", response_model=UsinaOut, status_code=201, tags=["usinas"])
def criar_usina(data: UsinaIn, db: Session = Depends(get_db), user: Usuario = Depends(current_user)):
    usina = Usina(nome=data.nome, descricao=data.descricao, dono_id=user.id)
    db.add(usina)
    db.commit()
    return usina


@router.get("/usinas/{usina_id}", response_model=UsinaOut, tags=["usinas"])
def obter_usina(usina_id: int, db: Session = Depends(get_db), user: Usuario = Depends(current_user)):
    return get_owned_usina(db, user, usina_id)


@router.delete("/usinas/{usina_id}", status_code=204, response_class=Response, response_model=None, tags=["usinas"])
def excluir_usina(usina_id: int, db: Session = Depends(get_db), user: Usuario = Depends(current_user)) -> None:
    db.delete(get_owned_usina(db, user, usina_id))
    db.commit()


# ------------------------------------------------------- fluxograma (UC03/UC04)
def _fluxograma_out(usina: Usina, alerts: list[Alert]) -> FluxogramaOut:
    sheet = services.build_flowsheet(usina)
    return FluxogramaOut(
        fluxos=list(sheet.flows),
        operacoes=[
            OperacaoIn(nome=o.name, entradas=[i + 1 for i in o.inputs], saidas=[i + 1 for i in o.outputs])
            for o in sheet.operations
        ],
        matriz_m=sheet.matrix().tolist() if sheet.operations else [],
        alertas=_alerts(alerts),
    )


@router.put("/usinas/{usina_id}/fluxograma", response_model=FluxogramaOut, tags=["usinas"])
def definir_fluxograma(usina_id: int, data: FluxogramaIn, db: Session = Depends(get_db), user: Usuario = Depends(current_user)):
    usina = get_owned_usina(db, user, usina_id)
    try:
        alerts = services.save_flowsheet(db, usina, data.fluxos, [(o.nome, o.entradas, o.saidas) for o in data.operacoes])
    except services.ServiceError as exc:
        raise _fail(exc) from exc
    if any(a.severity.value == "error" for a in alerts):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, [a.message for a in alerts])
    return _fluxograma_out(usina, alerts)


@router.get("/usinas/{usina_id}/fluxograma", response_model=FluxogramaOut, tags=["usinas"])
def obter_fluxograma(usina_id: int, db: Session = Depends(get_db), user: Usuario = Depends(current_user)):
    usina = get_owned_usina(db, user, usina_id)
    return _fluxograma_out(usina, services.build_flowsheet(usina).validate() if usina.operacoes else [])


# ---------------------------------------------------- campanhas e medidas (UC05)
@router.post("/usinas/{usina_id}/campanhas", response_model=CampanhaOut, status_code=201, tags=["campanhas"])
def criar_campanha(usina_id: int, data: CampanhaIn, db: Session = Depends(get_db), user: Usuario = Depends(current_user)):
    usina = get_owned_usina(db, user, usina_id)
    camp = Campanha(usina_id=usina.id, nome=data.nome)
    db.add(camp)
    db.commit()
    return camp


@router.put("/campanhas/{campanha_id}/medidas/{componente}", status_code=204, response_class=Response, response_model=None, tags=["campanhas"])
def registrar_medidas(
    campanha_id: int, componente: str, medidas: list[MedidaIn], db: Session = Depends(get_db), user: Usuario = Depends(current_user)
) -> None:
    camp = get_owned_campanha(db, user, campanha_id)
    by_num = {f.numero: f.id for f in camp.usina.fluxos}
    rows = []
    for m in medidas:
        if m.fluxo not in by_num:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Fluxo {m.fluxo} não existe.")
        rows.append({"fluxo_id": by_num[m.fluxo], "valor": m.valor, "desvio": m.desvio, "nao_amostrado": m.nao_amostrado})
    try:
        services.save_measures(db, camp, componente, rows)
    except services.ServiceError as exc:
        raise _fail(exc) from exc


@router.post("/estatistica/resumo", tags=["campanhas"])
def resumo_estatistico(amostras: list[float]) -> dict[str, float]:
    """UC06: média e desvio-padrão amostral."""
    try:
        mean, std = mean_std(amostras)
    except InvalidInputError as exc:
        raise _fail(exc) from exc
    return {"media": mean, "desvio_padrao": std}


# ----------------------------------------------------------- ajustes (UC08-UC12)
@router.post("/campanhas/{campanha_id}/ajustes", response_model=AjusteOut, status_code=201, tags=["ajustes"])
def executar_ajuste(campanha_id: int, data: AjusteIn, db: Session = Depends(get_db), user: Usuario = Depends(current_user)):
    camp = get_owned_campanha(db, user, campanha_id)
    actions = None
    if data.acoes is not None:
        actions = {a.fluxo: FlowAction(IterationAction(a.acao), a.valor, a.desvio) for a in data.acoes}
    try:
        ajuste, alerts = services.run_adjustment(db, camp, data.componente, actions)
    except (services.ServiceError, InvalidInputError, SingularSystemError) as exc:
        raise _fail(exc) from exc
    return _ajuste_out(ajuste, alerts)


@router.get("/ajustes/{ajuste_id}", response_model=AjusteOut, tags=["ajustes"])
def obter_ajuste(ajuste_id: int, db: Session = Depends(get_db), user: Usuario = Depends(current_user)):
    ajuste = db.get(Ajuste, ajuste_id)
    if ajuste is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ajuste não encontrado.")
    get_owned_campanha(db, user, ajuste.campanha_id)
    x = np.array([r.entrada for r in ajuste.resultados])
    xa = np.array([r.ajustado for r in ajuste.resultados])
    z = np.array([r.residuo_norm for r in ajuste.resultados])
    from app.core import diagnose

    alerts = diagnose(x, xa, z, ajuste.chi2, ajuste.graus, is_grade=ajuste.componente != services.MASSA)
    return _ajuste_out(ajuste, alerts)


@router.post("/reconcile", tags=["ajustes"])
def reconciliar_avulso(data: ReconcileIn) -> dict:
    """Cálculo avulso, sem login nem banco: útil para integração e testes."""
    try:
        res = reconcile(np.array(data.matriz_m), np.array(data.valores), np.array(data.desvios))
    except (InvalidInputError, SingularSystemError) as exc:
        raise _fail(exc) from exc
    return {
        "ajustados": res.adjusted.tolist(),
        "residuo_antes": res.residual_before.tolist(),
        "chi2": res.chi2,
        "graus_liberdade": res.dof,
        "residuos_normalizados": res.normalized_residuals.tolist(),
    }
