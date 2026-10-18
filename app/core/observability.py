"""Redundância e observabilidade do balanço (quais fluxos não medidos dá para calcular).

Seja M (n x m) a matriz do fluxograma e U o conjunto de fluxos NÃO medidos.
- Um fluxo não medido é calculável (determinável) se não depende de graus de liberdade livres:
  a sua componente no espaço nulo de M[:, U] é zero.
- Grau de redundância = posto(M) − posto(M[:, U]): quantas equações "sobram" para ajustar
  (e testar) as medidas. Com redundância 0 o balanço só calcula; não corrige nem testa nada.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

_TOL = 1e-9


@dataclass(frozen=True)
class Observability:
    redundancy: int  # equações que sobram para ajustar as medidas
    determinable: list[int]  # índices (base 0) de não medidos calculáveis
    indeterminate: list[int]  # índices (base 0) de não medidos NÃO calculáveis
    measured: list[int]
    unmeasured: list[int]

    @property
    def all_observable(self) -> bool:
        return not self.indeterminate


def analyze(m_mat: np.ndarray, measured: Sequence[bool]) -> Observability:
    m_mat = np.asarray(m_mat, dtype=float)
    n_flows = m_mat.shape[1]
    flags = np.asarray(list(measured), dtype=bool)
    if flags.shape != (n_flows,):
        raise ValueError("Uma indicação medido/não medido por fluxo é necessária.")
    unmeasured = [int(j) for j in np.where(~flags)[0]]
    measured_idx = [int(j) for j in np.where(flags)[0]]
    rank_m = int(np.linalg.matrix_rank(m_mat))
    if not unmeasured:
        return Observability(rank_m, [], [], measured_idx, [])

    m_u = m_mat[:, unmeasured]
    rank_u = int(np.linalg.matrix_rank(m_u))
    _, _, vt = np.linalg.svd(m_u)
    null = vt[rank_u:].T  # (|U| x graus de liberdade livres)
    determinable, indeterminate = [], []
    for pos, j in enumerate(unmeasured):
        free = null.shape[1] > 0 and float(np.linalg.norm(null[pos])) > _TOL
        (indeterminate if free else determinable).append(j)
    return Observability(max(rank_m - rank_u, 0), determinable, indeterminate, measured_idx, unmeasured)
