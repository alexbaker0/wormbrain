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


def wave_direction(kappa: np.ndarray) -> float:
    """How much of the bending travels head-to-tail, in [-1, 1].

    ``kappa`` is (T, joints) for one worm, joint 0 at the head. A bend travelling
    head-to-tail, exp(i(w t - k s)), puts its power where numpy's FFT frequencies
    (time, space) have opposite signs; tail-to-head, the same sign. Returns
    (head-to-tail - tail-to-head) / total; ~0 for a standing or frozen posture.
    """
    k = kappa - kappa.mean(0)
    power = np.abs(np.fft.fft2(k)) ** 2  # axes: time frequency, space frequency
    ft = np.fft.fftfreq(k.shape[0])[:, None]
    fs = np.fft.fftfreq(k.shape[1])[None, :]
    backward, forward = power[(ft * fs) > 0].sum(), power[(ft * fs) < 0].sum()
    total = forward + backward
    return float((forward - backward) / total) if total > 0 else 0.0


def undulation_frequency(kappa: np.ndarray, dt: float = DT) -> float:
    """Dominant temporal frequency (Hz) of the curvature, averaged over the body."""
    k = kappa - kappa.mean(0)
    spec = (np.abs(np.fft.rfft(k, axis=0)) ** 2).sum(1)
    f = np.fft.rfftfreq(len(k), dt)
    return float(f[1:][spec[1:].argmax()])


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


def setup(
    condition: str,
    seed: int,
    glutamate: str | None = None,
    adaptation: bool = True,
    bounded: bool = True,
    activation: str = "tanh",
    muscle_dv: bool = False,
):
    cfg = load_config("configs/connectome.yaml")
    if glutamate:
        cfg["signs"]["glutamate"] = glutamate
    conn = make_condition(build_connectome(cfg), condition, seed)
    env = load_env_config("configs/env.yaml")
    brain = Brain(conn, BrainConfig(adaptation=adaptation, bounded=bounded, activation=activation,
                                    muscle_dv=muscle_dv))  # fmt: skip
    return brain, make_body(env["body"]), cfg


def evaluate(brain, body, x, record_shapes: bool = False):
    """Run one worm with parameters ``x``; returns the episode and gait measures."""
    rec = KappaRecorder(BrainController(brain, x, record_every=10))
    ep = run_episode(rec, FLAT, np.zeros((1, 2)), np.zeros(1), duration=DURATION, body=body,
                     dt=DT, record_shapes=record_shapes)  # fmt: skip
    kappa = np.array(rec.kappa)[:, 0]
    k = int(SETTLE / DT)
    gait = {
        "forward_speed_mm_s": float(forward_speed(ep)[0]),
        "wave_direction": wave_direction(kappa[k:]),
        "undulation_hz": undulation_frequency(kappa[k:]),
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
    bounded: bool = True,
    activation: str = "tanh",
) -> dict:
    brain, body, cfg = setup(condition, seed, glutamate, adaptation, bounded, activation)

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
        "bounded": brain.cfg.bounded,
        "activation": brain.cfg.activation,
        "n_params": brain.n_params,
        "generations": generations,
        "popsize": popsize,
        "sigma0": sigma0,
        **gait,
        "seconds": res["history"][-1]["seconds"],
        "curve": [h["best_so_far"] for h in res["history"]],
        "best_x": res["best_x"].tolist(),
    }
