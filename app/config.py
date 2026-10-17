"""Configuração por variáveis de ambiente (12-factor) e identidade visual."""

from __future__ import annotations

from functools import lru_cache

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class Brand(BaseModel):
    """IDENTIDADE VISUAL - todos os pontos de troca em um só lugar.

    Substitua os arquivos em app/static/brand/ (mantendo os nomes) ou altere os
    caminhos abaixo. Veja docs/IDENTIDADE_VISUAL.md para dimensões e formatos.
    """

    name: str = "SIMETAL"
    tagline: str = "Ajuste e fechamento de balanço de massas e metalúrgico"
    logo: str = "/static/brand/logo.svg"  # LOGO principal (fundo claro) - cabeçalho
    logo_dark: str = "/static/brand/logo-dark.svg"  # LOGO para fundo escuro
    logo_mark: str = "/static/brand/logo-mark.svg"  # símbolo/ícone isolado (quadrado)
    favicon: str = "/static/brand/favicon.svg"  # favicon
    hero_image: str = "/static/brand/hero.svg"  # IMAGEM de destaque da tela de login
    empty_state_image: str = "/static/brand/empty-state.svg"  # IMAGEM de "lista vazia"
    og_image: str = "/static/brand/og-image.svg"  # IMAGEM de compartilhamento (redes sociais)
    mascot: str = "/static/brand/mascot.svg"  # MASCOTE do bot de dicas (sugestão: 128x128, fundo transparente)
    mascot_name: str = "Pepita"  # nome do mascote (placeholder: troque pelo oficial)
    institution_logo: str = ""  # LOGO de instituição parceira (opcional, rodapé)
    institution_name: str = ""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="SIMETAL_", extra="ignore")

    env: str = "development"
    secret_key: str = "troque-esta-chave-em-producao"
    database_url: str = "sqlite:///./simetal.db"
    token_minutes: int = 60 * 8
    max_iterations: int = 12
    convergence_tol: float = 1e-3
    allow_registration: bool = True  # desligue em produção real
    vlibras_enabled: bool = True  # widget de tradução para Libras (VLibras, governo federal)
    mascot_enabled: bool = True  # bot de dicas
    integrations_enabled: bool = True  # IBGE e Open-Meteo
    http_timeout: float = 6.0  # segundos, chamadas a fontes públicas
    rain_alert_mm: float = 20.0  # chuva diária (mm) que gera aviso informativo
    auto_create_tables: bool = True  # cria tabelas na partida (teste); em produção use Alembic
    brand: Brand = Brand()

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
