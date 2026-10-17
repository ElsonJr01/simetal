"""Estatística de amostras repetidas (média e desvio-padrão amostral)."""

from __future__ import annotations

import math
from collections.abc import Sequence

from app.core.errors import InvalidInputError


def mean_std(samples: Sequence[float]) -> tuple[float, float]:
    """Média e desvio-padrão amostral (n-1). Exige ao menos 2 amostras e desvio > 0."""
    n = len(samples)
    if n < 2:
        raise InvalidInputError("Número de amostras insuficiente para os cálculos estatísticos.")
    mean = math.fsum(samples) / n
    var = math.fsum((s - mean) ** 2 for s in samples) / (n - 1)
    std = math.sqrt(var)
    if std == 0:
        raise InvalidInputError("Desvio-padrão igual a zero: amostras idênticas.")
    return mean, std
