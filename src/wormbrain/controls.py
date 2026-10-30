"""Control graphs for the wiring comparison.

Only neuron-to-neuron wiring changes. Neuron identities, the sensory inputs, the
neuromuscular junctions and therefore the trainable parameter count are the same
in every condition.

=================  ==========================================================
real               the connectome as loaded
rewired            degree-preserving edge swaps (Maslov & Sneppen 2002). Chemical:
                   every neuron keeps its in- and out-degree; each edge keeps its
                   weight and sign, which stay with its presynaptic neuron, so
                   out-strength and each neuron's sign are kept too. Gap junctions:
                   undirected swaps that keep every neuron's degree and symmetry.
random             Erdős–Rényi: the same number of chemical edges and of gap
                   junctions placed uniformly at random; the real weights and the
                   real chemical signs are dealt out to them at random.
sign_shuffled      real wiring, chemical signs permuted across edges
weight_shuffled    real wiring and signs, weights permuted across edges
=================  ==========================================================
"""

from __future__ import annotations

import numpy as np

from .connectome import Connectome

CONDITIONS = ("real", "rewired", "random", "sign_shuffled", "weight_shuffled")


def rewire_chemical(chem, sign, rng, swaps_per_edge: int = 10):
    src, dst = np.nonzero(chem)
    w, s = chem[src, dst], sign[src, dst]
    adj = chem > 0
    m = len(src)
    picks = rng.integers(0, m, size=(swaps_per_edge * m, 2))
    for a, b in picks:
        s1, d1, s2, d2 = src[a], dst[a], src[b], dst[b]
        if d1 == d2 or s1 == d2 or s2 == d1 or adj[s1, d2] or adj[s2, d1]:
            continue
        adj[s1, d1] = adj[s2, d2] = False
        adj[s1, d2] = adj[s2, d1] = True
        dst[a], dst[b] = d2, d1
    return _directed(chem.shape, src, dst, w, s)


def rewire_gap(gap, rng, swaps_per_edge: int = 10):
    i, j = np.nonzero(np.triu(gap, 1))
    w = gap[i, j]
    adj = gap > 0
    m = len(i)
    picks = rng.integers(0, m, size=(swaps_per_edge * m, 2))
    flips = rng.random(swaps_per_edge * m) < 0.5
    for (a, b), flip in zip(picks, flips, strict=True):
        p, q = i[a], j[a]
        r, t = (j[b], i[b]) if flip else (i[b], j[b])
        # (p-q), (r-t)  ->  (p-t), (r-q)
        if a == b or p == t or r == q or adj[p, t] or adj[r, q]:
            continue
        adj[p, q] = adj[q, p] = adj[r, t] = adj[t, r] = False
        adj[p, t] = adj[t, p] = adj[r, q] = adj[q, r] = True
        i[a], j[a], i[b], j[b] = p, t, r, q
    return _undirected(gap.shape, i, j, w)


def random_chemical(chem, sign, rng):
    n = chem.shape[0]
    src, dst = np.nonzero(chem)
    off = np.flatnonzero(~np.eye(n, dtype=bool))
    cells = rng.choice(off, size=len(src), replace=False)
    order = rng.permutation(len(src))
    w, s = chem[src, dst][order], sign[src, dst][order]
    return _directed(chem.shape, cells // n, cells % n, w, s)


def random_gap(gap, rng):
    n = gap.shape[0]
    i, j = np.nonzero(np.triu(gap, 1))
    upper = np.flatnonzero(np.triu(np.ones((n, n), dtype=bool), 1))
    cells = rng.choice(upper, size=len(i), replace=False)
    return _undirected(gap.shape, cells // n, cells % n, rng.permutation(gap[i, j]))


def shuffle_signs(chem, sign, rng):
    out = np.zeros_like(sign)
    src, dst = np.nonzero(chem)
    out[src, dst] = rng.permutation(sign[src, dst])
    return out


def shuffle_weights(chem, rng):
    out = np.zeros_like(chem)
    src, dst = np.nonzero(chem)
    out[src, dst] = rng.permutation(chem[src, dst])
    return out


def make_condition(conn: Connectome, condition: str, seed: int) -> Connectome:
    """The connectome under a control condition; deterministic for a given seed."""
    rng = np.random.default_rng(seed)
    chem, sign, gap = conn.chem, conn.chem_sign, conn.gap
    if condition == "real":
        return conn
    if condition == "rewired":
        chem, sign = rewire_chemical(chem, sign, rng)
        gap = rewire_gap(gap, rng)
    elif condition == "random":
        chem, sign = random_chemical(chem, sign, rng)
        gap = random_gap(gap, rng)
    elif condition == "sign_shuffled":
        sign = shuffle_signs(chem, sign, rng)
    elif condition == "weight_shuffled":
        chem = shuffle_weights(chem, rng)
    else:
        raise ValueError(f"unknown condition {condition!r}; choose from {CONDITIONS}")
    return conn.with_wiring(chem, sign, gap, label=f"{condition}/seed{seed}")


def _directed(shape, src, dst, w, s):
    chem = np.zeros(shape)
    sign = np.zeros(shape, dtype=np.int8)
    chem[src, dst] = w
    sign[src, dst] = s
    return chem, sign


def _undirected(shape, i, j, w):
    gap = np.zeros(shape)
    gap[i, j] = w
    gap[j, i] = w
    return gap
