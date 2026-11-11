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


def gait_fitness(ep, target_speed: float = 0.2) -> np.ndarray:
    """How well each worm matches a real worm's crawl: 1 - |v - target| / target.

    ``v`` is the net speed after the start-up period: straight-line displacement of the
    centroid divided by the time, counted as negative if the worm travels tail-first. A
    worm that circles, wiggles on the spot or races scores low; 1 is a straight head-first
    crawl at ``target_speed`` mm/s (about 0.2 mm/s on agar: wavelength 0.65 body lengths x
    0.30 Hz, Fang-Yen et al. 2010). Speed matching follows Izquierdo & Beer (2018).
    """
    k = np.searchsorted(ep.t, SETTLE)
    net = np.linalg.norm(ep.centroid[-1] - ep.centroid[k], axis=-1) / (ep.t[-1] - ep.t[k])
    step = np.diff(ep.centroid[k:], axis=0)
    axis = (ep.head - ep.centroid)[k:-1]  # points from the body's middle to the head
    headfirst = np.sign((step * axis).sum(-1).sum(0))
    return 1.0 - np.abs(headfirst * net - target_speed) / target_speed


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
    dv_tie: bool = False,
    head_proprio: bool = False,
    food_sense: bool = False,
):
    cfg = load_config("configs/connectome.yaml")
    if glutamate:
        cfg["signs"]["glutamate"] = glutamate
    conn = make_condition(build_connectome(cfg), condition, seed)
    env = load_env_config("configs/env.yaml")
    brain = Brain(conn, BrainConfig(adaptation=adaptation, bounded=bounded, activation=activation,
                                    muscle_dv=muscle_dv, dv_tie=dv_tie,
                                    head_proprio=head_proprio, food_sense=food_sense))  # fmt: skip
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
    muscle_dv: bool = False,
    dv_tie: bool = False,
    head_proprio: bool = False,
    food_sense: bool = False,
    objective: str = "speed",
    target_speed: float = 0.2,
    duration: float = DURATION,
    diagonal: bool = False,
) -> dict:
    """``objective``: "speed" maximises forward speed (the original crawling stage);
    "gait" matches a real worm's net crawling speed (see ``gait_fitness``)."""
    brain, body, cfg = setup(condition, seed, glutamate, adaptation, bounded, activation,
                             muscle_dv, dv_tie, head_proprio, food_sense)  # fmt: skip

    match_gait = objective == "gait"

    def fitness(X):
        n = len(X)
        ep = run_episode(BrainController(brain, X), FLAT, np.zeros((n, 2)), np.zeros(n),
                         duration=duration, body=body, dt=DT)  # fmt: skip
        return gait_fitness(ep, target_speed) if match_gait else forward_speed(ep)

    res = cmaes(fitness, brain.spec.x0(), sigma0=sigma0, popsize=popsize,
                generations=generations, seed=seed, log_path=log_path,
                verbose=verbose, diagonal=diagonal)  # fmt: skip
    _, _, gait = evaluate(brain, body, res["best_x"])
    return {
        "condition": condition,
        "seed": seed,
        "glutamate": cfg["signs"]["glutamate"],
        "adaptation": adaptation,
        "bounded": brain.cfg.bounded,
        "activation": brain.cfg.activation,
        "muscle_dv": brain.cfg.muscle_dv,
        "dv_tie": brain.cfg.dv_tie,
        "head_proprio": brain.cfg.head_proprio,
        "food_sense": brain.cfg.food_sense,
        "objective": objective,
        "target_speed": target_speed,
        "duration": duration,
        "diagonal": diagonal,
        "n_params": brain.n_params,
        "generations": generations,
        "popsize": popsize,
        "sigma0": sigma0,
        **gait,
        "seconds": res["history"][-1]["seconds"],
        "curve": [h["best_so_far"] for h in res["history"]],
        "best_x": res["best_x"].tolist(),
    }
