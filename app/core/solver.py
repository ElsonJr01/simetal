"""Eliminação de Gauss com pivoteamento parcial (seção IV da monografia)."""

from __future__ import annotations

import numpy as np

from app.core.errors import SingularSystemError

_TOL = 1e-12


def gauss_solve(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Resolve A x = b por eliminação de Gauss com pivoteamento parcial.

    Triangulariza A (estágios k = 1..n-1) e resolve por substituição retroativa.
    Levanta SingularSystemError se algum pivô for (praticamente) nulo.
    """
    a = np.array(a, dtype=float, copy=True)
    b = np.array(b, dtype=float, copy=True)
    n = a.shape[0]
    if a.shape != (n, n) or b.shape != (n,):
        raise ValueError("Dimensões incompatíveis para o sistema A x = b.")
    scale = max(float(np.max(np.abs(a))), 1.0)

    for k in range(n):
        pivot_row = k + int(np.argmax(np.abs(a[k:, k])))
        if abs(a[pivot_row, k]) <= _TOL * scale:
            raise SingularSystemError("Sistema indeterminado ou inconsistente.")
        if pivot_row != k:
            a[[k, pivot_row]] = a[[pivot_row, k]]
            b[[k, pivot_row]] = b[[pivot_row, k]]
        for i in range(k + 1, n):
            mult = a[i, k] / a[k, k]
            a[i, k:] -= mult * a[k, k:]
            b[i] -= mult * b[k]

    x = np.zeros(n)
    for i in range(n - 1, -1, -1):
        x[i] = (b[i] - a[i, i + 1 :] @ x[i + 1 :]) / a[i, i]
    return x
