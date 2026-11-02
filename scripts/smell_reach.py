"""How far does a smell change travel through a trained brain?

    uv run python scripts/smell_reach.py

The same fake rising/falling smell as scripts/steering_probe.py; for each neuron group the
size of the smell-locked part of its activity (peak-to-peak of the phase-averaged trace)
and, after the slash, its total variation. Writes reports/smell_reach.md.
"""

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from steering_probe import PERIOD, FakeSmell

from wormbrain.brain import BrainController
from wormbrain.env import run_episode
from wormbrain.export import build_brain
from wormbrain.locomotion import FLAT

groups = {
    "ASE": ["ASEL", "ASER"],
    "AIY": ["AIYL", "AIYR"],
    "AIZ": ["AIZL", "AIZR"],
    "AIB": ["AIBL", "AIBR"],
    "RIA": ["RIAL", "RIAR"],
    "SMDD": ["SMDDL", "SMDDR"],
    "SMDV": ["SMDVL", "SMDVR"],
    "RMDD": ["RMDDL", "RMDDR"],
    "RMDV": ["RMDVL", "RMDVR"],
    "AVA": ["AVAL", "AVAR"],
    "AVB": ["AVBL", "AVBR"],
}
lines = []
CASES = [
    ("comparison", "real_glu-excitatory_seed1"),
    ("patches_scratch", "real_glu-excitatory_seed1"),
    ("patches_sym", "real_glu-excitatory_seed0"),
    ("patches_sym", "real_glu-inhibitory_seed1"),
]
if len(sys.argv) > 1:  # report folder names: every run in reports/<name>/runs
    CASES = [
        (f, p.stem) for f in sys.argv[1:] for p in sorted(Path("reports", f, "runs").glob("*.json"))
    ]
for f, r in CASES:
    run = json.load(open(f"reports/{f}/runs/{r}.json"))
    b = build_brain(run)
    x = np.array(run["x"])
    ctl = BrainController(b, x[None], record_every=5)
    ep = run_episode(FakeSmell(ctl), FLAT, np.zeros((1, 2)), np.zeros(1), duration=100.0, dt=0.02)
    V = np.array(ctl.activity)[:, 0]  # (T, n)
    t = np.arange(1, len(V) + 1) * 5 * 0.02
    keep = t > 20
    # smell-locked component: average v over phase bins, range across bins
    ph = ((t % PERIOD) / PERIOD * 10).astype(int)
    out = []
    for ns in groups.values():
        idx = b.conn.index(ns)
        v = V[:, idx].mean(1)
        prof = np.array([v[keep & (ph == k)].mean() for k in range(10)])
        out.append(f"{np.ptp(prof):.3f} / {v[keep].std():.3f}")
    line = f"| {f} | {r} | " + " | ".join(out) + " |"
    lines.append(line)
    print(line)
open(
    "reports/smell_reach.md" if len(sys.argv) == 1 else f"reports/{sys.argv[1]}/smell_reach.md", "w"
).write(
    "\n".join(
        [
            "# Smell reach",
            "",
            "Smell-locked activity / total activity variation per group.",
            "",
            "| run folder | run | " + " | ".join(groups) + " |",
            "|---|---|" + "---|" * len(groups),
            *lines,
            "",
        ]
    )
)
