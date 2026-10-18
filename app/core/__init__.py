"""Núcleo de cálculo do SIMETAL.

Este pacote NÃO conhece web nem banco de dados: só NumPy e Python puro.
Pode ser reaproveitado em CLI, notebooks ou qualquer outra interface.
"""

from app.core.diagnostics import Alert, Severity, diagnose
from app.core.errors import FlowsheetError, InvalidInputError, SingularSystemError
from app.core.flowsheet import Flowsheet, Operation
from app.core.indicators import Indicators, distribution, indicators
from app.core.iteration import IterationAction, apply_actions, has_converged
from app.core.observability import Observability, analyze
from app.core.reconcile import ReconciliationResult, reconcile, reconcile_component
from app.core.statistics import mean_std
from app.core.weights import ErrorModel, sigma_from

__all__ = [
    "Alert",
    "ErrorModel",
    "Flowsheet",
    "FlowsheetError",
    "InvalidInputError",
    "Indicators",
    "IterationAction",
    "Observability",
    "Operation",
    "ReconciliationResult",
    "Severity",
    "SingularSystemError",
    "analyze",
    "apply_actions",
    "distribution",
    "diagnose",
    "has_converged",
    "indicators",
    "mean_std",
    "reconcile",
    "reconcile_component",
    "sigma_from",
]
