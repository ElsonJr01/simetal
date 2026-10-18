"""Indicadores metalúrgicos clássicos, calculados sobre valores JÁ AJUSTADOS.

Notação: F, f = vazão e teor da alimentação; C, c = vazão e teor do produto (concentrado).
  Recuperação metalúrgica (%)  R = (C·c) / (F·f) · 100
  Razão de enriquecimento      E = c / f
  Razão de concentração        K = F / C
  Rendimento mássico (%)       Y = C / F · 100
  Distribuição do fluxo j (%)  D_j = (W_j·X_j) / (F·f) · 100
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.errors import InvalidInputError


@dataclass(frozen=True)
class Indicators:
    recovery_pct: float
    enrichment_ratio: float
    concentration_ratio: float
    yield_pct: float


def indicators(feed_flow: float, feed_grade: float, prod_flow: float, prod_grade: float) -> Indicators:
    if feed_flow <= 0 or prod_flow <= 0:
        raise InvalidInputError("As vazões ajustadas da alimentação e do produto precisam ser positivas.")
    if feed_grade <= 0:
        raise InvalidInputError("O teor da alimentação precisa ser positivo para calcular a recuperação.")
    return Indicators(
        recovery_pct=100.0 * prod_flow * prod_grade / (feed_flow * feed_grade),
        enrichment_ratio=prod_grade / feed_grade,
        concentration_ratio=feed_flow / prod_flow,
        yield_pct=100.0 * prod_flow / feed_flow,
    )


def distribution(flows: list[float], grades: list[float], feed_index: int = 0) -> list[float | None]:
    """Distribuição (%) do componente em cada fluxo, relativa à alimentação (`feed_index`)."""
    base = flows[feed_index] * grades[feed_index]
    if base == 0:
        return [None] * len(flows)
    return [100.0 * w * g / base for w, g in zip(flows, grades, strict=True)]
