"""Graded (non-spiking) connectome brain driving the body.

One leaky-integrator unit per neuron:

    tau_i dv_i/dt = -v_i + g_chem * sum_j W_ji phi_j(v_j)
                         + g_gap * sum_j M_ji (v_j - v_i) + b_i + input_i - w_i a_i
    tau_a da_i/dt = v_i - a_i              (slow adaptation current)
    phi_j(v) = sigmoid(gain_j * v)          (transmitter release, in [0, 1])

The adaptation current ``a`` is a slow negative feedback on each neuron's own
activity, like the calcium-activated potassium currents many neurons have. Without
it, every graph we tried (real, rewired, random) settled to a steady posture and
never crawled (reports/locomotion/); with it, the network can generate rhythms.

``W`` is the chemical wiring with signs, each neuron's inputs divided by its total
incoming synapse weight; ``M`` is the gap-junction wiring, normalised the same way.
Normalising per neuron keeps every neuron's input on the same scale whatever its
connectivity, in the real graph and in every control. Lesions are applied after
normalisation, so a silenced neuron simply stops contributing.

Integration is semi-implicit Euler: the leak and gap-junction self-terms are
implicit, everything else explicit. Because inputs are normalised and sigmoids are
bounded, ``v`` stays bounded for any step size. With adaptation, ``v`` and ``a``
are solved together implicitly (closed form per neuron), which stays stable however
strong the adaptation; an explicit update blew up for strong adaptation in testing.
``check_finite`` guards against anything else.

Fixed: which neurons connect, the weights and signs, the neuron->muscle synapses.
Trained (``ParamSpec``): per neuron class tau, bias and gain; global g_chem, g_gap;
adaptation strength per class and its global time constant; salt sensor gains
and averaging time; proprioceptive gain; muscle gain and bias.

Inputs
------
- ASEL is an ON cell and ASER an OFF cell for salt (Suzuki et al. 2008, Nature
  454:114): each sees the rectified relative change of concentration at the nose
  against a running average over ``salt_tau`` (transient, as observed).
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
    adaptation: bool = True  # slow per-neuron adaptation current (see module docstring)
    # Keep every parameter in a plausible range, so training cannot switch the chemical
    # wiring or a neuron off (a pilot brain scaled its chemical synapses to 0.01 and
    # crawled on gap junctions alone). False restores the unbounded milestone-4 model.
    bounded: bool = True
    # "per_neuron": each neuron's inputs divided by its own total input weight.
    # "global": raw synapse weights divided by one constant (the mean total input over
    # neurons that have inputs), so strong synapses carry strong signals.
    # "unit_loop_gain": raw synapse weights scaled so the network's largest eigenvalue
    # (of the unsigned weights) times the activation's steepest slope is 1: at unit
    # neuron gain, signals neither die out nor blow up on their way through. Gap
    # junctions stay per-neuron. Each graph is scaled by its own eigenvalue, the same
    # rule for every condition.
    normalise: str = "per_neuron"
    # Transmitter release as a function of v. "sigmoid": in [0, 1], about 0.5 at rest,
    # so every synapse also carries a large constant drive. "tanh": in [-1, 1], 0 at
    # rest, so a synapse transmits changes up or down around a tonic release level.
    activation: str = "tanh"  # sigmoid let no salt signal reach the motor neurons
    lesion: tuple[str, ...] = ()
    init: dict = field(default_factory=dict)  # overrides of ParamSpec defaults


def _sigmoid(x):
    return 0.5 * (1.0 + np.tanh(0.5 * x))


ACTIVATION = {"sigmoid": _sigmoid, "tanh": np.tanh}
SLOPE = {"sigmoid": 0.25, "tanh": 1.0}  # steepest slope at unit gain


def _normalise_global(w):
    total = np.abs(w).sum(0)
    return w / total[total > 0].mean()


def _unit_loop_gain(w, slope):
    """Scale so the largest eigenvalue of |w| times the activation's slope is 1."""
    rho = np.max(np.abs(np.linalg.eigvals(np.abs(w))))
    return w / (rho * slope)


def _normalise_columns(w):
    total = np.abs(w).sum(0, keepdims=True)
    return np.divide(w, total, out=np.zeros_like(w, dtype=float), where=total > 0)


class ParamSpec:
    """Layout of the flat parameter vector the optimiser sees."""

    def __init__(self, n_groups: int, init: dict, adaptation: bool = True, bounded: bool = True):
        # name: (size, initial raw value); transforms are in Brain.decode
        self.blocks = {
            "tau": (n_groups, 0.0),
            "bias": (n_groups, 0.0),
            "gain": (n_groups, 0.0),
            "g_chem": (1, 0.0),
            "g_gap": (1, np.log(0.5)),
            "salt_gain": (2, np.log(20.0)),
            "salt_tau": (1, 0.0),
            "proprio_gain": (1, 0.0),
            "muscle_gain": (1, np.log(4.0)),
            "muscle_bias": (1, 0.0),
        }
        if adaptation:
            self.blocks |= {"adapt": (n_groups, np.log(0.5)), "adapt_tau": (1, 0.0)}
        if bounded:  # every bounded range is centred on the old starting value
            self.blocks = {k: (n, 0.0) for k, (n, _) in self.blocks.items()}
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
        self.spec = ParamSpec(int(self.group.max()) + 1, cfg.init, cfg.adaptation, cfg.bounded)

        alive = np.ones(n)
        alive[conn.index(list(cfg.lesion))] = 0.0
        self.alive = alive
        signed = conn.chem * conn.chem_sign
        if cfg.normalise == "per_neuron":
            W, M = _normalise_columns(signed), _normalise_columns(conn.gap)
        elif cfg.normalise == "global":
            W, M = _normalise_global(signed), _normalise_global(conn.gap)
        elif cfg.normalise == "unit_loop_gain":
            W, M = _unit_loop_gain(signed, SLOPE[cfg.activation]), _normalise_columns(conn.gap)
        else:
            raise ValueError(f"unknown normalise {cfg.normalise!r}")
        self.W = W * alive[:, None]
        self.M = M * alive[:, None] * alive[None, :]
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
        if self.cfg.bounded:
            pos, sym = _log_range, _signed_range
        else:
            pos = lambda raw, lo_, hi_, old: np.exp(raw)  # noqa: E731
            sym = lambda raw, lim: raw  # noqa: E731
        out = {
            "tau": (lo + (hi - lo) * _sigmoid(p["tau"]))[:, self.group],
            "bias": sym(p["bias"], BOUNDS["bias"])[:, self.group],
            "gain": pos(p["gain"], *BOUNDS["gain"], 1.0)[:, self.group],
            "g_chem": pos(p["g_chem"], *BOUNDS["g_chem"], 1.0),
            "g_gap": pos(p["g_gap"], *BOUNDS["g_gap"], 0.5),
            "salt_on": pos(p["salt_gain"][:, :1], *BOUNDS["salt_gain"], 20.0),
            "salt_off": pos(p["salt_gain"][:, 1:], *BOUNDS["salt_gain"], 20.0),
            "salt_tau": 0.5 + 9.5 * _sigmoid(p["salt_tau"]),
            "proprio_gain": sym(p["proprio_gain"], BOUNDS["proprio_gain"]),
            "muscle_gain": pos(p["muscle_gain"], *BOUNDS["muscle_gain"], 4.0),
            "muscle_bias": sym(p["muscle_bias"], BOUNDS["muscle_bias"]),
            "adapt": None,
            "adapt_tau": None,
        }
        if "adapt" in p:
            out["adapt"] = pos(p["adapt"], *BOUNDS["adapt"], 0.5)[:, self.group]
            out["adapt_tau"] = 0.2 + 4.8 * _sigmoid(p["adapt_tau"])
        return out


# Ranges for bounded parameters: (low, high) for positive scales, spread evenly on a
# log scale; a single limit L for signed values, which stay in (-L, L).
BOUNDS = {
    "bias": 3.0,
    "gain": (0.3, 10.0),
    "g_chem": (0.3, 3.0),
    "g_gap": (0.1, 3.0),
    "salt_gain": (4.0, 100.0),
    "proprio_gain": 10.0,
    "muscle_gain": (0.5, 30.0),
    "muscle_bias": 5.0,
    "adapt": (0.05, 5.0),
}


def _log_range(raw, lo, hi, _old=None):
    """Raw value -> (lo, hi), geometric midpoint at raw = 0."""
    return np.exp(np.log(lo) + (np.log(hi) - np.log(lo)) * _sigmoid(raw))


def _signed_range(raw, limit):
    """Raw value -> (-limit, limit), identity near 0."""
    return limit * np.tanh(raw / limit)


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
        self.a = np.zeros((n_worms, self.brain.n))
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
        self.c_avg = self.c_avg + (c - self.c_avg) * dt / p["salt_tau"][:, 0]
        inp[:, b.on_idx] += p["salt_on"] * np.maximum(rel, 0)[:, None]
        inp[:, b.off_idx] += p["salt_off"] * np.maximum(-rel, 0)[:, None]
        kappa = obs["kappa"] @ b.joints_to_prop.T / b.kappa_max  # (P, n_prop)
        inp[:, b.prop_idx] += p["proprio_gain"] * b.prop_side * kappa
        return inp

    def step(self, obs: dict, dt: float) -> np.ndarray:
        b, p = self.brain, self.p
        out = ACTIVATION[b.cfg.activation](p["gain"] * self.v) * b.alive
        drive = p["g_chem"] * (out @ b.W) + p["g_gap"] * (self.v @ b.M)
        drive += p["bias"] + self.sensory_input(obs, dt)
        r = dt / p["tau"]
        leak = 1.0 + r * (1.0 + p["g_gap"] * b.gap_self)
        if p["adapt"] is None:
            self.v = (self.v + r * drive) / leak
        else:
            # v and a updated together, both implicit (backward Euler on the linear part):
            #   v' = (v + r (drive - w a')) / leak,   a' = (a + ra v') / (1 + ra)
            ra = dt / p["adapt_tau"]
            w = p["adapt"]
            self.v = (self.v + r * drive - r * w * self.a / (1 + ra)) / (
                leak + r * w * ra / (1 + ra)
            )
            self.a = (self.a + ra * self.v) / (1 + ra)
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
