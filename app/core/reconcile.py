"""Ajuste por mínimos quadrados ponderados com restrições (Lagrange / KKT).

Minimiza F = sum((x_aj - x)^2 / sigma^2) sujeito a M @ x_aj = 0.
Sistema (m+n)x(m+n):  [[2P, M^T], [M, 0]] @ [x_aj; lambda] = [2P x; 0].
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from app.core.errors import InvalidInputError, SingularSystemError
from app.core.solver import gauss_solve


@dataclass(frozen=True)
class ReconciliationResult:
    adjusted: np.ndarray  # valores ajustados (m)
    measured: np.ndarray  # valores de entrada (m)
    sigma: np.ndarray  # desvios de entrada (m)
    lagrange: np.ndarray  # multiplicadores (n) - só artifício matemático
    residual_before: np.ndarray  # M @ x antes do ajuste (n)
    chi2: float  # estatística do teste global
    dof: int  # graus de liberdade (= nº de restrições)
    normalized_residuals: np.ndarray  # z de cada medida (m)


def _check_inputs(m_mat: np.ndarray, x: np.ndarray, sigma: np.ndarray) -> None:
    n, m = m_mat.shape
    if x.shape != (m,) or sigma.shape != (m,):
        raise InvalidInputError("Número de medidas diferente do número de fluxos.")
    if not np.all(np.isfinite(x)) or not np.all(np.isfinite(sigma)):
        raise InvalidInputError("Valores não numéricos nas medidas.")
    if np.any(sigma <= 0):
        raise InvalidInputError("Desvio-padrão igual a zero (ou negativo) é inválido.")
    if np.linalg.matrix_rank(m_mat) < n:
        raise SingularSystemError("Sistema indeterminado ou inconsistente (restrições redundantes).")


def reconcile(
    m_mat: np.ndarray,
    x: np.ndarray,
    sigma: np.ndarray,
    *,
    method: str = "gauss",
) -> ReconciliationResult:
    """Fecha o balanço. `method`: 'gauss' (KKT com Gauss próprio) ou 'closed_form'."""
    m_mat = np.asarray(m_mat, dtype=float)
    x = np.asarray(x, dtype=float)
    sigma = np.asarray(sigma, dtype=float)
    _check_inputs(m_mat, x, sigma)
    n, m = m_mat.shape

    cov = np.diag(sigma**2)
    s_mt = cov @ m_mat.T  # Sigma M^T
    inner = m_mat @ s_mt  # M Sigma M^T
    residual = m_mat @ x

    if method == "closed_form":
        lam = np.linalg.solve(inner, residual)
        adjusted = x - s_mt @ lam
    elif method == "gauss":
        weights = np.diag(1.0 / sigma**2)
        a = np.block([[2 * weights, m_mat.T], [m_mat, np.zeros((n, n))]])
        y = np.concatenate([2 * weights @ x, np.zeros(n)])
        sol = gauss_solve(a, y)
        adjusted, lam = sol[:m], sol[m:]
    else:
        raise ValueError(f"Método desconhecido: {method}")

    chi2 = float(residual @ np.linalg.solve(inner, residual))
    var_adj_loss = np.einsum("ij,ji->i", s_mt, np.linalg.solve(inner, s_mt.T))  # diag(Sigma M^T inner^-1 M Sigma)
    with np.errstate(divide="ignore", invalid="ignore"):
        z = np.where(var_adj_loss > 1e-15, (x - adjusted) / np.sqrt(var_adj_loss), 0.0)

    return ReconciliationResult(adjusted, x, sigma, lam, residual, chi2, n, z)


def reconcile_component(
    m_mat: np.ndarray,
    adjusted_flows: np.ndarray,
    grade: np.ndarray,
    sigma_grade: np.ndarray,
    *,
    method: str = "gauss",
) -> ReconciliationResult:
    """Balanço metalúrgico (teor/componente) com as vazões já ajustadas fixas.

    Como a restrição é bilinear (vazão x teor), usa-se c_j = W_j * X_j como variável
    (sigma_c = W_j * sigma_X) e depois X_aj = c_aj / W_j. O resultado devolvido está
    em unidades de teor.
    """
    w = np.asarray(adjusted_flows, dtype=float)
    if np.any(w <= 0):
        raise InvalidInputError("Há vazão ajustada nula ou negativa; revise o balanço de massas.")
    grade = np.asarray(grade, dtype=float)
    sigma_grade = np.asarray(sigma_grade, dtype=float)
    res = reconcile(m_mat, w * grade, w * sigma_grade, method=method)
    return ReconciliationResult(
        adjusted=res.adjusted / w,
        measured=grade,
        sigma=sigma_grade,
        lagrange=res.lagrange,
        residual_before=res.residual_before,
        chi2=res.chi2,
        dof=res.dof,
        normalized_residuals=res.normalized_residuals,
    )
