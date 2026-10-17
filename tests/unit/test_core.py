"""Testes do núcleo de cálculo. Caso de aceitação: Tabelas 1 e 2 da monografia (iteração 1)."""

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.core import (
    ErrorModel,
    Flowsheet,
    InvalidInputError,
    IterationAction,
    Operation,
    SingularSystemError,
    apply_actions,
    has_converged,
    mean_std,
    reconcile,
    reconcile_component,
    sigma_from,
)
from app.core.iteration import FlowAction
from app.core.solver import gauss_solve

SHEET = Flowsheet(
    ("alim", "over", "under", "rej", "mid", "conc"),
    (Operation("ciclone", (0,), (1, 2)), Operation("espiral", (2,), (3, 4, 5))),
)
X_MASS = np.array([3682.36, 554.1, 6027.8, 239.85, 405.13, 1473.25])
S_MASS = np.array([3682.36, 554.1, 858.423, 63.701, 35.613, 525.66])
EXPECTED_MASS = [3750.82, 552.55, 3198.27, 255.41, 409.99, 2532.87]
X_ASH = np.array([23.04, 49.95, 32.59, 80.37, 35.35, 24.78])
S_ASH = np.array([23.04, 2.747, 6.06, 3.201, 4.683, 4.898])
EXPECTED_ASH = [33.77, 49.93, 30.98, 80.39, 35.42, 25.28]


def test_matrix_m():
    m = SHEET.matrix()
    assert m.shape == (2, 6)
    assert m[0].tolist() == [1, -1, -1, 0, 0, 0]
    assert m[1].tolist() == [0, 0, 1, -1, -1, -1]


@pytest.mark.parametrize("method", ["gauss", "closed_form"])
def test_cambui_mass_iteration_1(method):
    res = reconcile(SHEET.matrix(), X_MASS, S_MASS, method=method)
    np.testing.assert_allclose(res.adjusted, EXPECTED_MASS, atol=0.01)


def test_cambui_ash_iteration_1():
    mass = reconcile(SHEET.matrix(), X_MASS, S_MASS)
    res = reconcile_component(SHEET.matrix(), mass.adjusted, X_ASH, S_ASH)
    np.testing.assert_allclose(res.adjusted, EXPECTED_ASH, atol=0.01)


def test_balance_closes_after_adjustment():
    res = reconcile(SHEET.matrix(), X_MASS, S_MASS)
    np.testing.assert_allclose(SHEET.matrix() @ res.adjusted, 0, atol=1e-8)
    assert np.abs(res.residual_before).max() > 1  # os dados originais não fechavam


def test_consistent_data_is_not_changed():
    x = np.array([100.0, 40.0, 60.0, 10.0, 20.0, 30.0])
    res = reconcile(SHEET.matrix(), x, np.ones(6))
    np.testing.assert_allclose(res.adjusted, x, atol=1e-9)
    assert res.chi2 == pytest.approx(0, abs=1e-12)


def test_more_reliable_measure_moves_less():
    x = np.array([100.0, 40.0, 50.0, 10.0, 20.0, 30.0])  # fluxo 3 inconsistente
    precise = reconcile(SHEET.matrix(), x, np.array([1.0, 1, 0.01, 1, 1, 1]))
    vague = reconcile(SHEET.matrix(), x, np.array([1.0, 1, 100.0, 1, 1, 1]))
    assert abs(precise.adjusted[2] - 50) < abs(vague.adjusted[2] - 50)


def test_unsampled_flow_is_filled_in():
    x = np.array([100.0, 40.0, 1.0, 10.0, 20.0, 30.0])  # fluxo 3 sem medida real
    res = reconcile(SHEET.matrix(), x, np.array([1.0, 1, 1.0, 1, 1, 1]) * np.array([1, 1, 1, 1, 1, 1]))
    wide = reconcile(SHEET.matrix(), x, np.array([1.0, 1, 1e3, 1, 1, 1]))
    assert wide.adjusted[2] == pytest.approx(60, abs=0.5)
    assert res.adjusted[2] != pytest.approx(60, abs=0.5)


def test_zero_sigma_rejected():
    with pytest.raises(InvalidInputError):
        reconcile(SHEET.matrix(), X_MASS, np.array([1.0, 0, 1, 1, 1, 1]))


def test_redundant_constraints_rejected():
    m = np.array([[1.0, -1, 0], [2, -2, 0]])
    with pytest.raises(SingularSystemError):
        reconcile(m, np.ones(3), np.ones(3))


def test_gauss_matches_numpy():
    rng = np.random.default_rng(0)
    a = rng.normal(size=(8, 8))
    b = rng.normal(size=8)
    np.testing.assert_allclose(gauss_solve(a, b), np.linalg.solve(a, b), atol=1e-9)


def test_gauss_singular():
    with pytest.raises(SingularSystemError):
        gauss_solve(np.array([[1.0, 2], [2, 4]]), np.array([1.0, 2]))


@settings(max_examples=40, deadline=None)
@given(
    x=st.lists(st.floats(1, 1e4), min_size=6, max_size=6),
    s=st.lists(st.floats(0.1, 100), min_size=6, max_size=6),
)
def test_property_balance_always_closes_and_methods_agree(x, s):
    a = reconcile(SHEET.matrix(), np.array(x), np.array(s), method="gauss")
    b = reconcile(SHEET.matrix(), np.array(x), np.array(s), method="closed_form")
    np.testing.assert_allclose(SHEET.matrix() @ a.adjusted, 0, atol=1e-5 * max(x))
    np.testing.assert_allclose(a.adjusted, b.adjusted, rtol=1e-6, atol=1e-6 * max(x))


def test_flowsheet_validation():
    assert SHEET.validate() == []
    bad = Flowsheet(("a", "b", "c"), (Operation("op", (0,), (1,)),))
    assert any("não se liga" in a.message for a in bad.validate())
    twice = Flowsheet(("a", "b"), (Operation("o1", (0,), (1,)), Operation("o2", (0,), (1,))))
    assert any(a.severity.value == "error" for a in twice.validate())
    split = Flowsheet(("a", "b", "c", "d"), (Operation("o1", (0,), (1,)), Operation("o2", (2,), (3,))))
    assert any(a.severity.value == "warning" for a in split.validate())


def test_error_models():
    assert sigma_from(200, ErrorModel.DESVIO_PADRAO, 5) == 5
    assert sigma_from(200, ErrorModel.INCERTEZA_PCT, 10) == pytest.approx(20)
    assert sigma_from(200, ErrorModel.CERTEZA_PCT, 90) == pytest.approx(20)
    with pytest.raises(InvalidInputError):
        sigma_from(200, ErrorModel.CERTEZA_PCT, 100)
    with pytest.raises(InvalidInputError):
        sigma_from(200, ErrorModel.DESVIO_PADRAO, 0)


def test_mean_std():
    mean, std = mean_std([10, 12, 14])
    assert mean == 12 and std == pytest.approx(2)
    with pytest.raises(InvalidInputError):
        mean_std([1])
    with pytest.raises(InvalidInputError):
        mean_std([3, 3, 3])


def test_iteration_actions():
    res = reconcile(SHEET.matrix(), X_MASS, S_MASS)
    acts = [FlowAction(IterationAction.NEW, 6000.0), FlowAction(IterationAction.CALCULATED)] + [FlowAction()] * 4
    x, s = apply_actions(X_MASS, S_MASS, res.adjusted, acts)
    assert x[0] == 6000 and s[0] == 6000  # sigma = valor para novo sem desvio
    assert x[1] == pytest.approx(res.adjusted[1]) and s[1] == S_MASS[1]
    assert x[2] == X_MASS[2]
    assert has_converged(res.adjusted, res.adjusted)
    assert not has_converged(res.adjusted, res.adjusted * 1.1)
