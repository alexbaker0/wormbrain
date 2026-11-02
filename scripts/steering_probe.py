"""Can a trained brain steer at all? Feed it a fake smell that rises and falls.

    uv run python scripts/steering_probe.py

On a flat field the smell at the head is replaced by a triangle wave (10 s rising from 0.05
to 0.6, then 10 s falling), whatever the worm does. A steering brain turns differently when
the smell rises than when it falls. Reports the signed turning rate (deg/s) in each phase
and the difference (the steering response), the share of turning that is one-way, and the
crawling speed. 8 headings x 120 s, the first 20 s ignored.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from wormbrain.brain import BrainController
from wormbrain.controllers import GradientSteering
from wormbrain.env import run_episode
from wormbrain.export import build_brain
from wormbrain.locomotion import FLAT

PERIOD, LO, HI = 20.0, 0.05, 0.6
BRAINS = [
    ("milestone 6 (gradient reward)", "reports/comparison/runs", "real_glu-excitatory_seed1"),
    ("milestone 6 (gradient reward)", "reports/comparison/runs", "real_glu-inhibitory_seed1"),
    ("E. far food (straight steerer)", "reports/natural_far/runs", "real_glu-excitatory_seed1"),
    ("patch v2 + offset", "reports/patches_dv/runs", "real_glu-excitatory_seed1"),
    ("from scratch, usual", "reports/patches_scratch/runs", "real_glu-excitatory_seed1"),
    ("from scratch, usual", "reports/patches_scratch/runs", "real_glu-inhibitory_seed0"),
    ("from scratch, symmetric", "reports/patches_sym/runs", "real_glu-excitatory_seed0"),
    ("from scratch, symmetric", "reports/patches_sym/runs", "real_glu-inhibitory_seed0"),
    ("from scratch, symmetric", "reports/patches_sym/runs", "real_glu-excitatory_seed1"),
    ("from scratch, symmetric", "reports/patches_sym/runs", "real_glu-inhibitory_seed1"),
]


def smell(t):
    ph = (t % PERIOD) / PERIOD
    return LO + (HI - LO) * (2 * ph if ph < 0.5 else 2 - 2 * ph)


class FakeSmell:
    def __init__(self, inner):
        self.inner = inner

    def reset(self, n):
        self.inner.reset(n)

    def step(self, obs, dt):
        return self.inner.step(obs | {"conc": np.full_like(obs["conc"], smell(obs["t"]))}, dt)


def probe(make, n=8):
    heading = np.linspace(0, 2 * np.pi, n, endpoint=False)
    ep = run_episode(FakeSmell(make(n)), FLAT, np.zeros((n, 2)), heading, duration=120.0, dt=0.02)
    t, c = ep.t, ep.centroid
    k = 10  # 2 s windows
    d = c[k:] - c[:-k]
    ang = np.unwrap(np.arctan2(d[..., 1], d[..., 0]), axis=0)
    rate = np.rad2deg(np.diff(ang, axis=0)) / (t[1] - t[0])  # (T, n) signed deg/s
    tm = t[k + 1 :] - (t[1] - t[0]) * k / 2  # window centres
    ph = (tm % PERIOD) / PERIOD
    keep = tm > 20.0
    rising, falling = keep & (ph < 0.5), keep & (ph >= 0.5)
    r_up, r_down = rate[rising].mean(), rate[falling].mean()
    one_way = abs(rate[keep].mean()) / max(np.abs(rate[keep]).mean(), 1e-9)
    speed = np.linalg.norm(c[-1] - c[100], axis=-1).mean() / (t[-1] - t[100])
    return r_up, r_down, one_way, speed


def main():
    rows = ["| brain | run | turning while smell rises (°/s) | while it falls (°/s) "
            "| steering response (fall − rise) | one-way share | net speed (mm/s) |",
            "|---|---|---|---|---|---|---|"]  # fmt: skip
    entries = [(lab, Path(f) / f"{r}.json") for lab, f, r in BRAINS]
    for label, path in entries + [("hand-coded steering", None)]:
        if path is None:
            make = lambda n: GradientSteering()  # noqa: E731
            name = ""
        else:
            run = json.loads(path.read_text())
            brain, x = build_brain(run), np.array(run["x"])
            make = lambda n, b=brain, x=x: BrainController(b, np.repeat(x[None], n, 0))  # noqa: E731
            name = path.stem
        up, down, ow, sp = probe(make)
        rows.append(f"| {label} | {name} | {up:+.1f} | {down:+.1f} | {down - up:+.1f} "
                    f"| {ow:.0%} | {sp:.3f} |")  # fmt: skip
        print(rows[-1], flush=True)
    Path("reports/steering_probe.md").write_text("\n".join(
        ["# Steering probe", "", __doc__.split("\n\n", 2)[2].strip(), "", *rows, ""]))  # fmt: skip


if __name__ == "__main__":
    main()
