import os

os.environ["SIMETAL_DATABASE_URL"] = "sqlite://"
os.environ["SIMETAL_SECRET_KEY"] = "test-secret"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture()
def client():
    Base.metadata.drop_all(engine)
    with TestClient(app) as c:  # o lifespan cria as tabelas
        yield c


@pytest.fixture(autouse=True)
def _clean_http_cache():
    from app.integrations import http

    http.clear_cache()
    yield
    http.clear_cache()
