"""Excitatory/inhibitory signs for chemical synapses.

Two sources, chosen by ``SignConfig.source``:

``transmitter`` (default)
    One sign per presynaptic neuron (Dale's principle) from its fast classical
    transmitter in the Wang et al. 2024 atlas. Acetylcholine is excitatory and
    GABA inhibitory. Glutamate can be either in C. elegans (excitatory through
    GLR/NMR receptors, inhibitory through GLC chloride channels), so its sign
    is a config option. So is the rule for neurons releasing more than one
    classical transmitter, and for neurons with none (monoamine-only, betaine
    or unidentified transmitter).

``fenyves``
    Per-edge signs predicted from presynaptic transmitter and postsynaptic
    receptor expression (Fenyves et al. 2020, PLOS Comput Biol 16:e1007974),
    read from a local CSV with columns ``pre,post,sign``. Edges the file does
    not cover fall back to the ``transmitter`` rule. See DATA.md for how to
    obtain the file; it is not bundled.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import numpy as np

CLASSICAL = ("Acetylcholine", "GABA", "Glutamate")
_CHOICES = {"excitatory": 1, "inhibitory": -1, "zero": 0}


@dataclass(frozen=True)
class SignConfig:
    source: str = "transmitter"  # "transmitter" or "fenyves"
    glutamate: str = "excitatory"  # "excitatory" or "inhibitory"
    # neurons with no classical transmitter: "excitatory", "inhibitory" or "zero" (silent)
    unknown: str = "excitatory"
    # with several classical transmitters, the first one in this order decides
    cotransmitter_priority: tuple[str, ...] = CLASSICAL
    fenyves_csv: str | None = None


def transmitter_sign(transmitters: list[str], cfg: SignConfig) -> tuple[int, str]:
    """Sign for one neuron and the rule that produced it (recorded for DATA.md)."""
    classical = [t for t in cfg.cotransmitter_priority if t in transmitters]
    if not classical:
        return _CHOICES[cfg.unknown], "unknown"
    t = classical[0]
    rule = t if len(classical) == 1 else f"{t} (co-releases {', '.join(classical[1:])})"
    if t == "Acetylcholine":
        return 1, rule
    if t == "GABA":
        return -1, rule
    return _CHOICES[cfg.glutamate], rule


def node_signs(
    neurons: list[str], transmitters: dict[str, list[str]], cfg: SignConfig
) -> tuple[np.ndarray, dict[str, str]]:
    signs = np.zeros(len(neurons), dtype=np.int8)
    rules = {}
    for k, n in enumerate(neurons):
        signs[k], rules[n] = transmitter_sign(transmitters.get(n, []), cfg)
    return signs, rules


def read_fenyves(path: str | Path) -> dict[tuple[str, str], int]:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"Fenyves sign file {path} not found. See DATA.md for how to obtain it, "
            "or use signs.source: transmitter."
        )
    with path.open() as f:
        return {(r["pre"], r["post"]): int(np.sign(float(r["sign"]))) for r in csv.DictReader(f)}


def edge_signs(
    neurons: list[str],
    chem: np.ndarray,
    transmitters: dict[str, list[str]],
    cfg: SignConfig,
) -> np.ndarray:
    """Sign matrix with the shape of ``chem``: nonzero exactly where an edge has a sign."""
    signs, _ = node_signs(neurons, transmitters, cfg)
    s = np.where(chem > 0, signs[:, None], 0).astype(np.int8)
    if cfg.source == "fenyves":
        if not cfg.fenyves_csv:
            raise ValueError("signs.source is 'fenyves' but signs.fenyves_csv is not set")
        index = {n: k for k, n in enumerate(neurons)}
        for (pre, post), sign in read_fenyves(cfg.fenyves_csv).items():
            i, j = index.get(pre), index.get(post)
            if i is not None and j is not None and chem[i, j] > 0:
                s[i, j] = sign
    elif cfg.source != "transmitter":
        raise ValueError(f"unknown signs.source {cfg.source!r}")
    return s
