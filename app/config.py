"""Configuração por variáveis de ambiente (12-factor) e identidade visual."""

from __future__ import annotations

from functools import lru_cache

from pydantic import BaseModel, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app import brand as _b

DEFAULT_SECRET = "troque-esta-chave-em-producao"


class Brand(BaseModel):
    """Textos da marca e CAMINHOS FIXOS dos arquivos (ver app/brand.py e docs/IDENTIDADE_VISUAL.md).

    Para trocar as imagens, substitua os PNGs em app/static/brand/ mantendo os nomes.
    """

    name: str = "SIMETAL"
    tagline: str = "Ajuste e fechamento de balanço de massas e metalúrgico"
    mascot_name: str = "Pepita"  # nome provisório do mascote
    institution_name: str = ""  # preencha para exibir institution-logo.png no rodapé
    repo_url: str = "https://github.com/ElsonJr01/SIMETAL"  # código-fonte (rodapé)
    contact_email: str = ""  # opcional: aparece no rodapé e em "Sobre" quando preenchido
    logo: str = _b.BY_KEY["logo"].url
    logo_dark: str = _b.BY_KEY["logo_dark"].url
    logo_mark: str = _b.BY_KEY["logo_mark"].url
    favicon: str = _b.BY_KEY["favicon"].url
    hero_image: str = _b.BY_KEY["hero"].url
    empty_state_image: str = _b.BY_KEY["empty_state"].url
    og_image: str = _b.BY_KEY["og_image"].url
    mascot: str = _b.BY_KEY["mascot"].url
    institution_logo: str = _b.BY_KEY["institution_logo"].url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="SIMETAL_", extra="ignore")

    env: str = "development"
    secret_key: str = DEFAULT_SECRET
    database_url: str = "sqlite:///./simetal.db"
    token_minutes: int = 60 * 8
    max_iterations: int = 12
    convergence_tol: float = 1e-3
    max_flows: int = 100
    max_operations: int = 100
    page_size: int = 20
    # segurança de acesso
    allow_registration: bool = True  # valor inicial; o admin pode alternar em /admin (fica no banco)
    lockout_attempts: int = 5
    lockout_minutes: int = 15
    admin_email: str | None = None  # cria/garante um administrador na partida
    admin_password: str | None = None  # usada só se o admin ainda não existir
    admin_name: str = "Administrador"
    # recursos opcionais
    vlibras_enabled: bool = True
    mascot_enabled: bool = True
    integrations_enabled: bool = True
    http_timeout: float = 6.0
    rain_alert_mm: float = 20.0
    auto_create_tables: bool = True  # cria tabelas e colunas novas na partida; em produção prefira Alembic
    log_level: str = "INFO"
    brand: Brand = Brand()

    @model_validator(mode="after")
    def _production_guards(self) -> Settings:
        if self.env == "production" and (self.secret_key == DEFAULT_SECRET or len(self.secret_key) < 32):
            raise ValueError("Em produção, defina SIMETAL_SECRET_KEY com pelo menos 32 caracteres aleatórios.")
        if bool(self.admin_email) != bool(self.admin_password):
            raise ValueError("Defina SIMETAL_ADMIN_EMAIL e SIMETAL_ADMIN_PASSWORD juntos (ou nenhum dos dois).")
        return self

    @property
    def sqlalchemy_url(self) -> str:
        url = self.database_url
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+psycopg://", 1)
        elif url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+psycopg://", 1)
        return url


@lru_cache
def get_settings() -> Settings:
    return Settings()
