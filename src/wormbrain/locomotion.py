"""Locomotion task: train a brain to crawl forward on a flat field, and measure the gait.

Used by scripts/locomotion_check.py (one run with figures) and
scripts/locomotion_study.py (conditions x seeds x sign settings).
"""

from __future__ import annotations

import numpy as np

from .brain import Brain, BrainConfig, BrainController
from .connectome import build_connectome, load_config
from .controls import make_condition
from .env import Field, load_env_config, make_body, run_episode
from .train import cmaes

FLAT = Field({"type": "linear", "slope": 0.0, "offset": 1.0})
DURATION, SETTLE, DT = 30.0, 5.0, 0.01


def forward_speed(ep) -> np.ndarray:
    """Mean speed along the starting heading (+x) after the start-up period."""
    k = np.searchsorted(ep.t, SETTLE)
    return (ep.centroid[-1, :, 0] - ep.centroid[k, :, 0]) / (ep.t[-1] - ep.t[k])


def wave_lag(kappa: np.ndarray, dt: float = DT) -> float:
    """Lag (s) of tail curvature behind head curvature; > 0 means a head-to-tail wave.

    ``kappa`` is (T, joints) for one worm. Searches lags up to +-2 s.
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


def setup(condition: str, seed: int, glutamate: str | None = None, adaptation: bool = True):
    cfg = load_config("configs/connectome.yaml")
    if glutamate:
        cfg["signs"]["glutamate"] = glutamate
    conn = make_condition(build_connectome(cfg), condition, seed)
    env = load_env_config("configs/env.yaml")
    return Brain(conn, BrainConfig(adaptation=adaptation)), make_body(env["body"]), cfg


def evaluate(brain, body, x, record_shapes: bool = False):
    """Run one worm with parameters ``x``; returns the episode and gait measures."""
    rec = KappaRecorder(BrainController(brain, x, record_every=10))
    ep = run_episode(rec, FLAT, np.zeros((1, 2)), np.zeros(1), duration=DURATION, body=body,
                     dt=DT, record_shapes=record_shapes)  # fmt: skip
    kappa = np.array(rec.kappa)[:, 0]
    k = int(SETTLE / DT)
    gait = {
        "forward_speed_mm_s": float(forward_speed(ep)[0]),
        "wave_lag_s": wave_lag(kappa[k:]),
        "curvature_rms": float(np.sqrt((kappa[k:] ** 2).mean())),
        # how much the curvature changes over time; ~0 for a frozen posture
        "curvature_temporal_sd": float(kappa[k:].std(0).mean()),
        "max_abs_v": float(np.abs(np.array(rec.inner.activity)).max()),
    }
    return ep, kappa, gait


def train_locomotion(
    condition: str = "real",
    seed: int = 0,
    glutamate: str | None = None,
    adaptation: bool = True,
    generations: int = 100,
    popsize: int = 24,
    sigma0: float = 0.5,
    log_path=None,
    verbose: bool = False,
) -> dict:
    brain, body, cfg = setup(condition, seed, glutamate, adaptation)

    def objective(X):
        n = len(X)
        ep = run_episode(BrainController(brain, X), FLAT, np.zeros((n, 2)), np.zeros(n),
                         duration=DURATION, body=body, dt=DT)  # fmt: skip
        return forward_speed(ep)

    res = cmaes(objective, brain.spec.x0(), sigma0=sigma0, popsize=popsize,
                generations=generations, seed=seed, log_path=log_path,
                verbose=verbose)  # fmt: skip
    _, _, gait = evaluate(brain, body, res["best_x"])
    return {
        "condition": condition,
        "seed": seed,
        "glutamate": cfg["signs"]["glutamate"],
        "adaptation": adaptation,
        "n_params": brain.n_params,
        "generations": generations,
        "popsize": popsize,
        "sigma0": sigma0,
        **gait,
        "seconds": res["history"][-1]["seconds"],
        "curve": [h["best_so_far"] for h in res["history"]],
        "best_x": res["best_x"].tolist(),
    }
