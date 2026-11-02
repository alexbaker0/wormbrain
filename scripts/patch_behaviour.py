"""How trained brains move in patch world v2 (wrap-around, 12-minute lives, slow eating).

    uv run python scripts/patch_behaviour.py reports/patches_dv [more report folders]

For each trained run in <folder>/runs (and hand-coded baselines): food eaten, speed on
and far from food, time on food, turning far from and near food (deg/mm, measured over
2 s windows) and its one-way share (100% = circling, near 0 = weaving). Writes
<folder>/behaviour.md and <folder>/paths.png (6 worm paths per mover, test layout).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from wormbrain.brain import BrainController  # noqa: E402
from wormbrain.controllers import GradientSteering, TravelingWave  # noqa: E402
from wormbrain.env import PatchField, run_episode  # noqa: E402
from wormbrain.export import build_brain  # noqa: E402

WORLD = {"half_size": 25.0, "n_patches": 24, "sigma": 1.5, "eat_radius": 1.0,
         "eat_rate": 0.03, "min_spacing": 6.0, "periodic": True}  # fmt: skip
N, DURATION = 16, 720.0


def measure(make, field, head0, heading0):
    ep = run_episode(make(), field, head0, heading0, duration=DURATION, dt=0.02)
    c, dt = ep.centroid, ep.t[1] - ep.t[0]
    dist = np.min(np.linalg.norm(field._wrap(ep.head[:, :, None] - field.xy), axis=-1), -1)
    speed = np.linalg.norm(np.diff(c, axis=0), axis=-1) / dt
    k = 10  # 2 s windows at 0.2 s per record
    d = c[k:] - c[:-k]
    turn = np.diff(np.unwrap(np.arctan2(d[..., 1], d[..., 0]), axis=0), axis=0)
    step = np.linalg.norm(np.diff(c[k:], axis=0), axis=-1)
    dd = dist[k + 1 :]

    def per_mm(m):
        return np.rad2deg(np.abs(turn[m]).sum()) / max(step[m].sum(), 1e-9)

    def one_way(m):
        total = np.abs(turn[m]).sum()
        return sum(abs(turn[:, w][m[:, w]].sum()) for w in range(N)) / max(total, 1e-9)

    on, far = dist[1:] < 1.0, dist[1:] > 4.0
    return ep, {
        "eaten": float(ep.eaten[-1].mean()),
        "speed_on": float(speed[on].mean()) if on.any() else float("nan"),
        "speed_far": float(speed[far].mean()),
        "time_on": float(on.mean()),
        "turn_far": per_mm(dd > 4.0),
        "one_way_far": one_way(dd > 4.0),
        "turn_near": per_mm(dd < 3.0),
    }


def main(folders):
    field = PatchField(WORLD)
    field.relayout(9999)
    head0, heading0 = field.starts({"half_size": 15.0, "clearance": 4.0}, N, 9999)
    for folder in map(Path, folders):
        movers = []
        for path in sorted((folder / "runs").glob("*.json")):
            run = json.loads(path.read_text())
            brain, x = build_brain(run), np.array(run["x"])
            movers.append(
                (path.stem, lambda b=brain, x=x: BrainController(b, np.repeat(x[None], N, 0)))
            )
        movers += [("hand-coded steering", GradientSteering), ("blind straight", TravelingWave)]
        rows = ["| mover | food eaten (12 min) | speed on food (mm/s) | speed far from food "
                "| time on food | turning far from food, °/mm (one-way share) "
                "| turning near food, °/mm |", "|---|---|---|---|---|---|---|"]  # fmt: skip
        fig, axes = plt.subplots(1, len(movers), figsize=(4 * len(movers), 4.4), squeeze=False)
        for ax, (name, make) in zip(axes[0], movers, strict=True):
            ep, m = measure(make, field, head0, heading0)
            rows.append(f"| {name} | {m['eaten']:.2f} | {m['speed_on']:.3f} | {m['speed_far']:.3f} "
                        f"| {m['time_on']:.0%} | {m['turn_far']:.0f} ({m['one_way_far']:.0%}) "
                        f"| {m['turn_near']:.0f} |")  # fmt: skip
            for x, y in field.xy:
                for ox in (-50, 0, 50):
                    for oy in (-50, 0, 50):
                        ax.add_patch(plt.Circle((x + ox, y + oy), 1.5, color="g", alpha=0.3))
            for w in range(6):
                ax.plot(*ep.centroid[:, w].T, lw=0.7)
            ax.set_title(f"{name}: eaten {m['eaten']:.2f}", fontsize=8)
            ax.set_aspect("equal")
            ax.set_xlim(-40, 40)
            ax.set_ylim(-40, 40)
            print(rows[-1], flush=True)
        fig.tight_layout()
        fig.savefig(folder / "paths.png", dpi=90)
        (folder / "behaviour.md").write_text("\n".join(rows) + "\n")


if __name__ == "__main__":
    main(sys.argv[1:])
