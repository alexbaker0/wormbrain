import numpy as np
import pytest

from wormbrain.connectome import build_connectome


def test_neuron_counts(raw, conn):
    assert len(raw.neurons) == 302
    assert len(raw.pharyngeal) == 20
    assert conn.n == 282
    assert not set(raw.pharyngeal) & set(conn.neurons)
    assert build_connectome({"include_pharynx": True}, raw).n == 302


def test_matrix_orientation_is_pre_to_post(conn):
    # AVA drives the A-class motor neurons, not the other way round
    i, j = conn.index(["AVAL", "VA5"])
    assert conn.chem[i, j] > 0
    assert conn.chem[j, i] == 0


def test_gap_junctions_symmetric(raw, conn):
    np.testing.assert_array_equal(raw.gap, raw.gap.T)
    np.testing.assert_array_equal(conn.gap, conn.gap.T)
    assert np.all(np.diag(conn.gap) == 0)
    assert conn.gap.min() >= 0
    assert np.all(np.diag(conn.chem) == 0)  # autapses dropped


def test_chemical_signs_only_on_edges(conn):
    assert conn.chem.min() >= 0
    assert np.all((conn.chem_sign != 0) == (conn.chem > 0))  # default config: every edge signed
    assert set(np.unique(conn.chem_sign)) <= {-1, 0, 1}


def test_neuromuscular_junctions_match_anatomy(conn):
    assert len(conn.muscles) == 95
    assert conn.muscle_row.min() == 1 and conn.muscle_row.max() == 24
    quad = np.array(conn.muscle_quadrant)
    for cls, side in [("VB", "V"), ("VA", "V"), ("DB", "D"), ("DA", "D")]:
        rows = conn.nmj[[k for k, c in enumerate(conn.cell_class) if c == cls]]
        targets = quad[rows.sum(0) > 0]
        assert len(targets) and all(q[0] == side for q in targets), cls


def test_classes(conn):
    cls = dict(zip(conn.neurons, conn.cell_class, strict=True))
    assert len(conn.classes()) == 104  # White et al. 1986: 118 classes, 14 of them pharyngeal
    assert cls["AIYL"] == cls["AIYR"] == "AIY"
    assert {cls[f"VB{k}"] for k in range(1, 12)} == {"VB"}
    assert cls["RMDDL"] == cls["RMDVR"] == cls["RMDL"] == "RMD"
    assert cls["SABD"] == cls["SABVL"] == "SAB"
    assert cls["RID"] == "RID" and cls["RIVL"] == "RIV"


def _sign(conn, name):
    row = conn.chem_sign[conn.index([name])[0]]
    return set(np.unique(row[row != 0]))


def test_sign_rules(raw, conn):
    assert _sign(conn, "AIYL") == {1}  # acetylcholine
    assert _sign(conn, "DD3") == {-1}  # GABA
    assert _sign(conn, "AIZL") == {1}  # glutamate, default excitatory
    flipped = build_connectome({"signs": {"glutamate": "inhibitory"}}, raw)
    assert _sign(flipped, "AIZL") == {-1}
    assert _sign(flipped, "AIYL") == {1}
    silent = build_connectome({"signs": {"unknown": "zero"}}, raw)
    assert _sign(silent, "RID") == set()


def test_fenyves_source(raw, conn, tmp_path):
    with pytest.raises(FileNotFoundError):
        build_connectome({"signs": {"source": "fenyves", "fenyves_csv": "missing.csv"}}, raw)
    i, j = np.argwhere(conn.chem_sign > 0)[0]
    path = tmp_path / "signs.csv"
    path.write_text(f"pre,post,sign\n{conn.neurons[i]},{conn.neurons[j]},-1\n")
    f = build_connectome({"signs": {"source": "fenyves", "fenyves_csv": str(path)}}, raw)
    assert f.chem_sign[i, j] == -1
    assert (f.chem_sign != conn.chem_sign).sum() == 1
