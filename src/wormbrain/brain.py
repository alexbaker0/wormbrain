"""Graded (non-spiking) connectome brain driving the body.

One leaky-integrator unit per neuron:

    tau_i dv_i/dt = -v_i + g_chem * sum_j W_ji phi_j(v_j)
                         + g_gap * sum_j M_ji (v_j - v_i) + b_i + input_i
    phi_j(v) = sigmoid(gain_j * v)          (transmitter release, in [0, 1])

``W`` is the chemical wiring with signs, each neuron's inputs divided by its total
incoming synapse weight; ``M`` is the gap-junction wiring, normalised the same way.
Normalising per neuron keeps every neuron's input on the same scale whatever its
connectivity, in the real graph and in every control. Lesions are applied after
normalisation, so a silenced neuron simply stops contributing.

Integration is semi-implicit Euler: the leak and gap-junction self-terms are
implicit, everything else explicit. Because inputs are normalised and sigmoids are
bounded, the update is a contraction for any step size and ``v`` stays bounded;
``check_finite`` guards against anything else.

Fixed: which neurons connect, the weights and signs, the neuron->muscle synapses.
Trained (``ParamSpec``): per neuron class tau, bias and gain; global g_chem, g_gap;
salt sensor gains and adaptation time; proprioceptive gain; muscle gain and bias.

Inputs
------
- ASEL is an ON cell and ASER an OFF cell for salt (Suzuki et al. 2008, Nature
  454:114): each sees the rectified relative change of concentration at the nose
  against a running average over ``tau_adapt`` (transient, as observed).
- B-class motor neurons (VB, DB) sense body curvature (Wen et al. 2012, Neuron
  76:750): each gets the dorsal (DB) or ventral (VB) curvature a short distance
  anterior to its own position, which is taken from its neuromuscular synapses.

Output: each body-wall muscle sums its neuromuscular inputs (signed by the
presynaptic neuron's transmitter, so GABAergic DD/VD relax muscle), normalised, and
activation = sigmoid(muscle_gain * drive + muscle_bias).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .body import MUSCLE_ROWS, QUADRANTS, BodyParams
from .connectome import Connectome


@dataclass(frozen=True)
class BrainConfig:
    tau_range: tuple[float, float] = (0.05, 2.0)  # s
    per_class: bool = True  # tie tau/bias/gain across a neuron class; False: per neuron
    salt_on: tuple[str, ...] = ("ASEL",)
    salt_off: tuple[str, ...] = ("ASER",)
    conc_ref: float = 0.05  # relative change = (c - c_avg) / (conc_ref + |c_avg|)
    proprio_classes: tuple[str, ...] = ("VB", "DB")
    proprio_offset: float = 0.1  # body lengths anterior to the neuron
    lesion: tuple[str, ...] = ()
    init: dict = field(default_factory=dict)  # overrides of ParamSpec defaults


def _sigmoid(x):
    return 0.5 * (1.0 + np.tanh(0.5 * x))


def _normalise_columns(w):
    total = np.abs(w).sum(0, keepdims=True)
    return np.divide(w, total, out=np.zeros_like(w, dtype=float), where=total > 0)


class ParamSpec:
    """Layout of the flat parameter vector the optimiser sees."""

    def __init__(self, n_groups: int, init: dict):
        # name: (size, initial raw value); transforms are in Brain.decode
        self.blocks = {
            "tau": (n_groups, 0.0),
            "bias": (n_groups, 0.0),
            "gain": (n_groups, 0.0),
            "g_chem": (1, 0.0),
            "g_gap": (1, np.log(0.5)),
            "salt_gain": (2, np.log(20.0)),
            "tau_adapt": (1, 0.0),
            "proprio_gain": (1, 0.0),
            "muscle_gain": (1, np.log(4.0)),
            "muscle_bias": (1, 0.0),
        }
        self.blocks = {k: (n, init.get(k, v)) for k, (n, v) in self.blocks.items()}
        self.slices, start = {}, 0
        for k, (n, _) in self.blocks.items():
            self.slices[k] = slice(start, start + n)
            start += n
        self.size = start

    def x0(self) -> np.ndarray:
        x = np.empty(self.size)
        for k, (_, v) in self.blocks.items():
            x[self.slices[k]] = v
        return x

    def unpack(self, x: np.ndarray) -> dict:
        x = np.atleast_2d(x)
        return {k: x[:, s] for k, s in self.slices.items()}


class Brain:
    def __init__(self, conn: Connectome, cfg: BrainConfig | None = None, body=None):
        self.conn = conn
        self.cfg = cfg = cfg or BrainConfig()
        body = body or BodyParams()
        n = conn.n
        self.n = n
        if cfg.per_class:
            classes = conn.classes()
            self.group = np.array([classes.index(c) for c in conn.cell_class])
        else:
            self.group = np.arange(n)
        self.spec = ParamSpec(int(self.group.max()) + 1, cfg.init)

        alive = np.ones(n)
        alive[conn.index(list(cfg.lesion))] = 0.0
        self.alive = alive
        self.W = _normalise_columns(conn.chem * conn.chem_sign) * alive[:, None]
        self.M = _normalise_columns(conn.gap) * alive[:, None] * alive[None, :]
        self.gap_self = self.M.sum(0)  # each neuron's coupling to itself, implicit

        # salt sensors
        self.on_idx = conn.index(list(cfg.salt_on))
        self.off_idx = conn.index(list(cfg.salt_off))

        # neuron -> muscle readout, into the body's (4, 24) layout
        slot = np.array(
            [QUADRANTS.index(q) * MUSCLE_ROWS + r - 1
             for q, r in zip(conn.muscle_quadrant, conn.muscle_row, strict=True)]
        )  # fmt: skip
        R = np.zeros((n, 4 * MUSCLE_ROWS))
        R[:, slot] = _normalise_columns(conn.nmj * conn.node_sign[:, None])
        # muscles missing from the data (MVL24) copy their left/right partner
        for s in sorted(set(range(4 * MUSCLE_ROWS)) - set(slot)):
            q, r = divmod(s, MUSCLE_ROWS)
            partner = QUADRANTS.index(QUADRANTS[q][0] + ("R" if QUADRANTS[q][1] == "L" else "L"))
            R[:, s] = R[:, partner * MUSCLE_ROWS + r]
        self.R = R * alive[:, None]

        # proprioception: B-class neuron position from its neuromuscular synapses
        prop = [k for k, c in enumerate(conn.cell_class) if c in cfg.proprio_classes]
        prop = [k for k in prop if conn.nmj[k].sum() > 0]
        self.prop_idx = np.array(prop, dtype=int)
        row_pos = (conn.muscle_row - 0.5) / MUSCLE_ROWS  # fraction of body length
        pos = np.array([conn.nmj[k] @ row_pos / conn.nmj[k].sum() for k in prop])
        self.prop_pos = pos
        side = np.array([1.0 if conn.cell_class[k].startswith("D") else -1.0 for k in prop])
        self.prop_side = side  # dorsal neurons see +curvature, ventral ones -curvature
        joints = np.arange(1, body.n_segments) / body.n_segments
        sense = np.clip(pos - cfg.proprio_offset, joints[0], joints[-1])
        eye = np.eye(len(joints))
        self.joints_to_prop = np.stack([np.interp(sense, joints, e) for e in eye], axis=1)
        self.kappa_max = body.kappa_max

    @property
    def n_params(self) -> int:
        return self.spec.size

    def decode(self, x: np.ndarray) -> dict:
        """Raw parameter vectors (P, D) -> physical parameters, per neuron where relevant."""
        p = self.spec.unpack(x)
        lo, hi = self.cfg.tau_range
        return {
            "tau": (lo + (hi - lo) * _sigmoid(p["tau"]))[:, self.group],
            "bias": p["bias"][:, self.group],
            "gain": np.exp(p["gain"])[:, self.group],
            "g_chem": np.exp(p["g_chem"]),
            "g_gap": np.exp(p["g_gap"]),
            "salt_on": np.exp(p["salt_gain"][:, :1]),
            "salt_off": np.exp(p["salt_gain"][:, 1:]),
            "tau_adapt": 0.5 + 9.5 * _sigmoid(p["tau_adapt"]),
            "proprio_gain": p["proprio_gain"],
            "muscle_gain": np.exp(p["muscle_gain"]),
            "muscle_bias": p["muscle_bias"],
        }


class BrainController:
    """Runs a population of brains (one parameter vector per worm) as a controller."""

    def __init__(self, brain: Brain, x: np.ndarray, record_every: int = 0):
        self.brain = brain
        self.x = np.atleast_2d(x)
        self.p = brain.decode(self.x)
        self.record_every = record_every

    def reset(self, n_worms: int) -> None:
        if n_worms != len(self.x):
            if len(self.x) != 1:
                raise ValueError(f"{len(self.x)} parameter vectors for {n_worms} worms")
            self.x = np.repeat(self.x, n_worms, axis=0)
            self.p = self.brain.decode(self.x)
        self.v = np.zeros((n_worms, self.brain.n))
        self.c_avg = None
        self.k = 0
        self.activity = []

    def sensory_input(self, obs: dict, dt: float) -> np.ndarray:
        b, p, cfg = self.brain, self.p, self.brain.cfg
        inp = np.zeros_like(self.v)
        c = obs["conc"]
        if self.c_avg is None:
            self.c_avg = c.copy()
        rel = (c - self.c_avg) / (cfg.conc_ref + np.abs(self.c_avg))
        self.c_avg = self.c_avg + (c - self.c_avg) * dt / p["tau_adapt"][:, 0]
        inp[:, b.on_idx] += p["salt_on"] * np.maximum(rel, 0)[:, None]
        inp[:, b.off_idx] += p["salt_off"] * np.maximum(-rel, 0)[:, None]
        kappa = obs["kappa"] @ b.joints_to_prop.T / b.kappa_max  # (P, n_prop)
        inp[:, b.prop_idx] += p["proprio_gain"] * b.prop_side * kappa
        return inp

    def step(self, obs: dict, dt: float) -> np.ndarray:
        b, p = self.brain, self.p
        out = _sigmoid(p["gain"] * self.v) * b.alive
        drive = p["g_chem"] * (out @ b.W) + p["g_gap"] * (self.v @ b.M)
        drive += p["bias"] + self.sensory_input(obs, dt)
        a = dt / p["tau"]
        self.v = (self.v + a * drive) / (1.0 + a * (1.0 + p["g_gap"] * b.gap_self))
        self.v *= b.alive
        check_finite(self.v)
        self.k += 1
        if self.record_every and self.k % self.record_every == 0:
            self.activity.append(self.v.copy())
        muscle = _sigmoid(p["muscle_gain"] * (out @ b.R) + p["muscle_bias"])
        return muscle.reshape(-1, 4, MUSCLE_ROWS)


def check_finite(v: np.ndarray) -> None:
    if not np.isfinite(v).all():
        raise FloatingPointError("brain state became non-finite")
