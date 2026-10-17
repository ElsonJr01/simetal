"""Fluxograma da usina e matriz de restrições M.

Convenção da monografia (Damasceno & Nunes, 1992): M tem dimensão (n x m),
n = número de operações, m = número de fluxos; m_ij = +1 se o fluxo j entra na
operação i, -1 se sai e 0 se não se liga. O balanço fecha quando M @ W = 0.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

import numpy as np

from app.core.diagnostics import Alert, Severity
from app.core.errors import FlowsheetError


@dataclass(frozen=True)
class Operation:
    """Operação unitária. `inputs`/`outputs` são índices (base 0) de fluxos."""

    name: str
    inputs: tuple[int, ...]
    outputs: tuple[int, ...]


@dataclass(frozen=True)
class Flowsheet:
    flows: tuple[str, ...]
    operations: tuple[Operation, ...]

    @property
    def n_flows(self) -> int:
        return len(self.flows)

    @property
    def n_operations(self) -> int:
        return len(self.operations)

    def matrix(self) -> np.ndarray:
        """Matriz M (n x m) de entradas (+1) e saídas (-1)."""
        m = np.zeros((self.n_operations, self.n_flows))
        for i, op in enumerate(self.operations):
            for j in op.inputs:
                m[i, j] += 1.0
            for j in op.outputs:
                m[i, j] -= 1.0
        return m

    def validate(self) -> list[Alert]:
        """Valida o fluxograma. Usa busca em largura (BFS) para conectividade."""
        alerts: list[Alert] = []
        if not self.flows or not self.operations:
            return [Alert(Severity.ERROR, "Defina ao menos um fluxo e uma operação.")]

        for op in self.operations:
            for j in (*op.inputs, *op.outputs):
                if not 0 <= j < self.n_flows:
                    raise FlowsheetError(f"Operação '{op.name}' usa fluxo inexistente ({j + 1}).")
            if not op.inputs or not op.outputs:
                alerts.append(
                    Alert(Severity.ERROR, f"Operação '{op.name}' precisa de entrada e de saída.")
                )

        as_input = [0] * self.n_flows
        as_output = [0] * self.n_flows
        for op in self.operations:
            for j in op.inputs:
                as_input[j] += 1
            for j in op.outputs:
                as_output[j] += 1
        for j, name in enumerate(self.flows):
            if as_input[j] == 0 and as_output[j] == 0:
                alerts.append(Alert(Severity.ERROR, f"Fluxo {j + 1} ({name}) não se liga a nenhuma operação."))
            if as_input[j] > 1:
                alerts.append(Alert(Severity.ERROR, f"Fluxo {j + 1} ({name}) entra em mais de uma operação."))
            if as_output[j] > 1:
                alerts.append(Alert(Severity.ERROR, f"Fluxo {j + 1} ({name}) sai de mais de uma operação."))

        if self._n_components() > 1:
            alerts.append(
                Alert(Severity.WARNING, "O fluxograma tem partes desconectadas; cada parte fecha separadamente.")
            )
        if not any(a.severity is Severity.ERROR for a in alerts):
            rank = int(np.linalg.matrix_rank(self.matrix()))
            if rank < self.n_operations:
                alerts.append(
                    Alert(Severity.ERROR, "Há restrições redundantes entre as operações (matriz sem posto completo).")
                )
        return alerts

    def _n_components(self) -> int:
        """Conta componentes conexos (operações ligadas por fluxos em comum) via BFS."""
        owners: dict[int, list[int]] = {}
        for i, op in enumerate(self.operations):
            for j in (*op.inputs, *op.outputs):
                owners.setdefault(j, []).append(i)
        seen: set[int] = set()
        count = 0
        for start in range(self.n_operations):
            if start in seen:
                continue
            count += 1
            queue = deque([start])
            seen.add(start)
            while queue:
                i = queue.popleft()
                op = self.operations[i]
                for j in (*op.inputs, *op.outputs):
                    for k in owners[j]:
                        if k not in seen:
                            seen.add(k)
                            queue.append(k)
        return count
