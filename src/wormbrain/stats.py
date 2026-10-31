"""Statistics for the pre-registered comparison (see ANALYSIS_PLAN.md).

Samples are dicts {stratum: 1-D array}; strata are the glutamate settings, and
labels are only ever permuted within a stratum.
"""

from __future__ import annotations

import itertools

import numpy as np


def stratified_permutation(a: dict, b: dict) -> tuple[float, float, int]:
    """Two-sided exact permutation test on mean(a) - mean(b), relabelling within strata.

    Returns (observed difference, p value, number of relabellings).
    """
    strata = [s for s in a if len(a[s]) and len(b.get(s, []))]
    obs = np.mean(np.concatenate([a[s] for s in strata])) - np.mean(
        np.concatenate([b[s] for s in strata]))  # fmt: skip
    per_stratum = []
    for s in strata:
        pooled, na = np.concatenate([a[s], b[s]]), len(a[s])
        splits = []
        for idx in itertools.combinations(range(len(pooled)), na):
            mask = np.zeros(len(pooled), bool)
            mask[list(idx)] = True
            splits.append((pooled[mask].sum(), pooled[~mask].sum()))
        per_stratum.append(np.array(splits))
    na_tot = sum(len(a[s]) for s in strata)
    nb_tot = sum(len(b[s]) for s in strata)
    sums_a, sums_b = np.zeros(1), np.zeros(1)
    for sp in per_stratum:  # all combinations across strata
        sums_a = (sums_a[:, None] + sp[None, :, 0]).ravel()
        sums_b = (sums_b[:, None] + sp[None, :, 1]).ravel()
    diffs = sums_a / na_tot - sums_b / nb_tot
    p = float(np.mean(np.abs(diffs) >= abs(obs) - 1e-12))
    return float(obs), p, len(diffs)


def bootstrap_ci(a: dict, b: dict, n=10_000, seed=0) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    strata = [s for s in a if len(a[s]) and len(b.get(s, []))]
    diffs = np.empty(n)
    for i in range(n):
        ra = np.concatenate([rng.choice(a[s], len(a[s])) for s in strata])
        rb = np.concatenate([rng.choice(b[s], len(b[s])) for s in strata])
        diffs[i] = ra.mean() - rb.mean()
    return float(np.percentile(diffs, 2.5)), float(np.percentile(diffs, 97.5))


def holm(pvals: list[float]) -> list[float]:
    order = np.argsort(pvals)
    adj, running = np.empty(len(pvals)), 0.0
    for rank, i in enumerate(order):
        running = max(running, (len(pvals) - rank) * pvals[i])
        adj[i] = min(1.0, running)
    return adj.tolist()
