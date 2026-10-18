"""Páginas públicas de ajuda: guia, glossário, método, boas práticas, ferramentas e sobre."""

from __future__ import annotations

import math

import numpy as np
from fastapi import APIRouter, Depends, Form, Request

from app import csrf, services
from app.content.faq import FAQ
from app.content.glossary import by_category, slug
from app.core import InvalidInputError, Flowsheet, Operation, reconcile, reconcile_component
from app.deps import optional_user
from app.models import Usuario
from app.routers.web import render
from app.seed import CAMBUI_CINZAS, CAMBUI_FLOWS, CAMBUI_MASSA

router = APIRouter(include_in_schema=False, dependencies=[Depends(csrf.csrf_protect)])


@router.get("/ajuda")
def guia(request: Request, user: Usuario | None = Depends(optional_user)):
    return render(request, "ajuda/guia.html", user=user, secao="guia")


@router.get("/ajuda/glossario")
def glossario(request: Request, user: Usuario | None = Depends(optional_user)):
    grupos = [(cat, terms) for cat, terms in by_category()]
    return render(request, "ajuda/glossario.html", user=user, secao="glossario", grupos=grupos, slug=slug)


def _exemplo_cambui() -> dict:
    """Roda o exemplo da monografia com o próprio núcleo, para a página mostrar números reais."""
    sheet = Flowsheet(tuple(CAMBUI_FLOWS), (Operation("Ciclone", (0,), (1, 2)), Operation("Espiral", (2,), (3, 4, 5))))
    m = sheet.matrix()
    x = np.array([v for v, _ in CAMBUI_MASSA]); s = np.array([d for _, d in CAMBUI_MASSA])
    mass = reconcile(m, x, s)
    ash = reconcile_component(m, mass.adjusted, np.array([v for v, _ in CAMBUI_CINZAS]), np.array([d for _, d in CAMBUI_CINZAS]))
    rows = [
        {"n": i + 1, "nome": CAMBUI_FLOWS[i], "x": x[i], "s": s[i], "xa": mass.adjusted[i], "z": mass.normalized_residuals[i]}
        for i in range(len(x))
    ]
    return {
        "rows": rows,
        "antes_op1": float(x[0] - x[1] - x[2]), "antes_op2": float(x[2] - x[3] - x[4] - x[5]),
        "depois_op1": float(mass.adjusted[0] - mass.adjusted[1] - mass.adjusted[2]),
        "depois_op2": float(mass.adjusted[2] - mass.adjusted[3] - mass.adjusted[4] - mass.adjusted[5]),
        "chi2": mass.chi2, "dof": mass.dof, "cinzas_alim": float(ash.adjusted[0]), "cinzas_conc": float(ash.adjusted[5]),
    }


@router.get("/ajuda/metodo")
def metodo(request: Request, user: Usuario | None = Depends(optional_user)):
    return render(request, "ajuda/metodo.html", user=user, secao="metodo", ex=_exemplo_cambui())


@router.get("/ajuda/boas-praticas")
def boas_praticas(request: Request, user: Usuario | None = Depends(optional_user)):
    return render(request, "ajuda/boas_praticas.html", user=user, secao="praticas", faq=FAQ)


@router.get("/ajuda/amostras")
def amostras_page(request: Request, user: Usuario | None = Depends(optional_user)):
    return render(request, "ajuda/amostras.html", user=user, secao="amostras")


@router.post("/ajuda/amostras")
def amostras_calcular(request: Request, texto: str = Form("")):
    try:
        values = [services.parse_decimal(t) for t in texto.replace(";", " ").replace("\t", " ").split() if t.strip()]
        from app.core import mean_std

        mean, std = mean_std(values)
        n = len(values)
        res = {
            "n": n, "media": mean, "s": std, "cv": 100 * std / abs(mean) if mean else None,
            "sem": std / math.sqrt(n), "minimo": min(values), "maximo": max(values),
        }
        return render(request, "ajuda/_amostras_resultado.html", res=res, erro=None)
    except (services.ServiceError, InvalidInputError) as exc:
        return render(request, "ajuda/_amostras_resultado.html", res=None, erro=str(exc))


@router.get("/sobre")
def sobre(request: Request, user: Usuario | None = Depends(optional_user)):
    return render(request, "ajuda/sobre.html", user=user, secao="sobre")
