"""Milestone 4 go/no-go: can the fixed connectome learn to crawl forward at all?

    uv run python scripts/locomotion_check.py [--generations 150] [--condition real]

Trains only the brain's few hundred parameters (CMA-ES) to maximise forward speed
on a flat field, then measures speed and whether the body carries a head-to-tail
bending wave. Writes reports/locomotion/<condition>_seed<seed>.{json,png}.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from wormbrain.brain import Brain, BrainController  # noqa: E402
from wormbrain.connectome import build_connectome, load_config  # noqa: E402
from wormbrain.controls import make_condition  # noqa: E402
from wormbrain.env import Field, load_env_config, make_body, run_episode  # noqa: E402
from wormbrain.train import cmaes  # noqa: E402

OUT = Path("reports/locomotion")
FLAT = Field({"type": "linear", "slope": 0.0, "offset": 1.0})
DURATION, SETTLE = 30.0, 5.0


def forward_speed(ep) -> np.ndarray:
    """Mean speed along the starting heading (+x) after the start-up period."""
    k = np.searchsorted(ep.t, SETTLE)
    return (ep.centroid[-1, :, 0] - ep.centroid[k, :, 0]) / (ep.t[-1] - ep.t[k])


def wave_direction(kappa: np.ndarray, dt: float) -> float:
    """Lag (s) of tail curvature behind head curvature; > 0 means a head-to-tail wave.

    ``kappa`` is (T, joints) for one worm.
    """
    head, tail = kappa[:, 2] - kappa[:, 2].mean(), kappa[:, -3] - kappa[:, -3].mean()
    n, m = len(head), int(2.0 / dt)
    lags = np.arange(-m, m + 1)
    # corr(k) = sum_t head[t] * tail[t + k]
    corr = [
        np.dot(head[max(0, -k) : n - max(0, k)], tail[max(0, k) : n - max(0, -k)]) for k in lags
    ]
    return float(lags[int(np.argmax(corr))] * dt)


class KappaRecorder:
    """Wraps a controller and keeps the body curvature it observes."""

    def __init__(self, inner):
        self.inner, self.kappa = inner, []

    def reset(self, n):
        self.inner.reset(n)
        self.kappa = []

    def step(self, obs, dt):
        self.kappa.append(obs["kappa"].copy())
        return self.inner.step(obs, dt)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--condition", default="real")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--generations", type=int, default=150)
    p.add_argument("--popsize", type=int, default=24)
    p.add_argument("--sigma0", type=float, default=0.5)
    p.add_argument("--glutamate", default=None, help="override signs.glutamate")
    p.add_argument("--tag", default="", help="suffix for output names")
    args = p.parse_args()

    env = load_env_config("configs/env.yaml")
    body = make_body(env["body"])
    cfg = load_config("configs/connectome.yaml")
    if args.glutamate:
        cfg["signs"]["glutamate"] = args.glutamate
    conn = make_condition(build_connectome(cfg), args.condition, args.seed)
    brain = Brain(conn)

    def objective(X):
        ctrl = BrainController(brain, X)
        n = len(X)
        ep = run_episode(ctrl, FLAT, np.zeros((n, 2)), np.zeros(n), duration=DURATION, body=body)
        return forward_speed(ep)

    OUT.mkdir(parents=True, exist_ok=True)
    stem = OUT / f"{args.condition}_seed{args.seed}{args.tag}"
    res = cmaes(objective, brain.spec.x0(), sigma0=args.sigma0, popsize=args.popsize,
                generations=args.generations, seed=args.seed,
                log_path=stem.with_suffix(".log.json"))  # fmt: skip

    rec = KappaRecorder(BrainController(brain, res["best_x"], record_every=10))
    ep = run_episode(rec, FLAT, np.zeros((1, 2)), np.zeros(1), duration=DURATION, body=body,
                     record_shapes=True)  # fmt: skip
    kappa = np.array(rec.kappa)[:, 0]
    k = int(SETTLE / 0.01)
    summary = {
        "condition": args.condition,
        "seed": args.seed,
        "n_params": brain.n_params,
        "generations": args.generations,
        "popsize": args.popsize,
        "sigma0": args.sigma0,
        "glutamate": cfg["signs"]["glutamate"],
        "forward_speed_mm_s": float(forward_speed(ep)[0]),
        "wave_lag_s": wave_direction(kappa[k:], 0.01),
        "curvature_rms": float(np.sqrt((kappa[k:] ** 2).mean())),
        "max_abs_v": float(np.abs(np.array(rec.inner.activity)).max()),
        "seconds": res["history"][-1]["seconds"],
    }
    stem.with_suffix(".json").write_text(json.dumps(summary | {"best_x": res["best_x"].tolist()}))
    np.save(stem.with_suffix(".npy"), res["best_x"])

    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    h = res["history"]
    axes[0].plot([r["evaluations"] for r in h], [r["best"] for r in h], label="best")
    axes[0].plot([r["evaluations"] for r in h], [r["mean"] for r in h], label="mean")
    axes[0].axhline(0.175, color="k", ls=":", label="hand-coded wave")
    axes[0].set_xlabel("evaluations")
    axes[0].set_ylabel("forward speed (mm/s)")
    axes[0].legend(frameon=False)
    t = np.arange(len(kappa)) * 0.01
    axes[1].imshow(kappa.T, aspect="auto", cmap="RdBu_r", extent=[0, t[-1], kappa.shape[1], 0])
    axes[1].set_xlabel("time (s)")
    axes[1].set_ylabel("joint (head at top)")
    axes[1].set_title("body curvature (red dorsal)")
    for i in range(0, len(ep.t), 20):
        axes[2].plot(*ep.nodes[i, 0].T, color="C0", alpha=0.4)
    axes[2].plot(*ep.centroid[:, 0].T, color="k", lw=1)
    axes[2].set_aspect("equal")
    axes[2].set_title(f"{args.condition}: {summary['forward_speed_mm_s']:.3f} mm/s")
    fig.tight_layout()
    fig.savefig(stem.with_suffix(".png"), dpi=110)
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
