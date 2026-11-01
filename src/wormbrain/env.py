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


class PatchField:
    """Scattered food patches that can be smelled only nearby and are eaten up.

    ``n_patches`` Gaussian odour sources (width ``sigma`` mm) are placed at random in a
    square arena of half-width ``half_size`` mm, at least ``min_spacing`` apart. Each
    worm has its own copy of the food: a patch holds ``capacity`` units, a worm whose
    head is within ``eat_radius`` mm eats ``eat_rate`` units per second, and a patch's
    smell fades in proportion to what is left. ``relayout(seed)`` draws a new arena.
    """

    kind = "patches"

    def __init__(self, cfg: dict):
        self.cfg = dict(cfg)
        self.half = cfg.get("half_size", 25.0)
        self.k = cfg.get("n_patches", 16)
        self.sigma = cfg.get("sigma", 1.5)
        self.capacity = cfg.get("capacity", 1.0)
        self.eat_radius = cfg.get("eat_radius", 0.75)
        self.eat_rate = cfg.get("eat_rate", 0.1)
        self.min_spacing = cfg.get("min_spacing", 6.0)
        self.relayout(cfg.get("seed", 0))
        self.reset_worms(1)

    def relayout(self, seed: int) -> None:
        rng = np.random.default_rng(seed)
        xy: list[np.ndarray] = []
        while len(xy) < self.k:
            p = rng.uniform(-self.half, self.half, 2)
            if all(np.linalg.norm(p - q) >= self.min_spacing for q in xy):
                xy.append(p)
        self.xy = np.array(xy)

    def reset_worms(self, n: int) -> None:
        self.left = np.full((n, self.k), self.capacity)  # food left, per worm per patch

    @property
    def center(self) -> np.ndarray:
        return np.zeros(2)

    def move_peak(self, xy, index: int = 0) -> None:
        self.xy[index] = xy

    def conc(self, pos) -> np.ndarray:
        pos = np.asarray(pos, dtype=float)
        d2 = ((pos[..., None, :] - self.xy) ** 2).sum(-1)  # (..., K)
        amp = self.left / self.capacity if pos.ndim == 2 and len(pos) == len(self.left) else 1.0
        return (amp * np.exp(-d2 / (2 * self.sigma**2))).sum(-1)

    def consume(self, head: np.ndarray, dt: float) -> np.ndarray:
        """Worms at a patch eat from it; returns the amount each worm ate this step."""
        near = ((head[:, None, :] - self.xy) ** 2).sum(-1) < self.eat_radius**2
        bite = np.minimum(self.left, self.eat_rate * dt) * near
        self.left -= bite
        return bite.sum(1)

    def starts(self, cfg: dict, n: int, seed: int):
        """Random starts in the middle of the arena, away from every patch."""
        rng = np.random.default_rng(seed + 1)
        lim, clear = cfg.get("half_size", self.half * 0.6), cfg.get("clearance", 4.0)
        head = []
        while len(head) < n:
            p = rng.uniform(-lim, lim, 2)
            if np.min(np.linalg.norm(self.xy - p, axis=1)) >= clear:
                head.append(p)
        return np.array(head), rng.uniform(0, 2 * np.pi, n)


def make_field(cfg: dict):
    return PatchField(cfg) if cfg.get("type") == "patches" else Field(cfg)


def start_positions(cfg: dict, field: Field, n: int, seed: int):
    """Random head positions and headings for ``n`` worms; deterministic per seed.

    In a patch world each seed also draws a new arena layout.
    """
    if getattr(field, "kind", None) == "patches":
        field.relayout(seed)
        return field.starts(cfg, n, seed)
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
    food: np.ndarray | None = None  # (T, 2) position of the (first) food peak over time
    eaten: np.ndarray | None = None  # (T, P) food eaten so far (patch worlds)


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
    food_events: list | None = None,
) -> Episode:
    """``food_events``: [(time, [x, y]), ...] moves the food peak during the episode
    (food patches run out); the field is restored afterwards."""
    body = body or Body()
    events = sorted(food_events or [], key=lambda e: e[0])
    initial_peak = field.center if field.kind not in ("linear", "patches") else None
    if hasattr(field, "reset_worms"):
        field.reset_worms(len(np.atleast_1d(heading)))
    eaten = np.zeros(len(np.atleast_1d(heading)))
    state = body.reset(head, heading)
    n = len(state.theta0)
    controller.reset(n)
    steps = int(round(duration / dt))
    rec = {k: [] for k in ("t", "head", "centroid", "conc", "power", "nodes", "food", "eaten")}
    power_acc = np.zeros(n)

    def record(k):
        rec["t"].append(k * dt)
        rec["head"].append(state.head.copy())
        rec["centroid"].append(body.centroid(state))
        rec["conc"].append(field.conc(state.head))
        rec["power"].append(power_acc / record_every)
        rec["food"].append(field.center)
        rec["eaten"].append(eaten.copy())
        if record_shapes:
            rec["nodes"].append(body.nodes(state))

    record(0)
    for k in range(1, steps + 1):
        while events and (k - 1) * dt >= events[0][0]:
            field.move_peak(events.pop(0)[1])
        obs = {"t": (k - 1) * dt, "conc": field.conc(state.head), "kappa": state.kappa}
        power_acc += body.step(state, controller.step(obs, dt), dt)
        if hasattr(field, "consume"):
            eaten += field.consume(state.head, dt)
        if k % record_every == 0:
            record(k)
            power_acc[:] = 0
    if initial_peak is not None:
        field.move_peak(initial_peak)
    return Episode(
        t=np.array(rec["t"]),
        head=np.array(rec["head"]),
        centroid=np.array(rec["centroid"]),
        conc=np.array(rec["conc"]),
        power=np.array(rec["power"]),
        nodes=np.array(rec["nodes"]) if record_shapes else None,
        food=np.array(rec["food"]),
        eaten=np.array(rec["eaten"]),
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
    elif kind == "food_time" and field.kind != "linear":
        # share of the episode with the head within ``radius`` mm of the (possibly
        # moving) food, i.e. time spent eating; a linear gradient has no food, so it
        # falls back to concentration gain
        dist = np.linalg.norm(ep.head - ep.food[:, None, :], axis=-1)
        r = (dist < cfg.get("radius", 1.0)).mean(0)
    elif kind == "food_time":
        return reward(ep, field, cfg | {"type": "concentration_gain"})
    elif kind == "eaten":
        # patch world: food eaten (units; one patch holds ``capacity``)
        r = ep.eaten[-1].copy()
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
