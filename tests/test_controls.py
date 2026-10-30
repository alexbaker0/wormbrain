import numpy as np
import pytest

from wormbrain.controls import CONDITIONS, make_condition


def _degrees(adj):
    return adj.sum(0), adj.sum(1)


def _sorted_edges(m):
    return np.sort(m[m != 0])


@pytest.fixture(scope="module")
def rewired(conn):
    return make_condition(conn, "rewired", seed=1)


def test_rewired_keeps_chemical_degrees_strength_and_signs(conn, rewired):
    a, b = conn.chem > 0, rewired.chem > 0
    for x, y in zip(_degrees(a), _degrees(b), strict=True):
        np.testing.assert_array_equal(x, y)
    np.testing.assert_allclose(conn.chem.sum(1), rewired.chem.sum(1))  # out-strength
    for s in (-1, 1):  # each neuron's outgoing excitatory / inhibitory edge counts
        np.testing.assert_array_equal((conn.chem_sign == s).sum(1), (rewired.chem_sign == s).sum(1))
    assert np.all(np.diag(rewired.chem) == 0)
    assert np.all((rewired.chem_sign != 0) == b)
    assert (a & b).sum() / a.sum() < 0.2  # wiring really shuffled


def test_rewired_keeps_gap_degrees_and_symmetry(conn, rewired):
    np.testing.assert_array_equal(rewired.gap, rewired.gap.T)
    np.testing.assert_array_equal((conn.gap > 0).sum(0), (rewired.gap > 0).sum(0))
    np.testing.assert_array_equal(_sorted_edges(conn.gap), _sorted_edges(rewired.gap))
    assert np.all(np.diag(rewired.gap) == 0)
    overlap = ((conn.gap > 0) & (rewired.gap > 0)).sum() / (conn.gap > 0).sum()
    assert overlap < 0.3


def test_random_matches_counts_weights_and_sign_ratio(conn):
    r = make_condition(conn, "random", seed=1)
    assert (r.chem > 0).sum() == (conn.chem > 0).sum()
    np.testing.assert_array_equal(_sorted_edges(conn.chem), _sorted_edges(r.chem))
    np.testing.assert_array_equal(_sorted_edges(conn.chem_sign), _sorted_edges(r.chem_sign))
    np.testing.assert_array_equal(r.gap, r.gap.T)
    np.testing.assert_array_equal(_sorted_edges(conn.gap), _sorted_edges(r.gap))
    assert np.all(np.diag(r.chem) == 0) and np.all(np.diag(r.gap) == 0)


def test_shuffles_keep_adjacency(conn):
    s = make_condition(conn, "sign_shuffled", seed=1)
    np.testing.assert_array_equal(s.chem, conn.chem)
    np.testing.assert_array_equal(_sorted_edges(s.chem_sign), _sorted_edges(conn.chem_sign))
    assert (s.chem_sign != conn.chem_sign).any()
    w = make_condition(conn, "weight_shuffled", seed=1)
    np.testing.assert_array_equal(w.chem > 0, conn.chem > 0)
    np.testing.assert_array_equal(w.chem_sign, conn.chem_sign)
    np.testing.assert_array_equal(_sorted_edges(w.chem), _sorted_edges(conn.chem))


@pytest.mark.parametrize("condition", CONDITIONS)
def test_inputs_outputs_untouched_and_deterministic(conn, condition):
    a = make_condition(conn, condition, seed=3)
    assert a.neurons == conn.neurons and a.cell_class == conn.cell_class
    np.testing.assert_array_equal(a.nmj, conn.nmj)
    b = make_condition(conn, condition, seed=3)
    np.testing.assert_array_equal(a.chem, b.chem)
    np.testing.assert_array_equal(a.chem_sign, b.chem_sign)
    np.testing.assert_array_equal(a.gap, b.gap)
    if condition != "real":
        c = make_condition(conn, condition, seed=4)
        assert not (np.array_equal(a.chem, c.chem) and np.array_equal(a.chem_sign, c.chem_sign))
