"""Modelos de erro: conversão da incerteza informada em desvio-padrão."""

from __future__ import annotations

from enum import Enum

from app.core.errors import InvalidInputError


class ErrorModel(str, Enum):
    DESVIO_PADRAO = "desvio_padrao"  # o usuário informa o desvio-padrão
    INCERTEZA_PCT = "incerteza_pct"  # sigma = incerteza(%) * valor
    CERTEZA_PCT = "certeza_pct"  # sigma = (1 - certeza(%)) * valor


def sigma_from(value: float, model: ErrorModel, parameter: float) -> float:
    """Desvio-padrão a partir do modelo de erro escolhido (como no BALMAS original).

    - DESVIO_PADRAO: `parameter` já é o desvio (> 0).
    - INCERTEZA_PCT: `parameter` em % (> 0).
    - CERTEZA_PCT: `parameter` em % (0 < p < 100).
    """
    if model is ErrorModel.DESVIO_PADRAO:
        sigma = parameter
    elif model is ErrorModel.INCERTEZA_PCT:
        sigma = abs(value) * parameter / 100.0
    elif model is ErrorModel.CERTEZA_PCT:
        if not 0 < parameter < 100:
            raise InvalidInputError("Grau de certeza deve estar entre 0 e 100 (exclusivo).")
        sigma = abs(value) * (1.0 - parameter / 100.0)
    else:  # pragma: no cover
        raise InvalidInputError(f"Modelo de erro desconhecido: {model}")
    if not sigma > 0:
        raise InvalidInputError("Desvio-padrão deve ser maior que zero.")
    return float(sigma)
