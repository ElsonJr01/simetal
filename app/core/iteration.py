"""Iteração assistida: o engenheiro decide, fluxo a fluxo, o que fazer (seção VI.1)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import numpy as np

from app.core.errors import InvalidInputError


class IterationAction(str, Enum):
    KEEP = "manter"  # mantém o valor e o desvio da iteração anterior
    CALCULATED = "calculado"  # adota o valor ajustado (mantém o desvio)
    NEW = "novo"  # valor (e desvio) informados pelo usuário


@dataclass(frozen=True)
class FlowAction:
    action: IterationAction = IterationAction.KEEP
    value: float | None = None
    sigma: float | None = None


def apply_actions(
    prev_inputs: np.ndarray,
    prev_sigma: np.ndarray,
    prev_adjusted: np.ndarray,
    actions: list[FlowAction],
) -> tuple[np.ndarray, np.ndarray]:
    """Gera entradas da próxima iteração. Para NEW sem desvio, usa sigma = valor
    (critério de mínima confiabilidade da monografia)."""
    if not len(actions) == len(prev_inputs):
        raise InvalidInputError("Uma ação por fluxo é necessária.")
    values = np.array(prev_inputs, dtype=float, copy=True)
    sigmas = np.array(prev_sigma, dtype=float, copy=True)
    for j, act in enumerate(actions):
        if act.action is IterationAction.CALCULATED:
            values[j] = prev_adjusted[j]
        elif act.action is IterationAction.NEW:
            if act.value is None:
                raise InvalidInputError(f"Fluxo {j + 1}: informe o novo valor.")
            values[j] = act.value
            sigmas[j] = act.sigma if act.sigma else abs(act.value)
            if sigmas[j] <= 0:
                raise InvalidInputError(f"Fluxo {j + 1}: desvio-padrão deve ser maior que zero.")
    return values, sigmas


def has_converged(prev_adjusted: np.ndarray, adjusted: np.ndarray, tol: float = 1e-3) -> bool:
    """Convergência: variação relativa máxima entre iterações abaixo da tolerância."""
    denom = np.maximum(np.abs(prev_adjusted), 1e-12)
    return bool(np.max(np.abs(adjusted - prev_adjusted) / denom) < tol)
