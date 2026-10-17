import os

os.environ["SIMETAL_DATABASE_URL"] = "sqlite://"
os.environ["SIMETAL_SECRET_KEY"] = "test-secret"
os.environ["SIMETAL_ADMIN_EMAIL"] = "admin@teste.com"
os.environ["SIMETAL_ADMIN_PASSWORD"] = "admin-senha-123"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture()
def client():
    Base.metadata.drop_all(engine)
    with TestClient(app) as c:  # o lifespan cria as tabelas e o administrador inicial
        yield c


def prime_csrf(client) -> str:
    """Obtém o cookie CSRF (GET numa página) e passa a enviar o cabeçalho X-CSRF-Token."""
    client.get("/login")
    token = client.cookies.get("simetal_csrf")
    client.headers["X-CSRF-Token"] = token
    return token


@pytest.fixture()
def web(client):
    """Cliente web com CSRF preparado."""
    prime_csrf(client)
    return client


@pytest.fixture(autouse=True)
def _clean_http_cache():
    from app.integrations import http

    http.clear_cache()
    yield
    http.clear_cache()
