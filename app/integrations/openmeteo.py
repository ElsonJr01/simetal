"""Open-Meteo (clima, sem chave). Gratuito para uso NÃO comercial; atribuição obrigatória.
Docs: https://open-meteo.com/en/docs"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass

from app.config import get_settings
from app.integrations.http import IntegrationError, get_json

GEOCODING = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST = "https://api.open-meteo.com/v1/forecast"
PAST_DAYS = 7
FORECAST_DAYS = 3


def _norm(text: str | None) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    return "".join(c for c in text if not unicodedata.combining(c)).casefold().strip()


def geocode(municipio: str, estado_nome: str | None = None) -> tuple[float, float] | None:
    """Coordenadas aproximadas do município (centro). Prefere resultado do Brasil e do estado informado."""
    data = get_json(GEOCODING, {"name": municipio, "count": 10, "language": "pt"}, ttl=7 * 24 * 3600)
    results = [r for r in (data.get("results") or []) if r.get("country_code", "BR") == "BR"]
    if estado_nome:
        same_state = [r for r in results if _norm(r.get("admin1")) == _norm(estado_nome)]
        results = same_state or results
    if not results:
        return None
    return float(results[0]["latitude"]), float(results[0]["longitude"])


@dataclass(frozen=True)
class Day:
    date: str
    tmax: float | None
    tmin: float | None
    rain_mm: float | None


@dataclass(frozen=True)
class Weather:
    temperature_c: float | None
    rain_now_mm: float | None
    days: list[Day]  # últimos 7 dias + hoje + próximos dias
    rain_last_7d_mm: float
    rain_alert: bool
    alert_threshold_mm: float


def weather(lat: float, lon: float) -> Weather:
    params = {
        "latitude": round(lat, 4),
        "longitude": round(lon, 4),
        "current": "temperature_2m,precipitation",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
        "past_days": PAST_DAYS,
        "forecast_days": FORECAST_DAYS,
        "timezone": "auto",
    }
    data = get_json(FORECAST, params, ttl=15 * 60)
    try:
        daily = data["daily"]
        days = [
            Day(d, tmax, tmin, rain)
            for d, tmax, tmin, rain in zip(
                daily["time"], daily["temperature_2m_max"], daily["temperature_2m_min"], daily["precipitation_sum"],
                strict=True,
            )
        ]
        current = data.get("current") or {}
    except (KeyError, TypeError, ValueError) as exc:
        raise IntegrationError("Resposta inesperada do Open-Meteo.") from exc
    past = days[:PAST_DAYS]
    threshold = get_settings().rain_alert_mm
    recent = days[max(PAST_DAYS - 2, 0) : PAST_DAYS + 1]  # 2 dias anteriores + hoje
    return Weather(
        temperature_c=current.get("temperature_2m"),
        rain_now_mm=current.get("precipitation"),
        days=days,
        rain_last_7d_mm=round(sum(d.rain_mm or 0 for d in past), 1),
        rain_alert=any((d.rain_mm or 0) >= threshold for d in recent),
        alert_threshold_mm=threshold,
    )
