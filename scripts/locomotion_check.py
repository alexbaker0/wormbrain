"""One locomotion training run with figures (milestone 4 go/no-go).

    uv run python scripts/locomotion_check.py [--condition real] [--generations 100]

Trains only the brain parameters (CMA-ES) to maximise forward speed on a flat
field, then shows the learning curve, body curvature over time and the path.
Writes reports/locomotion/<condition>_seed<seed><tag>.{json,png}.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from wormbrain.locomotion import DT, evaluate, setup, train_locomotion  # noqa: E402

OUT = Path("reports/locomotion")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--condition", default="real")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--generations", type=int, default=100)
    p.add_argument("--popsize", type=int, default=24)
    p.add_argument("--sigma0", type=float, default=0.5)
    p.add_argument("--glutamate", default=None, help="override signs.glutamate")
    p.add_argument("--no-adaptation", action="store_true")
    p.add_argument("--tag", default="", help="suffix for output names")
    args = p.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    stem = OUT / f"{args.condition}_seed{args.seed}{args.tag}"
    res = train_locomotion(args.condition, args.seed, args.glutamate, not args.no_adaptation,
                           args.generations, args.popsize, args.sigma0,
                           log_path=stem.with_suffix(".log.json"), verbose=True)  # fmt: skip
    stem.with_suffix(".json").write_text(json.dumps(res))

    brain, body, _ = setup(args.condition, args.seed, args.glutamate, not args.no_adaptation)
    ep, kappa, gait = evaluate(brain, body, np.array(res["best_x"]), record_shapes=True)
    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    curve = res["curve"]
    axes[0].plot(np.arange(1, len(curve) + 1) * args.popsize, curve, label="best so far")
    axes[0].axhline(0.175, color="k", ls=":", label="hand-coded wave")
    axes[0].set_xlabel("evaluations")
    axes[0].set_ylabel("forward speed (mm/s)")
    axes[0].legend(frameon=False)
    t_end = len(kappa) * DT
    axes[1].imshow(kappa.T, aspect="auto", cmap="RdBu_r", extent=[0, t_end, kappa.shape[1], 0])
    axes[1].set_xlabel("time (s)")
    axes[1].set_ylabel("joint (head at top)")
    axes[1].set_title("body curvature (red dorsal)")
    for i in range(0, len(ep.t), 20):
        axes[2].plot(*ep.nodes[i, 0].T, color="C0", alpha=0.4)
    axes[2].plot(*ep.centroid[:, 0].T, color="k", lw=1)
    axes[2].set_aspect("equal")
    axes[2].set_title(f"{args.condition}: {gait['forward_speed_mm_s']:.3f} mm/s")
    fig.tight_layout()
    fig.savefig(stem.with_suffix(".png"), dpi=110)
    print(json.dumps({k: v for k, v in res.items() if k not in ("best_x", "curve")}, indent=1))


if __name__ == "__main__":
    main()
