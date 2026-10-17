"""Diagnósticos e alertas de plausibilidade do ajuste."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

import numpy as np

SUSPECT_ADJUSTMENT = 0.30  # ajuste relativo acima disso => medida suspeita
Z_LIMIT = 1.96  # |z| acima disso => candidato a erro grosseiro (95%)


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True)
class Alert:
    severity: Severity
    message: str
    flow: int | None = None  # índice base 1 do fluxo, quando aplicável


def chi2_critical(dof: int, z: float = 1.6449) -> float:
    """Quantil 95% do qui-quadrado (aproximação de Wilson-Hilferty)."""
    if dof <= 0:
        return 0.0
    t = 2.0 / (9.0 * dof)
    return dof * (1.0 - t + z * math.sqrt(t)) ** 3


def diagnose(
    measured: np.ndarray,
    adjusted: np.ndarray,
    normalized_residuals: np.ndarray,
    chi2: float,
    dof: int,
    *,
    is_grade: bool = False,
) -> list[Alert]:
    """Regras de negócio da seção 5.4 do documento de projeto."""
    alerts: list[Alert] = []
    limit = chi2_critical(dof)
    if chi2 > limit:
        alerts.append(
            Alert(
                Severity.WARNING,
                f"Teste global reprovado (χ²={chi2:.2f} > {limit:.2f}): "
                "os dados são incompatíveis com os desvios informados.",
            )
        )
    for j, (x, xa, z) in enumerate(zip(measured, adjusted, normalized_residuals, strict=True), start=1):
        if xa < 0:
            alerts.append(Alert(Severity.ERROR, f"Fluxo {j}: valor ajustado negativo ({xa:.3f}).", j))
        if is_grade and xa > 100:
            alerts.append(Alert(Severity.ERROR, f"Fluxo {j}: teor ajustado acima de 100%.", j))
        if x != 0 and abs(xa - x) / abs(x) > SUSPECT_ADJUSTMENT:
            alerts.append(
                Alert(Severity.WARNING, f"Fluxo {j}: ajuste de {abs(xa - x) / abs(x):.0%}; medida suspeita.", j)
            )
        elif abs(z) > Z_LIMIT:
            alerts.append(Alert(Severity.WARNING, f"Fluxo {j}: resíduo normalizado alto (|z|={abs(z):.2f}).", j))
    return alerts
