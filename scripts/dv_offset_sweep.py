# ruff: noqa: E501
"""Sweep the dorsal/ventral muscle offset on already-trained brains (nothing retrained):
flat-field turning (deg/mm) and net progress for each offset. uv run python scripts/dv_offset_sweep.py
"""

import json, numpy as np
from wormbrain.brain import BrainController
from wormbrain.env import run_episode, mean_curvature, progress_speed
from wormbrain.export import build_brain
from wormbrain.locomotion import FLAT

raws = np.linspace(-2, 2, 17)
H = 4
for folder, n in [
    ("reports/comparison/runs", "real_glu-inhibitory_seed0"),
    ("reports/comparison/runs", "real_glu-inhibitory_seed1"),
    ("reports/comparison/runs", "real_glu-excitatory_seed1"),
    ("reports/patches_long/runs", "real_glu-inhibitory_seed0"),
    ("reports/patches_long/runs", "real_glu-inhibitory_seed1"),
    ("reports/patches_long/runs", "real_glu-excitatory_seed1"),
]:
    r = json.load(open(f"{folder}/{n}.json")) | {"muscle_dv": True}
    b = build_brain(r)
    x = np.array(r["x"])
    X = np.array([np.append(x, raw) for raw in raws for _ in range(H)])
    head = np.zeros((len(X), 2))
    hd = np.tile(np.linspace(0, 2 * np.pi, H, endpoint=False), len(raws))
    ep = run_episode(BrainController(b, X), FLAT, head, hd, duration=90.0, dt=0.02)
    cur = mean_curvature(ep).reshape(len(raws), H).mean(1)
    sp = progress_speed(ep).reshape(len(raws), H).mean(1)
    dv = b.decode(X[::H])["muscle_dv"][:, 0]
    i0 = np.argmin(np.abs(raws))
    ib = np.argmin(cur)
    print(
        f"{folder.split('/')[1]:12s} {n}: offset 0 -> {cur[i0]:.0f} deg/mm (progress {sp[i0]:.3f}); best offset {dv[ib]:+.2f} -> {cur[ib]:.1f} deg/mm (progress {sp[ib]:.3f})",
        flush=True,
    )
    print("    curve:", " ".join(f"{d:+.2f}:{c:.0f}" for d, c in zip(dv, cur)), flush=True)
