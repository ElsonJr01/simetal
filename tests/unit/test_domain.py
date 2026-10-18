"""Conteúdo e regras de domínio: observabilidade, indicadores, importação, exportação, glossário."""

import numpy as np
import pytest

from app.content.faq import FAQ
from app.content.glossary import CATEGORIES, TERMS, by_category, slug
from app.core import (
    Flowsheet, InvalidInputError, Operation, analyze, distribution, indicators, reconcile, reconcile_component,
)
from app.routers.web import fmt_num
from app.services import ServiceError, parse_decimal, parse_pasted

SHEET = Flowsheet(
    ("alim", "over", "under", "rej", "mid", "conc"),
    (Operation("ciclone", (0,), (1, 2)), Operation("espiral", (2,), (3, 4, 5))),
)
M = SHEET.matrix()


def test_observability_all_measured_has_full_redundancy():
    obs = analyze(M, [True] * 6)
    assert obs.redundancy == 2 and obs.all_observable and obs.unmeasured == []


def test_observability_single_unmeasured_flow_is_computable():
    obs = analyze(M, [True, True, False, True, True, True])
    assert obs.determinable == [2] and obs.indeterminate == [] and obs.redundancy == 1


def test_observability_two_flows_in_same_balance_are_indeterminate():
    obs = analyze(M, [False, False, True, True, True, True])  # fluxos 1 e 2: uma equação, duas incógnitas
    assert obs.indeterminate == [0, 1] and not obs.all_observable


def test_observability_no_redundancy_when_everything_is_computed():
    obs = analyze(M, [True, False, False, False, False, False])
    assert obs.redundancy == 0


def test_observability_rejects_wrong_length():
    with pytest.raises(ValueError):
        analyze(M, [True])


def test_distribution_and_indicators_match_monograph_table_2():
    x = np.array([3682.36, 554.1, 6027.8, 239.85, 405.13, 1473.25])
    s = np.array([3682.36, 554.1, 858.423, 63.701, 35.613, 525.66])
    mass = reconcile(M, x, s)
    ash = reconcile_component(M, mass.adjusted, np.array([23.04, 49.95, 32.59, 80.37, 35.35, 24.78]),
                              np.array([23.04, 2.747, 6.06, 3.201, 4.683, 4.898]))
    dist = distribution(list(mass.adjusted), list(ash.adjusted))
    assert [round(v, 2) for v in dist] == [100.0, 21.78, 78.22, 16.21, 11.46, 50.55]  # Tabela 2, iteração 1
    # o balanço de cada operação fecha em distribuição: saídas somam 100%
    assert dist[1] + dist[2] == pytest.approx(100.0, abs=1e-6)
    assert dist[3] + dist[4] + dist[5] == pytest.approx(dist[2], abs=1e-6)
    ind = indicators(mass.adjusted[0], ash.adjusted[0], mass.adjusted[5], ash.adjusted[5])
    assert ind.recovery_pct == pytest.approx(dist[5], abs=1e-9)  # recuperação = distribuição no concentrado
    assert ind.yield_pct == pytest.approx(100 * mass.adjusted[5] / mass.adjusted[0])
    assert ind.concentration_ratio == pytest.approx(1 / (ind.yield_pct / 100))


def test_indicators_reject_invalid_values():
    with pytest.raises(InvalidInputError):
        indicators(0, 10, 5, 20)
    with pytest.raises(InvalidInputError):
        indicators(100, 0, 5, 20)
    assert distribution([0.0, 1.0], [5.0, 5.0]) == [None, None]


def test_parse_decimal_accepts_comma_dot_and_thousands():
    assert parse_decimal("3,5") == 3.5 and parse_decimal("3.5") == 3.5
    assert parse_decimal("1.234,5") == 1234.5 and parse_decimal(" 12 ") == 12
    with pytest.raises(ServiceError):
        parse_decimal("abc")


def test_parse_pasted_variants_and_errors():
    assert parse_pasted("10,5\t1,2\n20\t2", 2) == [(1, 10.5, 1.2), (2, 20.0, 2.0)]
    assert parse_pasted("2;30;3", 2) == [(2, 30.0, 3.0)]
    with pytest.raises(ServiceError):
        parse_pasted("", 2)
    with pytest.raises(ServiceError):
        parse_pasted("10", 2)  # falta o desvio
    with pytest.raises(ServiceError):
        parse_pasted("9;30;3", 2)  # fluxo inexistente


def test_fmt_num_brazilian_format():
    assert fmt_num(3750.8234, 2) == "3.750,82" and fmt_num(0.5, 1) == "0,5" and fmt_num(None) == "–"
    assert fmt_num(-1234567.891, 3) == "-1.234.567,891"


def test_glossary_integrity():
    names = {t["termo"] for t in TERMS}
    assert len(names) == len(TERMS) and len({slug(t["termo"]) for t in TERMS}) == len(TERMS)
    for t in TERMS:
        assert t["categoria"] in CATEGORIES and len(t["definicao"]) > 30
        assert all(v in names for v in t["ver"]), (t["termo"], t["ver"])
    assert [c for c, _ in by_category()] == list(CATEGORIES) and all(terms for _, terms in by_category())
    for essential in ("Balanço de massas", "Recuperação metalúrgica", "Matriz M", "Redundância", "Fluxo não amostrado", "Hidrociclone"):
        assert essential in names


def test_faq_has_questions_and_answers():
    assert len(FAQ) >= 10 and all(i["p"].endswith("?") and len(i["r"]) > 40 for i in FAQ)
