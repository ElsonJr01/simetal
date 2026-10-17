"""Testes de integração: API REST e páginas web (SQLite em memória)."""

import re


def _register(client, email="eng@exemplo.com"):
    r = client.post("/api/v1/auth/registro", json={"nome": "Eng Teste", "email": email, "senha": "senha-forte-123"})
    assert r.status_code == 201
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_health_and_auth_required(client):
    assert client.get("/api/v1/health").json() == {"status": "ok"}
    assert client.get("/api/v1/usinas").status_code == 401
    assert client.post("/api/v1/auth/login", json={"email": "x@y.com", "senha": "errada123"}).status_code == 401


def test_full_flow_via_api(client):
    h = _register(client)
    usina = client.post("/api/v1/usinas", json={"nome": "Minha usina"}, headers=h).json()
    fx = {
        "fluxos": ["alim", "over", "under", "rej", "mid", "conc"],
        "operacoes": [
            {"nome": "Ciclone", "entradas": [1], "saidas": [2, 3]},
            {"nome": "Espiral", "entradas": [3], "saidas": [4, 5, 6]},
        ],
    }
    r = client.put(f"/api/v1/usinas/{usina['id']}/fluxograma", json=fx, headers=h)
    assert r.status_code == 200 and r.json()["matriz_m"][0] == [1, -1, -1, 0, 0, 0]
    camp = client.post(f"/api/v1/usinas/{usina['id']}/campanhas", json={"nome": "C1"}, headers=h).json()

    medidas = [
        {"fluxo": i + 1, "valor": v, "desvio": s}
        for i, (v, s) in enumerate(zip([3682.36, 554.1, 6027.8, 239.85, 405.13, 1473.25], [3682.36, 554.1, 858.423, 63.701, 35.613, 525.66], strict=True))
    ]
    assert client.put(f"/api/v1/campanhas/{camp['id']}/medidas/massa", json=medidas, headers=h).status_code == 204
    r = client.post(f"/api/v1/campanhas/{camp['id']}/ajustes", json={"componente": "massa"}, headers=h)
    assert r.status_code == 201
    ajuste = r.json()
    assert [round(x["ajustado"], 2) for x in ajuste["resultados"]] == [3750.82, 552.55, 3198.27, 255.41, 409.99, 2532.87]
    assert any("suspeita" in a["mensagem"] for a in ajuste["alertas"])  # fluxo 3 é ajustado em ~47%

    # iteração 2: novo valor para o fluxo 1, usar calculado nos demais
    acoes = [{"fluxo": 1, "acao": "novo", "valor": 6000}] + [{"fluxo": n, "acao": "calculado"} for n in range(2, 7)]
    r2 = client.post(f"/api/v1/campanhas/{camp['id']}/ajustes", json={"componente": "massa", "acoes": acoes}, headers=h)
    assert r2.status_code == 201 and r2.json()["iteracao"] == 2
    assert client.get(f"/api/v1/ajustes/{r2.json()['id']}", headers=h).status_code == 200

    # metalúrgico exige massa fechada
    cin = [{"fluxo": i + 1, "valor": v, "desvio": s} for i, (v, s) in enumerate(zip([23.04, 49.95, 32.59, 80.37, 35.35, 24.78], [23.04, 2.747, 6.06, 3.201, 4.683, 4.898], strict=True))]
    client.put(f"/api/v1/campanhas/{camp['id']}/medidas/cinzas", json=cin, headers=h)
    r3 = client.post(f"/api/v1/campanhas/{camp['id']}/ajustes", json={"componente": "cinzas"}, headers=h)
    assert r3.status_code == 201


def test_isolation_between_users(client):
    h1 = _register(client, "a@a.com")
    h2 = _register(client, "b@b.com")
    usina = client.post("/api/v1/usinas", json={"nome": "Da Ana"}, headers=h1).json()
    assert client.get(f"/api/v1/usinas/{usina['id']}", headers=h2).status_code == 404
    assert client.get("/api/v1/usinas", headers=h2).json() == []


def test_validation_errors(client):
    h = _register(client)
    usina = client.post("/api/v1/usinas", json={"nome": "U"*3}, headers=h).json()
    bad = {"fluxos": ["a", "b", "c"], "operacoes": [{"nome": "x", "entradas": [1], "saidas": [2]}]}
    assert client.put(f"/api/v1/usinas/{usina['id']}/fluxograma", json=bad, headers=h).status_code == 422
    assert client.post("/api/v1/estatistica/resumo", json=[1.0]).status_code == 422
    assert client.post("/api/v1/estatistica/resumo", json=[10.0, 12, 14]).json()["media"] == 12
    r = client.post("/api/v1/reconcile", json={"matriz_m": [[1, -1, -1]], "valores": [10, 6, 5], "desvios": [1, 1, 1]})
    assert r.status_code == 200 and abs(sum(a * b for a, b in zip([1, -1, -1], r.json()["ajustados"], strict=True))) < 1e-9


def test_web_pages_and_demo_flow(client):
    assert client.get("/usinas", headers={"accept": "text/html"}, follow_redirects=False).status_code == 303
    r = client.post("/registrar", data={"nome": "Eng Web", "email": "web@ex.com", "senha": "senha-forte-123"}, follow_redirects=False)
    assert r.status_code == 303
    assert "SIMETAL" in client.get("/usinas").text
    r = client.post("/usinas/exemplo", follow_redirects=False)
    usina_url = r.headers["location"]
    page = client.get(usina_url).text
    assert "Ciclone" in page and "Matriz M" in page
    camp_id = re.search(r"/campanhas/(\d+)", page).group(1)
    r = client.post(f"/campanhas/{camp_id}/ajustar", data={"componente": "massa"}, headers={"HX-Request": "true"})
    assert "3750.82" in r.text and "Iteração 1" in r.text
    form = {"componente": "massa", **{f"acao_{n}": "calculado" for n in range(1, 7)}}
    r = client.post(f"/campanhas/{camp_id}/iterar", data=form)
    assert "Iteração 2" in r.text
    r = client.post(f"/campanhas/{camp_id}/ajustar", data={"componente": "cinzas"})
    assert "33.77" in r.text
    assert client.get("/static/css/brand.css").status_code == 200
    assert client.get("/static/brand/logo.svg").status_code == 200


def test_open_tips_api_and_widgets(client):
    r = client.get("/api/v1/dicas?contexto=medidas,resultado")  # sem login
    assert r.status_code == 200
    tips = r.json()
    assert tips and {t["contexto"] for t in tips} <= {"medidas", "resultado"}
    assert all({"id", "titulo", "texto", "nivel"} <= t.keys() for t in tips)
    assert all(t["nivel"] == "basico" for t in client.get("/api/v1/dicas?nivel=basico").json())
    page = client.get("/login").text
    assert "vlibras-plugin.js" in page and 'id="mascote"' in page
    assert 'data-tip-context="geral"' in page


def test_tip_ids_are_unique():
    from app.content.tips import TIPS

    ids = [t["id"] for t in TIPS]
    assert len(ids) == len(set(ids))


def test_location_and_weather_flow(client, monkeypatch):
    from app.integrations import http

    def fake(url, params):
        if url.endswith("/estados"):
            return [{"id": 15, "sigla": "PA", "nome": "Pará"}]
        if url.endswith("/estados/PA/municipios"):
            return [{"id": 1504208, "nome": "Marabá"}]
        if "geocoding" in url:
            return {"results": [{"latitude": -5.37, "longitude": -49.12, "admin1": "Pará", "country_code": "BR"}]}
        days = [f"2026-10-{d:02d}" for d in range(4, 14)]
        return {"current": {"temperature_2m": 30.0, "precipitation": 0.0},
                "daily": {"time": days, "temperature_2m_max": [33.0] * 10, "temperature_2m_min": [24.0] * 10,
                          "precipitation_sum": [0, 0, 0, 0, 0, 0, 30.0, 0, 0, 0]}}

    monkeypatch.setattr(http, "_request", fake)
    h = _register(client)
    usina = client.post("/api/v1/usinas", json={"nome": "Usina Local"}, headers=h).json()
    assert client.get(f"/api/v1/usinas/{usina['id']}/clima", headers=h).status_code == 422  # sem local ainda
    assert client.get("/api/v1/ibge/estados", headers=h).json()[0]["sigla"] == "PA"
    r = client.put(f"/api/v1/usinas/{usina['id']}/local", json={"uf": "pa", "municipio_ibge": 1504208}, headers=h)
    assert r.status_code == 200 and r.json()["municipio_nome"] == "Marabá" and r.json()["latitude"] == -5.37
    assert client.put(f"/api/v1/usinas/{usina['id']}/local", json={"uf": "PA", "municipio_ibge": 1}, headers=h).status_code == 422
    clima = client.get(f"/api/v1/usinas/{usina['id']}/clima", headers=h).json()
    assert clima["alerta_chuva"] is True and clima["chuva_ultimos_7_dias_mm"] == 30.0 and "Open-Meteo" in clima["atribuicao"]
    fontes = client.get("/api/v1/fontes").json()  # sem login
    assert "ibge" in fontes and fontes["anm"]["conjuntos"]


def test_weather_failure_does_not_break_pages(client, monkeypatch):
    from app.integrations import http
    from app.integrations.http import IntegrationError

    def down(url, params):
        raise IntegrationError("fora do ar")

    monkeypatch.setattr(http, "_request", down)
    client.post("/registrar", data={"nome": "Eng Web", "email": "w2@ex.com", "senha": "senha-forte-123"})
    r = client.post("/usinas/exemplo", follow_redirects=False)
    page = client.get(r.headers["location"])
    assert page.status_code == 200 and "Dados abertos da mineração" in page.text and "Localização e clima" in page.text
    uid = r.headers["location"].rsplit("/", 1)[1]
    assert "Defina o local" in client.get(f"/usinas/{uid}/clima").text
    bad = client.post(f"/usinas/{uid}/local", data={"uf": "PA", "municipio_ibge": "1504208"})
    assert bad.status_code == 422 and "Tente novamente" in bad.text  # IBGE fora do ar: erro amigável, sem 500
