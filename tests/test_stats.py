import numpy as np
import pytest

from wormbrain.stats import bootstrap_ci, holm, stratified_permutation


def test_permutation_exact_p_for_complete_separation():
    # 4 vs 4 in one stratum, fully separated: only 2 of 70 relabellings are as extreme
    a = {"s": np.array([5.0, 6, 7, 8])}
    b = {"s": np.array([1.0, 2, 3, 4])}
    d, p, n = stratified_permutation(a, b)
    assert d == pytest.approx(4.0) and n == 70 and p == pytest.approx(2 / 70)


def test_permutation_respects_strata():
    # a stratum offset alone must not create a difference: labels only move within strata
    a = {"x": np.array([0.0, 1]), "y": np.array([100.0, 101])}
    b = {"x": np.array([0.0, 1]), "y": np.array([100.0, 101])}
    d, p, n = stratified_permutation(a, b)
    assert d == pytest.approx(0.0) and p == pytest.approx(1.0) and n == 36


def test_permutation_ignores_empty_strata():
    a = {"x": np.array([3.0, 4]), "y": np.array([])}
    b = {"x": np.array([1.0, 2]), "y": np.array([7.0])}
    d, p, n = stratified_permutation(a, b)
    assert d == pytest.approx(2.0) and n == 6


def test_bootstrap_interval_covers_difference():
    rng = np.random.default_rng(0)
    a = {"s": rng.normal(1.0, 0.1, 8)}
    b = {"s": rng.normal(0.0, 0.1, 8)}
    lo, hi = bootstrap_ci(a, b, n=2000)
    assert lo < a["s"].mean() - b["s"].mean() < hi and lo > 0.5


def test_holm():
    np.testing.assert_allclose(holm([0.01, 0.04]), [0.02, 0.04])
    np.testing.assert_allclose(holm([0.04, 0.01]), [0.04, 0.02])
    np.testing.assert_allclose(holm([0.03, 0.03]), [0.06, 0.06])
