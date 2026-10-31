import numpy as np

from wormbrain.controls import make_condition
from wormbrain.layout import CIRCUIT, circuit_edges, whole_layout


def test_whole_layout_columns_and_range(conn):
    x, y = whole_layout(conn)
    assert set(np.unique(x)) == {0.0, 1.0, 2.0}
    assert y.min() == 0.0 and y.max() == 1.0
    roles = np.array(conn.role)
    assert np.all(x[roles == "sensory"] == 0) and np.all(x[roles == "motor"] == 2)


def test_circuit_edges(conn):
    edges = circuit_edges(conn)
    motor = {c for c, col, _ in CIRCUIT if col == 3}
    pairs = {(e["from"], e["to"]) for e in edges if not e["gap"]}
    assert ("ASE", "AIY") in pairs and ("ASE", "AIB") in pairs  # the known salt pathway
    assert not any(e["from"] in motor and e["to"] in motor for e in edges)
    assert all(e["w"] >= 8 for e in edges)
    # a rewired brain draws its own, different links
    other = {(e["from"], e["to"]) for e in circuit_edges(make_condition(conn, "random", 0))
             if not e["gap"]}  # fmt: skip
    assert other != pairs
