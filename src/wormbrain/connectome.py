"""The fixed graph the brain runs on: neurons, signed chemical synapses, gap junctions
and neuromuscular junctions, built from the raw data and a config.

Matrices follow the package convention ``M[i, j]`` = from ``i`` (pre) to ``j`` (post).
"""

from __future__ import annotations

import dataclasses
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import yaml

from .data import RawData, load_raw
from .signs import SignConfig, edge_signs, node_signs

# Classes whose members also differ by a dorsal/ventral letter (White et al. 1986),
# e.g. RMDDL, RMDVR, RMDL all belong to RMD.
_DV_CLASSES = {
    "CEP", "IL1", "IL2", "OLQ", "RMD", "RME", "SAA", "SAB",
    "SIA", "SIB", "SMB", "SMD", "URA", "URY",
}  # fmt: skip
_NUMBERED = re.compile(r"^(AS|DA|DB|DD|VA|VB|VC|VD)\d+$")
_MUSCLE = re.compile(r"^M([DV][LR])(\d\d)$")
ROLE = {"Sensory": "sensory", "Interneuron": "inter", "Motorneuron": "motor", "Other": "other"}


def neuron_class(name: str, all_names: set[str]) -> str:
    """Anatomical class: VB1..VB11 -> VB, AIYL/AIYR -> AIY, RMDDL -> RMD."""
    m = _NUMBERED.match(name)
    if m:
        return m.group(1)
    base = name
    if name[-1] in "LR" and name[:-1] + {"L": "R", "R": "L"}[name[-1]] in all_names:
        base = name[:-1]
    if base[-1] in "DV" and base[:-1] in _DV_CLASSES:
        base = base[:-1]
    return base


@dataclass(frozen=True)
class Connectome:
    neurons: list[str]
    cell_class: list[str]  # anatomical class, used to tie parameters
    role: list[str]  # sensory / inter / motor / other
    chem: np.ndarray  # (N, N) synapse weights
    chem_sign: np.ndarray  # (N, N) int8 in {-1, 0, 1}, nonzero only where chem > 0
    gap: np.ndarray  # (N, N) symmetric gap-junction weights, zero diagonal
    nmj: np.ndarray  # (N, M) neuron -> body-wall muscle weights (never rewired)
    node_sign: np.ndarray  # (N,) transmitter-rule sign, used for neuron -> muscle synapses
    muscles: list[str]
    muscle_quadrant: list[str]  # DL / DR / VL / VR
    muscle_row: np.ndarray  # 1 (head) ... 24 (tail)
    label: str = "real"

    @property
    def n(self) -> int:
        return len(self.neurons)

    def index(self, names: list[str]) -> np.ndarray:
        lookup = {n: k for k, n in enumerate(self.neurons)}
        return np.array([lookup[n] for n in names], dtype=int)

    def classes(self) -> list[str]:
        return sorted(set(self.cell_class))

    def with_wiring(self, chem, chem_sign, gap, label: str) -> Connectome:
        return dataclasses.replace(self, chem=chem, chem_sign=chem_sign, gap=gap, label=label)


def load_config(path: str | Path) -> dict:
    return yaml.safe_load(Path(path).read_text()) or {}


def sign_config(cfg: dict) -> SignConfig:
    s = dict(cfg.get("signs", {}))
    if "cotransmitter_priority" in s:
        s["cotransmitter_priority"] = tuple(s["cotransmitter_priority"])
    return SignConfig(**s)


def build_connectome(cfg: dict | None = None, raw: RawData | None = None) -> Connectome:
    cfg = cfg or {}
    raw = raw or load_raw()
    keep = [
        k
        for k, n in enumerate(raw.neurons)
        if cfg.get("include_pharynx", False) or n not in raw.pharyngeal
    ]
    neurons = [raw.neurons[k] for k in keep]
    chem = raw.chem[np.ix_(keep, keep)].copy()
    gap = raw.gap[np.ix_(keep, keep)].copy()
    np.fill_diagonal(gap, 0.0)  # a gap junction onto itself carries no current
    # Autapses (37 in Cook 2019 outside the pharynx) are dropped so that the real graph
    # and every control live in the same space of graphs without self-loops.
    np.fill_diagonal(chem, 0.0)
    names = set(neurons)
    sub_nt = {n: raw.neurotransmitters.get(n, []) for n in neurons}
    sign = edge_signs(neurons, chem, sub_nt, sign_config(cfg))
    quad, row = zip(*(_MUSCLE.match(m).groups() for m in raw.muscles), strict=True)
    return Connectome(
        neurons=neurons,
        cell_class=[neuron_class(n, names) for n in neurons],
        role=[ROLE[raw.sim_class[n]] for n in neurons],
        chem=chem,
        chem_sign=sign,
        gap=gap,
        nmj=raw.nmj[keep].copy(),
        node_sign=node_signs(neurons, sub_nt, sign_config(cfg))[0],
        muscles=list(raw.muscles),
        muscle_quadrant=list(quad),
        muscle_row=np.array([int(r) for r in row]),
    )


def sign_rules(cfg: dict | None = None, raw: RawData | None = None) -> dict[str, str]:
    """Which rule set each neuron's sign, for documentation."""
    raw = raw or load_raw()
    return node_signs(raw.neurons, raw.neurotransmitters, sign_config(cfg or {}))[1]
