"""Arena with a chemical gradient, episodes, and the chemotaxis reward.

Fields (``field.type`` in the config):

- ``gaussian``: one peak, ``peak: [x, y]``, ``sigma``, ``amplitude``
- ``peaks``: several Gaussian peaks, ``peaks: [{xy, sigma, amplitude}, ...]``
- ``linear``: ``slope`` per mm along ``direction_deg``, plus ``offset``

The arena is an open plane (no walls). Each episode places every worm at a random
distance from ``start.center`` (default: the first peak, or the origin) facing a
random direction, straight-bodied. Everything random comes from the episode seed.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import yaml

from .body import Body, BodyParams


class Field:
    """Concentration c(x, y) and its gradient, for (..., 2) positions."""

    def __init__(self, cfg: dict):
        self.cfg = dict(cfg)
        self.kind = cfg.get("type", "gaussian")
        if self.kind == "gaussian":
            peaks = [{"xy": cfg.get("peak", [0, 0]), **cfg}]
        elif self.kind == "peaks":
            peaks = cfg["peaks"]
        elif self.kind == "linear":
            a = np.deg2rad(cfg.get("direction_deg", 0.0))
            self.slope = cfg.get("slope", 0.1) * np.array([np.cos(a), np.sin(a)])
            self.offset = cfg.get("offset", 0.0)
            return
        else:
            raise ValueError(f"unknown field type {self.kind!r}")
        self.xy = np.array([p["xy"] for p in peaks], dtype=float)
        self.sigma = np.array([p.get("sigma", 4.0) for p in peaks], dtype=float)
        self.amp = np.array([p.get("amplitude", 1.0) for p in peaks], dtype=float)

    @property
    def center(self) -> np.ndarray:
        return self.xy[0].copy() if self.kind != "linear" else np.zeros(2)

    def move_peak(self, xy, index: int = 0) -> None:
        self.xy[index] = xy

    def _terms(self, pos):
        d = np.asarray(pos, dtype=float)[..., None, :] - self.xy  # (..., K, 2)
        g = self.amp * np.exp(-(d**2).sum(-1) / (2 * self.sigma**2))  # (..., K)
        return d, g

    def conc(self, pos) -> np.ndarray:
        if self.kind == "linear":
            return np.asarray(pos, dtype=float) @ self.slope + self.offset
        return self._terms(pos)[1].sum(-1)

    def grad(self, pos) -> np.ndarray:
        if self.kind == "linear":
            return np.broadcast_to(self.slope, np.shape(pos)).copy()
        d, g = self._terms(pos)
        return -(g[..., None] * d / self.sigma[:, None] ** 2).sum(-2)


def start_positions(cfg: dict, field: Field, n: int, seed: int):
    """Random head positions and headings for ``n`` worms; deterministic per seed."""
    rng = np.random.default_rng(seed)
    center = np.asarray(cfg.get("center", field.center), dtype=float)
    lo, hi = cfg.get("distance", [4.0, 6.0])
    r = rng.uniform(lo, hi, n)
    a = rng.uniform(0, 2 * np.pi, n)
    head = center + r[:, None] * np.stack([np.cos(a), np.sin(a)], axis=1)
    heading = rng.uniform(0, 2 * np.pi, n)
    return head, heading


@dataclass
class Episode:
    t: np.ndarray  # (T,) recorded times
    head: np.ndarray  # (T, P, 2)
    centroid: np.ndarray  # (T, P, 2)
    conc: np.ndarray  # (T, P) concentration at the head
    power: np.ndarray  # (T, P) mean dissipated power since the previous record
    nodes: np.ndarray | None  # (T, P, n + 1, 2) body shapes, if recorded


def run_episode(
    controller,
    field: Field,
    head,
    heading,
    duration: float = 120.0,
    dt: float = 0.01,
    body: Body | None = None,
    record_every: int = 10,
    record_shapes: bool = False,
) -> Episode:
    body = body or Body()
    state = body.reset(head, heading)
    n = len(state.theta0)
    controller.reset(n)
    steps = int(round(duration / dt))
    rec = {k: [] for k in ("t", "head", "centroid", "conc", "power", "nodes")}
    power_acc = np.zeros(n)

    def record(k):
        rec["t"].append(k * dt)
        rec["head"].append(state.head.copy())
        rec["centroid"].append(body.centroid(state))
        rec["conc"].append(field.conc(state.head))
        rec["power"].append(power_acc / record_every)
        if record_shapes:
            rec["nodes"].append(body.nodes(state))

    record(0)
    for k in range(1, steps + 1):
        obs = {"t": (k - 1) * dt, "conc": field.conc(state.head), "kappa": state.kappa}
        power_acc += body.step(state, controller.step(obs, dt), dt)
        if k % record_every == 0:
            record(k)
            power_acc[:] = 0
    return Episode(
        t=np.array(rec["t"]),
        head=np.array(rec["head"]),
        centroid=np.array(rec["centroid"]),
        conc=np.array(rec["conc"]),
        power=np.array(rec["power"]),
        nodes=np.array(rec["nodes"]) if record_shapes else None,
    )


def reward(ep: Episode, field: Field, cfg: dict | None = None) -> np.ndarray:
    """Per-worm reward (P,).

    ``concentration_gain`` (default): mean head concentration over the last
    ``final_fraction`` of the episode minus the starting concentration, divided by
    the field's peak amplitude. ``final_distance``: minus the final centroid
    distance to the first peak, in mm. Both subtract ``energy_weight`` times the
    mean dissipated power, and ``idle_penalty * max(0, 1 - speed / min_speed)``
    where speed is the centroid's mean path speed: real worms keep crawling during
    chemotaxis, and without this term stopping dead beats crawling before steering
    has been learned (blind crawling loses concentration on average).
    """
    cfg = cfg or {}
    kind = cfg.get("type", "concentration_gain")
    if kind == "concentration_gain":
        tail = max(1, int(round(len(ep.t) * cfg.get("final_fraction", 0.1))))
        scale = field.amp.max() if field.kind != "linear" else 1.0
        r = (ep.conc[-tail:].mean(0) - ep.conc[0]) / scale
    elif kind == "final_distance":
        r = -np.linalg.norm(ep.centroid[-1] - field.center, axis=-1)
    else:
        raise ValueError(f"unknown reward type {kind!r}")
    r = r - cfg.get("energy_weight", 0.0) * ep.power[1:].mean(0)
    if cfg.get("idle_penalty", 0.0):
        # "path": centroid path length (jitter included); "progress": net displacement
        # over 5 s windows, so wiggling on the spot does not count as moving
        speed = progress_speed(ep) if cfg.get("speed_measure") == "progress" else path_speed(ep)
        r = r - cfg["idle_penalty"] * np.maximum(0.0, 1.0 - speed / cfg["min_speed"])
    return r


def progress_speed(ep: Episode, window: float = 5.0) -> np.ndarray:
    """Mean net speed (mm/s): centroid displacement over ``window`` s, averaged over time."""
    k = max(1, int(round(window / (ep.t[1] - ep.t[0]))))
    d = np.linalg.norm(ep.centroid[k:] - ep.centroid[:-k], axis=-1)
    return d.mean(0) / (k * (ep.t[1] - ep.t[0]))


def path_speed(ep: Episode) -> np.ndarray:
    """Mean speed of the centroid along its path (mm/s), per worm."""
    length = np.linalg.norm(np.diff(ep.centroid, axis=0), axis=-1).sum(0)
    return length / (ep.t[-1] - ep.t[0])


def make_body(cfg: dict | None) -> Body:
    return Body(BodyParams(**(cfg or {})))


def load_env_config(*paths) -> dict:
    """Merge env configs left to right; ``field`` is replaced whole, other sections merged."""
    cfg: dict = {}
    for path in paths:
        for key, value in (yaml.safe_load(Path(path).read_text()) or {}).items():
            if key != "field" and isinstance(value, dict):
                cfg[key] = {**cfg.get(key, {}), **value}
            else:
                cfg[key] = value
    return cfg


def mean_turning_rate(ep: Episode, window: float = 2.0, settle: float = 10.0) -> np.ndarray:
    """Mean signed turning rate (deg/s, + = counter-clockwise) of each worm's path.

    The travel direction is the centroid's displacement over ``window`` seconds;
    the first ``settle`` seconds are skipped. A worm crawling in a fixed circle
    turns at a steady nonzero rate; one crawling straight (even if it wiggles)
    scores about 0.
    """
    rec_dt = ep.t[1] - ep.t[0]
    k = max(1, int(round(window / rec_dt)))
    d = ep.centroid[k:] - ep.centroid[:-k]
    ang = np.unwrap(np.arctan2(d[..., 1], d[..., 0]), axis=0)
    s = min(len(ang) - 2, int(round(settle / rec_dt)))
    return np.rad2deg(ang[-1] - ang[s]) / ((len(ang) - 1 - s) * rec_dt)


def mean_curvature(ep: Episode, min_speed: float = 0.02) -> np.ndarray:
    """|Mean turning| per mm of net progress (deg/mm); a circle of radius r gives 57.3 / r.

    Unlike turning per second, this cannot be lowered by crawling slowly. The speed
    is floored at ``min_speed`` so a worm that barely moves scores high, not infinite.
    """
    return np.abs(mean_turning_rate(ep)) / np.maximum(progress_speed(ep), min_speed)
