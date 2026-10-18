"""Modelos de banco (SQLAlchemy 2.0). Ver diagrama ER em docs/."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, false, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _now() -> datetime:
    return datetime.now(UTC)


class Usuario(Base):
    __tablename__ = "usuario"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    senha_hash: Mapped[str] = mapped_column(String(255))
    papel: Mapped[str] = mapped_column(String(20), default="engenheiro")  # admin | engenheiro | visitante
    ativo: Mapped[bool] = mapped_column(default=True, server_default=true())
    falhas_login: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    bloqueado_ate: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ultimo_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    usinas: Mapped[list[Usina]] = relationship(back_populates="dono", cascade="all, delete-orphan")


class Usina(Base):
    __tablename__ = "usina"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(120), index=True)
    descricao: Mapped[str] = mapped_column(Text, default="")
    uf: Mapped[str | None] = mapped_column(String(2), nullable=True)  # IBGE
    municipio_ibge: Mapped[int | None] = mapped_column(Integer, nullable=True)  # código IBGE
    municipio_nome: Mapped[str | None] = mapped_column(String(120), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    dono_id: Mapped[int] = mapped_column(ForeignKey("usuario.id", ondelete="CASCADE"), index=True)
    criada_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    dono: Mapped[Usuario] = relationship(back_populates="usinas")
    fluxos: Mapped[list[Fluxo]] = relationship(
        back_populates="usina", cascade="all, delete-orphan", order_by="Fluxo.numero"
    )
    operacoes: Mapped[list[Operacao]] = relationship(
        back_populates="usina", cascade="all, delete-orphan", order_by="Operacao.id"
    )
    campanhas: Mapped[list[Campanha]] = relationship(
        back_populates="usina", cascade="all, delete-orphan", order_by="Campanha.id.desc()"
    )


class Fluxo(Base):
    __tablename__ = "fluxo"
    __table_args__ = (UniqueConstraint("usina_id", "numero"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    usina_id: Mapped[int] = mapped_column(ForeignKey("usina.id", ondelete="CASCADE"), index=True)
    numero: Mapped[int] = mapped_column(Integer)  # base 1
    nome: Mapped[str] = mapped_column(String(120))

    usina: Mapped[Usina] = relationship(back_populates="fluxos")


class Operacao(Base):
    __tablename__ = "operacao"

    id: Mapped[int] = mapped_column(primary_key=True)
    usina_id: Mapped[int] = mapped_column(ForeignKey("usina.id", ondelete="CASCADE"), index=True)
    nome: Mapped[str] = mapped_column(String(120))
    tipo: Mapped[str] = mapped_column(String(40), default="outro")

    usina: Mapped[Usina] = relationship(back_populates="operacoes")
    conexoes: Mapped[list[Conexao]] = relationship(back_populates="operacao", cascade="all, delete-orphan")


class Conexao(Base):
    __tablename__ = "conexao"
    __table_args__ = (
        UniqueConstraint("operacao_id", "fluxo_id"),
        CheckConstraint("sinal IN (1, -1)", name="ck_conexao_sinal"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    operacao_id: Mapped[int] = mapped_column(ForeignKey("operacao.id", ondelete="CASCADE"), index=True)
    fluxo_id: Mapped[int] = mapped_column(ForeignKey("fluxo.id", ondelete="CASCADE"), index=True)
    sinal: Mapped[int] = mapped_column(Integer)  # +1 entra, -1 sai

    operacao: Mapped[Operacao] = relationship(back_populates="conexoes")


class Campanha(Base):
    __tablename__ = "campanha"

    id: Mapped[int] = mapped_column(primary_key=True)
    usina_id: Mapped[int] = mapped_column(ForeignKey("usina.id", ondelete="CASCADE"), index=True)
    nome: Mapped[str] = mapped_column(String(120))
    unidade_vazao: Mapped[str] = mapped_column(String(20), default="t/h", server_default="t/h")
    unidade_teor: Mapped[str] = mapped_column(String(20), default="%", server_default="%")
    criada_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    usina: Mapped[Usina] = relationship(back_populates="campanhas")
    medidas: Mapped[list[Medida]] = relationship(back_populates="campanha", cascade="all, delete-orphan")
    ajustes: Mapped[list[Ajuste]] = relationship(
        back_populates="campanha", cascade="all, delete-orphan", order_by="Ajuste.id"
    )


class Medida(Base):
    __tablename__ = "medida"
    __table_args__ = (UniqueConstraint("campanha_id", "fluxo_id", "componente"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    campanha_id: Mapped[int] = mapped_column(ForeignKey("campanha.id", ondelete="CASCADE"), index=True)
    fluxo_id: Mapped[int] = mapped_column(ForeignKey("fluxo.id", ondelete="CASCADE"))
    componente: Mapped[str] = mapped_column(String(60), default="massa")  # massa, cinzas, Fe...
    valor: Mapped[float] = mapped_column(Float)
    desvio: Mapped[float] = mapped_column(Float)
    nao_amostrado: Mapped[bool] = mapped_column(default=False)

    campanha: Mapped[Campanha] = relationship(back_populates="medidas")


class Ajuste(Base):
    """Uma iteração de ajuste. Imutável depois de criada (histórico/auditoria)."""

    __tablename__ = "ajuste"

    id: Mapped[int] = mapped_column(primary_key=True)
    campanha_id: Mapped[int] = mapped_column(ForeignKey("campanha.id", ondelete="CASCADE"), index=True)
    componente: Mapped[str] = mapped_column(String(60), default="massa")
    iteracao: Mapped[int] = mapped_column(Integer, default=1)
    chi2: Mapped[float] = mapped_column(Float, default=0.0)
    graus: Mapped[int] = mapped_column(Integer, default=0)
    convergiu: Mapped[bool] = mapped_column(default=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    campanha: Mapped[Campanha] = relationship(back_populates="ajustes")
    resultados: Mapped[list[ResultadoFluxo]] = relationship(
        back_populates="ajuste", cascade="all, delete-orphan", order_by="ResultadoFluxo.fluxo_numero"
    )


class ResultadoFluxo(Base):
    __tablename__ = "resultado_fluxo"

    id: Mapped[int] = mapped_column(primary_key=True)
    ajuste_id: Mapped[int] = mapped_column(ForeignKey("ajuste.id", ondelete="CASCADE"), index=True)
    fluxo_numero: Mapped[int] = mapped_column(Integer)
    fluxo_nome: Mapped[str] = mapped_column(String(120))
    entrada: Mapped[float] = mapped_column(Float)
    desvio: Mapped[float] = mapped_column(Float)
    ajustado: Mapped[float] = mapped_column(Float)
    residuo_norm: Mapped[float] = mapped_column(Float, default=0.0)
    percentual: Mapped[float | None] = mapped_column(Float, nullable=True)  # % da alimentação
    acao: Mapped[str] = mapped_column(String(20), default="manter")

    ajuste: Mapped[Ajuste] = relationship(back_populates="resultados")


class Auditoria(Base):
    """Trilha de auditoria: ações administrativas e eventos de segurança."""

    __tablename__ = "auditoria"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.id", ondelete="SET NULL"), nullable=True)
    usuario_email: Mapped[str] = mapped_column(String(254), default="")  # cópia: sobrevive à exclusão do usuário
    acao: Mapped[str] = mapped_column(String(60), index=True)
    alvo: Mapped[str] = mapped_column(String(160), default="")
    detalhe: Mapped[str] = mapped_column(Text, default="")
    ip: Mapped[str] = mapped_column(String(45), default="")
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)


class Configuracao(Base):
    """Chaves de configuração alteráveis em tempo de execução pelo administrador."""

    __tablename__ = "configuracao"

    chave: Mapped[str] = mapped_column(String(60), primary_key=True)
    valor: Mapped[str] = mapped_column(String(255), default="")
