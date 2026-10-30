"""Load the raw datasets (via the `cect` package) and cache them as plain arrays.

Everything downstream works from the cached arrays, so `cect` is only imported on
the first load. Sources and licences are listed in DATA.md.

Matrix convention, used throughout the package: ``M[i, j]`` is the connection
from cell ``i`` (presynaptic) to cell ``j`` (postsynaptic).
"""

from __future__ import annotations

import contextlib
import io
import json
import os
from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path

import numpy as np

CECT_VERSION = "0.3.5"
DATASET = "Cook2019Herm"


@dataclass(frozen=True)
class RawData:
    neurons: list[str]  # all 302 hermaphrodite neurons, in cect's preferred order
    muscles: list[str]  # body-wall muscles present in the dataset (MDL01 ... MVR24)
    chem: np.ndarray  # (neurons, neurons) chemical synapse weights, pre -> post
    gap: np.ndarray  # (neurons, neurons) gap-junction weights, symmetric
    nmj: np.ndarray  # (neurons, muscles) chemical neuron -> muscle weights
    neurotransmitters: dict[str, list[str]]  # Wang et al. 2024 identities per neuron
    sim_class: dict[str, str]  # cect's Sensory / Interneuron / Motorneuron / Other
    pharyngeal: list[str]  # the 20 neurons of the pharyngeal nervous system
    cect_version: str


def cache_dir() -> Path:
    default = Path(__file__).resolve().parents[2] / "data" / "cache"
    return Path(os.environ.get("WORMBRAIN_CACHE", default))


def _cache_paths() -> tuple[Path, Path]:
    stem = cache_dir() / f"{DATASET}_cect{CECT_VERSION}"
    return stem.with_suffix(".npz"), stem.with_suffix(".json")


def _load_from_cect() -> RawData:
    installed = version("cect")
    if installed != CECT_VERSION:
        raise RuntimeError(f"wormbrain is pinned to cect=={CECT_VERSION}, found {installed}")
    # cect prints progress for every file it reads; keep it off our output.
    with contextlib.redirect_stdout(io.StringIO()):
        from cect.Cells import (
            BODY_WALL_MUSCLE_NAMES,
            PHARYNGEAL_NEURONS,
            PREFERRED_HERM_NEURON_NAMES,
            get_SIM_class,
        )
        from cect.readers.Cook2019HermReader import get_instance as cook
        from cect.readers.Wang2024HermReader import get_instance as wang

        cds = cook()
        nts = wang().all_neurotransmitters

    nodes = list(cds.nodes)
    neurons = [n for n in PREFERRED_HERM_NEURON_NAMES if n in nodes]
    muscles = sorted(n for n in nodes if n in BODY_WALL_MUSCLE_NAMES)
    ni = [nodes.index(n) for n in neurons]
    mi = [nodes.index(m) for m in muscles]
    cs = np.asarray(cds.connections["Generic_CS"], dtype=float)
    gj = np.asarray(cds.connections["Generic_GJ"], dtype=float)
    return RawData(
        neurons=neurons,
        muscles=muscles,
        chem=cs[np.ix_(ni, ni)],
        gap=gj[np.ix_(ni, ni)],
        nmj=cs[np.ix_(ni, mi)],
        neurotransmitters={n: [t for t in nts.get(n, []) if t] for n in neurons},
        sim_class={n: get_SIM_class(n) for n in neurons},
        pharyngeal=[n for n in neurons if n in PHARYNGEAL_NEURONS],
        cect_version=installed,
    )


def load_raw(refresh: bool = False) -> RawData:
    """Return the Cook et al. 2019 hermaphrodite data, from the cache when present."""
    npz_path, json_path = _cache_paths()
    if not refresh and npz_path.exists() and json_path.exists():
        arrays = np.load(npz_path)
        meta = json.loads(json_path.read_text())
        return RawData(
            neurons=meta["neurons"],
            muscles=meta["muscles"],
            chem=arrays["chem"],
            gap=arrays["gap"],
            nmj=arrays["nmj"],
            neurotransmitters=meta["neurotransmitters"],
            sim_class=meta["sim_class"],
            pharyngeal=meta["pharyngeal"],
            cect_version=meta["cect_version"],
        )

    raw = _load_from_cect()
    npz_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(npz_path, chem=raw.chem, gap=raw.gap, nmj=raw.nmj)
    meta = {
        "neurons": raw.neurons,
        "muscles": raw.muscles,
        "neurotransmitters": raw.neurotransmitters,
        "sim_class": raw.sim_class,
        "pharyngeal": raw.pharyngeal,
        "cect_version": raw.cect_version,
        "source": "Cook et al. 2019 (Nature 571:63-71), SI 5 corrected July 2020, via cect",
    }
    json_path.write_text(json.dumps(meta, indent=1))
    return raw
