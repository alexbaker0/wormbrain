"""Summary statistics of a connectome, used to compare the real graph with controls."""

from __future__ import annotations

import numpy as np
from scipy.sparse.csgraph import connected_components, shortest_path

from .connectome import Connectome


def _clustering(adj: np.ndarray) -> float:
    """Mean local clustering coefficient of the undirected version of ``adj``."""
    a = ((adj + adj.T) > 0).astype(float)
    np.fill_diagonal(a, 0)
    k = a.sum(1)
    triangles = np.einsum("ij,jk,ki->i", a, a, a) / 2
    possible = k * (k - 1) / 2
    return float(np.mean(np.divide(triangles, possible, out=np.zeros_like(k), where=possible > 0)))


def stats(conn: Connectome) -> dict:
    chem = conn.chem > 0
    gap = conn.gap > 0
    n = conn.n
    e = int(chem.sum())
    signs = conn.chem_sign[chem]
    weights = conn.chem[chem]
    role = np.array(conn.role)
    sensory, motor = role == "sensory", role == "motor"
    # hops from each sensory neuron to its nearest motor neuron, either synapse type,
    # following chemical synapses forwards and gap junctions both ways
    hops = shortest_path((chem | gap).astype(float), unweighted=True, directed=True)
    nearest = hops[np.ix_(sensory, motor)].min(1)
    reached = np.isfinite(nearest)
    n_scc, scc_labels = connected_components(chem, directed=True, connection="strong")
    return {
        "neurons": n,
        "classes": len(set(conn.cell_class)),
        "chem_edges": e,
        "chem_weight_total": float(weights.sum()),
        "chem_density": e / (n * (n - 1)),
        "chem_reciprocity": float((chem & chem.T).sum() / e),
        "excitatory_edges": int((signs > 0).sum()),
        "inhibitory_edges": int((signs < 0).sum()),
        "silent_edges": int((signs == 0).sum()),
        "excitatory_weight_fraction": float(weights[signs > 0].sum() / weights.sum()),
        "gap_edges": int(np.triu(gap, 1).sum()),
        "gap_weight_total": float(np.triu(conn.gap, 1).sum()),
        "gap_max_degree": int(gap.sum(1).max()),
        "max_in_degree": int(chem.sum(0).max()),
        "max_out_degree": int(chem.sum(1).max()),
        "clustering": _clustering(chem),
        "largest_scc": int(np.bincount(scc_labels).max()),
        "sensory_to_motor_hops_mean": float(nearest[reached].mean()),
        "sensory_reaching_motor": f"{int(reached.sum())}/{int(sensory.sum())}",
        "isolated_neurons": int(((chem.sum(0) + chem.sum(1) + gap.sum(1)) == 0).sum()),
        "nmj_neurons": int((conn.nmj.sum(1) > 0).sum()),
        "strong_components": int(n_scc),
    }
