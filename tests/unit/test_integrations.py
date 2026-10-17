"""Integrações com fontes públicas: a rede é substituída por respostas gravadas."""

import pytest

from app.integrations import anm, http, ibge, openmeteo
from app.integrations.http import IntegrationError

ESTADOS = [{"id": 15, "sigla": "PA", "nome": "Pará"}, {"id": 11, "sigla": "RO", "nome": "Rondônia"}]
MUN_PA = [{"id": 1504208, "nome": "Marabá"}, {"id": 1500107, "nome": "Abaetetuba"}]
GEO = {"results": [
    {"latitude": -5.0, "longitude": -49.0, "admin1": "Pará", "country_code": "BR"},
    {"latitude": 1.0, "longitude": 2.0, "admin1": "Outro", "country_code": "PT"},
]}


def forecast(rain):
    days = [f"2026-10-{d:02d}" for d in range(4, 14)]  # 7 passados + hoje + 2
    return {
        "current": {"temperature_2m": 31.5, "precipitation": 0.0},
        "daily": {"time": days, "temperature_2m_max": [33.0] * 10, "temperature_2m_min": [24.0] * 10, "precipitation_sum": rain},
    }


@pytest.fixture()
def fake_net(monkeypatch):
    calls = []

    def fake(url, params):
        calls.append(url)
        if url.endswith("/estados"):
            return ESTADOS
        if url.endswith("/estados/PA/municipios"):
            return MUN_PA
        if "geocoding" in url:
            return GEO
        if "forecast" in url:
            return fake.forecast
        raise AssertionError(url)

    fake.forecast = forecast([0.0] * 10)
    monkeypatch.setattr(http, "_request", fake)
    fake.calls = calls
    return fake


def test_ibge_estados_municipios_sorted_and_cached(fake_net):
    assert [e["sigla"] for e in ibge.estados()] == ["PA", "RO"]
    assert [m["nome"] for m in ibge.municipios("pa")] == ["Abaetetuba", "Marabá"]
    ibge.estados()
    assert fake_net.calls.count("https://servicodados.ibge.gov.br/api/v1/localidades/estados") == 1  # cache
    with pytest.raises(IntegrationError):
        ibge.municipios("../x")


def test_geocode_prefers_brazil_and_state(fake_net):
    assert openmeteo.geocode("Marabá", "Pará") == (-5.0, -49.0)


def test_weather_summary_and_rain_alert(fake_net):
    w = openmeteo.weather(-5.0, -49.0)
    assert w.temperature_c == 31.5 and w.rain_last_7d_mm == 0 and not w.rain_alert and len(w.days) == 10
    fake_net.forecast = forecast([0, 0, 0, 0, 0, 0, 25.0, 0, 0, 0])  # 25 mm há 1 dia
    http.clear_cache()
    w = openmeteo.weather(-5.0, -49.0)
    assert w.rain_alert and w.rain_last_7d_mm == 25.0


def test_unexpected_payload_and_network_failure(monkeypatch):
    monkeypatch.setattr(http, "_request", lambda url, params: {"daily": {}})
    with pytest.raises(IntegrationError):
        openmeteo.weather(0, 0)

    def boom(url, params):
        raise IntegrationError("fora do ar")

    monkeypatch.setattr(http, "_request", boom)
    with pytest.raises(IntegrationError):
        ibge.estados()


def test_anm_catalog_only_official_links():
    cat = anm.catalog()
    assert cat["pagina"].startswith("https://www.gov.br/anm/")
    assert all(d["url"].startswith("https://dados.gov.br/dados/conjuntos-dados/") for d in cat["conjuntos"])
    assert len({d["id"] for d in cat["conjuntos"]}) == len(cat["conjuntos"])
