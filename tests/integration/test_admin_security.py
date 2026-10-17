"""Administração, segurança de acesso e robustez."""

import re

import pytest

from tests.conftest import prime_csrf


def _login(client, email, senha):
    prime_csrf(client)
    return client.post("/login", data={"email": email, "senha": senha}, follow_redirects=False)


def _admin(client):
    r = _login(client, "admin@teste.com", "admin-senha-123")
    assert r.status_code == 303
    return client


def _make_user(client, email="eng@ex.com", senha="senha-forte-123"):
    r = client.post("/api/v1/auth/registro", json={"nome": "Eng", "email": email, "senha": senha})
    assert r.status_code == 201
    client.cookies.clear()


def test_csrf_blocks_form_without_token(client):
    client.get("/login")  # cria o cookie, mas não enviamos o token
    r = client.post("/login", data={"email": "admin@teste.com", "senha": "admin-senha-123"})
    assert r.status_code == 403
    assert client.post("/registrar", data={"nome": "x", "email": "a@b.co", "senha": "12345678"}).status_code == 403


def test_admin_requires_admin_role(client):
    assert client.get("/admin", headers={"accept": "text/html"}, follow_redirects=False).status_code == 303  # sem login
    _make_user(client)
    _login(client, "eng@ex.com", "senha-forte-123")
    r = client.get("/admin", headers={"accept": "text/html"})
    assert r.status_code == 403 and "Acesso negado" in r.text
    assert "Administração" not in client.get("/usinas").text  # link só para admin


def test_admin_dashboard_and_pages(client):
    _admin(client)
    page = client.get("/admin").text
    assert "Administração" in page and "Usuários" in page
    for path in ("/admin/usuarios", "/admin/usinas", "/admin/auditoria", "/admin/identidade"):
        assert client.get(path).status_code == 200
    ident = client.get("/admin/identidade").text
    assert "logo.png" in ident and "provisório" in ident  # placeholders detectados


def test_admin_manages_users(client):
    _make_user(client, "maria@ex.com")
    _admin(client)
    users = client.get("/admin/usuarios?q=maria").text
    uid = int(re.search(r"/admin/usuarios/(\d+)/papel", users).group(1))
    # promover, desativar, redefinir senha
    assert client.post(f"/admin/usuarios/{uid}/papel", data={"papel": "visitante"}, follow_redirects=False).status_code == 303
    assert "visitante" in client.get("/admin/usuarios?q=maria").text
    client.post(f"/admin/usuarios/{uid}/ativo", data={"ativo": "0"})
    r = client.post(f"/admin/usuarios/{uid}/senha")
    temp = re.search(r"<code>([\w-]+)</code>", r.text).group(1)
    client.post(f"/admin/usuarios/{uid}/ativo", data={"ativo": "1"})
    client.cookies.clear()
    assert _login(client, "maria@ex.com", temp).status_code == 303  # entra com a senha temporária


def test_deactivated_user_cannot_login_and_session_dies(client):
    _make_user(client, "joao@ex.com")
    _admin(client)
    uid = int(re.search(r"/admin/usuarios/(\d+)/papel", client.get("/admin/usuarios?q=joao").text).group(1))
    client.post(f"/admin/usuarios/{uid}/ativo", data={"ativo": "0"})
    client.cookies.clear()
    r = _login(client, "joao@ex.com", "senha-forte-123")
    assert r.status_code == 401 and "desativada" in r.text
    assert client.post("/api/v1/auth/login", json={"email": "joao@ex.com", "senha": "senha-forte-123"}).status_code == 401


def test_cannot_remove_last_admin_or_self(client):
    _admin(client)
    users = client.get("/admin/usuarios").text
    uid = int(re.search(r"/admin/usuarios/(\d+)/senha", users).group(1))  # o próprio admin
    for path, data in ((f"/admin/usuarios/{uid}/excluir", {}), (f"/admin/usuarios/{uid}/ativo", {"ativo": "0"}), (f"/admin/usuarios/{uid}/papel", {"papel": "engenheiro"})):
        r = client.post(path, data=data, follow_redirects=True)
        assert "não pode" in r.text or "ao menos um administrador" in r.text


def test_lockout_after_failed_attempts(client):
    _make_user(client, "lock@ex.com")
    for _ in range(5):
        assert client.post("/api/v1/auth/login", json={"email": "lock@ex.com", "senha": "errada-errada"}).status_code == 401
    r = client.post("/api/v1/auth/login", json={"email": "lock@ex.com", "senha": "senha-forte-123"})  # senha certa, mas bloqueada
    assert r.status_code == 401 and "bloqueada" in r.json()["detail"]
    _admin(client)
    assert "login_falha" in client.get("/admin/auditoria").text
    assert "bloqueada" in client.get("/admin/usuarios?q=lock").text
    uid = int(re.search(r"/admin/usuarios/(\d+)/desbloquear", client.get("/admin/usuarios?q=lock").text).group(1))
    client.post(f"/admin/usuarios/{uid}/desbloquear")
    client.cookies.clear()
    assert client.post("/api/v1/auth/login", json={"email": "lock@ex.com", "senha": "senha-forte-123"}).status_code == 200


def test_registration_toggle(client):
    _admin(client)
    client.post("/admin/cadastro", data={"abrir": "0"})
    client.cookies.clear()
    r = client.post("/api/v1/auth/registro", json={"nome": "Novo", "email": "novo@ex.com", "senha": "senha-forte-123"})
    assert r.status_code == 403
    prime_csrf(client)
    r = client.post("/registrar", data={"nome": "Novo", "email": "novo@ex.com", "senha": "senha-forte-123"})
    assert r.status_code == 403 and "desabilitado" in r.text


def test_visitor_is_read_only(client):
    _make_user(client, "vis@ex.com")
    _admin(client)
    uid = int(re.search(r"/admin/usuarios/(\d+)/papel", client.get("/admin/usuarios?q=vis").text).group(1))
    client.post(f"/admin/usuarios/{uid}/papel", data={"papel": "visitante"})
    client.cookies.clear()
    h = {"Authorization": "Bearer " + client.post("/api/v1/auth/login", json={"email": "vis@ex.com", "senha": "senha-forte-123"}).json()["access_token"]}
    assert client.get("/api/v1/usinas", headers=h).status_code == 200
    assert client.post("/api/v1/usinas", json={"nome": "Não pode"}, headers=h).status_code == 403


def test_admin_deletes_user_and_cascades(client):
    _make_user(client, "del@ex.com")
    h = {"Authorization": "Bearer " + client.post("/api/v1/auth/login", json={"email": "del@ex.com", "senha": "senha-forte-123"}).json()["access_token"]}
    client.post("/api/v1/usinas", json={"nome": "Usina do Del"}, headers=h)
    _admin(client)
    assert "Usina do Del" in client.get("/admin/usinas").text
    uid = int(re.search(r"/admin/usuarios/(\d+)/excluir", client.get("/admin/usuarios?q=del@").text).group(1))
    client.post(f"/admin/usuarios/{uid}/excluir")
    assert "Usina do Del" not in client.get("/admin/usinas").text


def test_headers_health_and_errors(client):
    r = client.get("/api/v1/health/ready")
    assert r.status_code == 200 and r.json() == {"status": "ready"}
    r = client.get("/login")
    assert r.headers["x-content-type-options"] == "nosniff" and r.headers["x-frame-options"] == "DENY" and r.headers["x-request-id"]
    html = client.get("/nao-existe", headers={"accept": "text/html"})
    assert html.status_code == 404 and "Página não encontrada" in html.text
    assert client.get("/api/v1/nao-existe").json() == {"detail": "Not Found"}


def test_flowsheet_resave_keeps_measures(client):
    from app.db import SessionLocal
    from app.models import Medida
    from app.seed import create_cambui

    _admin(client)
    from app.models import Usuario

    with SessionLocal() as db:
        owner = db.query(Usuario).filter_by(email="admin@teste.com").one()
        usina = create_cambui(db, owner.id)
        before = db.query(Medida).count()
        from app.services import flowsheet_text, parse_flowsheet_text, save_flowsheet

        flows, ops = parse_flowsheet_text(*flowsheet_text(usina))
        flows[0] = "Alimentação (renomeada)"
        save_flowsheet(db, usina, flows, ops)
        assert db.query(Medida).count() == before  # medidas preservadas
        assert usina.fluxos[0].nome == "Alimentação (renomeada)"


def test_sync_missing_columns_upgrades_old_db():
    from sqlalchemy import create_engine, text

    from app.db import Base, sync_missing_columns

    old = create_engine("sqlite://")
    with old.begin() as c:
        c.execute(text("CREATE TABLE usuario (id INTEGER PRIMARY KEY, nome VARCHAR(120), email VARCHAR(254), senha_hash VARCHAR(255), papel VARCHAR(20), criado_em DATETIME)"))
        c.execute(text("INSERT INTO usuario (id, nome, email, senha_hash, papel) VALUES (1, 'A', 'a@a.co', 'x', 'engenheiro')"))
    added = sync_missing_columns(old)
    assert {"usuario.ativo", "usuario.falhas_login", "usuario.bloqueado_ate"} <= set(added)
    with old.connect() as c:
        assert c.execute(text("SELECT ativo, falhas_login FROM usuario")).one() == (1, 0)
    assert Base.metadata is not None


def test_production_requires_strong_secret(monkeypatch):
    from app.config import Settings

    with pytest.raises(ValueError):
        Settings(env="production", secret_key="curta")
    assert Settings(env="production", secret_key="x" * 40).env == "production"
    with pytest.raises(ValueError):
        Settings(admin_email="a@b.co", admin_password=None)  # senha ausente


def test_brand_slots_are_fixed_png_files():
    from app import brand

    names = {s.file for s in brand.SLOTS}
    assert {"logo.png", "logo-dark.png", "logo-mark.png", "favicon.png", "hero.png", "empty-state.png", "og-image.png", "mascot.png", "institution-logo.png"} == names
    for item in brand.status():
        assert item["existe"] and item["valido"]
        assert item["dimensoes"] == (item["slot"].width, item["slot"].height)
