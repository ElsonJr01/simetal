"""Esquemas Pydantic da API REST."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class RegistroIn(BaseModel):
    nome: str = Field(min_length=2, max_length=120)
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    senha: str = Field(min_length=8, max_length=128)


class LoginIn(BaseModel):
    email: str
    senha: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UsinaIn(BaseModel):
    nome: str = Field(min_length=2, max_length=120)
    descricao: str = ""


class UsinaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nome: str
    descricao: str
    uf: str | None = None
    municipio_ibge: int | None = None
    municipio_nome: str | None = None
    latitude: float | None = None
    longitude: float | None = None


class LocalIn(BaseModel):
    uf: str = Field(pattern="^[A-Za-z]{2}$")
    municipio_ibge: int
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


class OperacaoIn(BaseModel):
    nome: str
    entradas: list[int]
    saidas: list[int]


class FluxogramaIn(BaseModel):
    fluxos: list[str] = Field(min_length=1)
    operacoes: list[OperacaoIn] = Field(min_length=1)


class AlertaOut(BaseModel):
    severidade: str
    mensagem: str
    fluxo: int | None = None


class FluxogramaOut(BaseModel):
    fluxos: list[str]
    operacoes: list[OperacaoIn]
    matriz_m: list[list[float]]
    alertas: list[AlertaOut]


class CampanhaIn(BaseModel):
    nome: str = Field(min_length=2, max_length=120)


class CampanhaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    usina_id: int
    nome: str


class MedidaIn(BaseModel):
    fluxo: int = Field(ge=1, description="Número do fluxo (base 1)")
    valor: float
    desvio: float | None = None
    nao_amostrado: bool = False


class AcaoIn(BaseModel):
    fluxo: int = Field(ge=1)
    acao: str = Field(pattern="^(manter|calculado|novo)$")
    valor: float | None = None
    desvio: float | None = None


class AjusteIn(BaseModel):
    componente: str = "massa"
    acoes: list[AcaoIn] | None = None  # presente => nova iteração (UC10)


class ResultadoOut(BaseModel):
    fluxo: int
    nome: str
    entrada: float
    desvio: float
    ajustado: float
    residuo_normalizado: float
    percentual: float | None
    acao: str


class AjusteOut(BaseModel):
    id: int
    componente: str
    iteracao: int
    chi2: float
    graus_liberdade: int
    convergiu: bool
    resultados: list[ResultadoOut]
    alertas: list[AlertaOut]


class ReconcileIn(BaseModel):
    """Cálculo avulso (sem banco): matriz M, medidas e desvios."""

    matriz_m: list[list[float]]
    valores: list[float]
    desvios: list[float]
