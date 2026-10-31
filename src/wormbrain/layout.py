"""Layouts for drawing the wiring, shared by scripts/connectome_figure.py and the web page.

``whole_layout``: every neuron in three columns (sensory, inter, motor), ordered so
that connected neurons sit near each other. ``circuit_edges``: the class-level circuit
from the salt sensors to the motor neurons, with synapse counts.
"""

from __future__ import annotations

import numpy as np

from .connectome import Connectome

COLUMNS = {"sensory": 0, "inter": 1, "motor": 2, "other": 1}

# class-level salt circuit: (class, column, row)
CIRCUIT = [
    ("ASE", 0, 3.5),
    ("AIY", 1, 1), ("AIZ", 1, 3), ("AIB", 1, 5), ("AIA", 1, 7),
    ("RIA", 2, 0), ("RIB", 2, 2), ("RIM", 2, 4), ("AVA", 2, 6), ("AVB", 2, 8),
    ("SMD", 3, -0.5), ("RMD", 3, 1), ("SMB", 3, 2.5),
    ("VB", 3, 4), ("DB", 3, 5), ("VA", 3, 6.5), ("DA", 3, 7.5), ("VD", 3, 9), ("DD", 3, 10),
]  # fmt: skip
MIN_SYNAPSES = 8  # class-to-class links with fewer synapses are not drawn


def order_column(idx, y, adj, sweeps=12):
    """Barycentric ordering: move each neuron towards the mean height of its partners."""
    for _ in range(sweeps):
        w = adj[idx].sum(1)
        bary = np.where(w > 0, adj[idx] @ y / np.maximum(w, 1e-12), y[idx])
        ranked = np.argsort(bary, kind="stable")
        y[np.array(idx)[ranked]] = np.linspace(0, 1, len(idx))
    return y


def whole_layout(conn: Connectome) -> tuple[np.ndarray, np.ndarray]:
    """(x, y) per neuron: x is the column 0, 1, 2; y in [0, 1]."""
    col = np.array([COLUMNS[r] for r in conn.role])
    adj = (conn.chem + conn.chem.T + conn.gap).astype(float)
    y = np.zeros(conn.n)
    for c in range(3):
        idx = list(np.flatnonzero(col == c))
        idx.sort(key=lambda i: (conn.cell_class[i], conn.neurons[i]))
        y[idx] = np.linspace(0, 1, len(idx))
    for _ in range(3):
        for c in range(3):
            y = order_column(list(np.flatnonzero(col == c)), y, adj)
    return col.astype(float), y


def circuit_members(conn: Connectome) -> dict[str, list[int]]:
    return {c: [i for i, k in enumerate(conn.cell_class) if k == c] for c, _, _ in CIRCUIT}


def circuit_edges(conn: Connectome, min_synapses: int = MIN_SYNAPSES) -> list[dict]:
    """Class-to-class links of the salt circuit (motor-to-motor left out for clarity).

    Chemical links carry the summed synapse weight and the sign of the summed signed
    weight; gap-junction links are undirected.
    """
    members = circuit_members(conn)
    names = [c for c, _, _ in CIRCUIT]
    motor = {c for c, col, _ in CIRCUIT if col == 3}
    edges = []
    for a in names:
        for b in names:
            if a == b or (a in motor and b in motor):
                continue
            block = np.ix_(members[a], members[b])
            w = float(conn.chem[block].sum())
            if w >= min_synapses:
                signed = float((conn.chem[block] * conn.chem_sign[block]).sum())
                edges.append({"from": a, "to": b, "w": w, "sign": int(np.sign(signed)),
                              "gap": False})  # fmt: skip
    for k, a in enumerate(names):
        for b in names[k + 1 :]:
            if a in motor and b in motor:
                continue
            g = float(conn.gap[np.ix_(members[a], members[b])].sum())
            if g >= min_synapses:
                edges.append({"from": a, "to": b, "w": g, "sign": 0, "gap": True})
    return edges
