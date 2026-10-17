"""Cliente HTTP mínimo com timeout e cache em memória (por instância serverless)."""

from __future__ import annotations

import time
from typing import Any

from app.config import get_settings


class IntegrationError(Exception):
    """Falha ao consultar uma fonte pública externa."""


_cache: dict[tuple, tuple[float, Any]] = {}


def clear_cache() -> None:
    _cache.clear()


def _request(url: str, params: dict[str, Any] | None) -> Any:
    """Chamada real de rede. Os testes substituem esta função."""
    import httpx

    try:
        resp = httpx.get(
            url,
            params=params,
            timeout=get_settings().http_timeout,
            headers={"User-Agent": "SIMETAL/0.1 (+dados publicos)"},
        )
        resp.raise_for_status()
        return resp.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise IntegrationError(f"Não foi possível consultar {url.split('/')[2]}: {exc.__class__.__name__}") from exc


def get_json(url: str, params: dict[str, Any] | None = None, ttl: float = 0) -> Any:
    if not get_settings().integrations_enabled:
        raise IntegrationError("Integrações com dados públicos estão desabilitadas.")
    key = (url, tuple(sorted((params or {}).items())))
    now = time.monotonic()
    hit = _cache.get(key)
    if ttl and hit and now - hit[0] < ttl:
        return hit[1]
    data = _request(url, params)
    if ttl:
        _cache[key] = (now, data)
    return data
