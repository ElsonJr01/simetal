"""IBGE - API de Localidades (aberta, sem chave).
Docs: https://servicodados.ibge.gov.br/api/docs/localidades"""

from __future__ import annotations

import re

from app.integrations.http import IntegrationError, get_json

BASE = "https://servicodados.ibge.gov.br/api/v1/localidades"
DAY = 24 * 3600


def estados() -> list[dict]:
    """[{'id': 15, 'sigla': 'PA', 'nome': 'Pará'}, ...] ordenado por nome."""
    data = get_json(f"{BASE}/estados", ttl=DAY)
    try:
        items = [{"id": int(e["id"]), "sigla": e["sigla"], "nome": e["nome"]} for e in data]
    except (KeyError, TypeError, ValueError) as exc:
        raise IntegrationError("Resposta inesperada do IBGE (estados).") from exc
    return sorted(items, key=lambda e: e["nome"])


def municipios(uf: str) -> list[dict]:
    """[{'id': 1504208, 'nome': 'Marabá'}, ...] do estado `uf` (sigla)."""
    if not re.fullmatch(r"[A-Za-z]{2}", uf or ""):
        raise IntegrationError("UF inválida.")
    data = get_json(f"{BASE}/estados/{uf.upper()}/municipios", ttl=DAY)
    try:
        items = [{"id": int(m["id"]), "nome": m["nome"]} for m in data]
    except (KeyError, TypeError, ValueError) as exc:
        raise IntegrationError("Resposta inesperada do IBGE (municípios).") from exc
    return sorted(items, key=lambda m: m["nome"])
