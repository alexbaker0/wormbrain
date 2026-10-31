"""Export trained brains for the browser simulation (web/sim.js), and reference runs
for checking that the JavaScript port matches Python.

The export holds everything the brain and body step need, with parameters already
decoded to per-neuron values, so the JavaScript does no training-side maths. Sparse
matrices are coordinate lists (row = presynaptic or source, col = postsynaptic or
target). Floats are written at full precision so both sides compute the same thing.
"""

from __future__ import annotations

import numpy as np

from .body import Body, BodyParams
from .brain import Brain, BrainConfig, BrainController
from .connectome import build_connectome, load_config
from .controls import make_condition
from .env import Field


def _coo(m: np.ndarray) -> dict:
    r, c = np.nonzero(m)
    return {"row": r.tolist(), "col": c.tolist(), "val": m[r, c].tolist()}


def build_brain(run: dict, lesion=()) -> Brain:
    cfg = load_config("configs/connectome.yaml")
    cfg["signs"]["glutamate"] = run["glutamate"]
    conn = make_condition(build_connectome(cfg), run["condition"], run["seed"])
    bc = BrainConfig(bounded=run.get("bounded", False), activation=run.get("activation", "sigmoid"),
                     lesion=tuple(lesion))  # fmt: skip
    return Brain(conn, bc)


def export_model(run: dict, title: str, body_cfg: dict) -> dict:
    """Everything web/sim.js needs to run one trained brain in one body."""
    brain = build_brain(run)
    if brain.cfg.normalise != "per_neuron":
        raise NotImplementedError("web export supports per-neuron input scaling only")
    p = brain.decode(np.array(run["x"])[None])
    conn = brain.conn
    body = Body(BodyParams(**body_cfg))

    def vec(key):
        return np.broadcast_to(p[key][0], (conn.n,)).tolist()

    def scalar(key):
        return float(np.ravel(p[key])[0])

    return {
        "title": title,
        "run": f"{run['condition']}_glu-{run['glutamate']}_seed{run['seed']}",
        "condition": run["condition"],
        "testReward": run["test"]["gaussian"]["brain"]["reward_mean"],
        "neurons": conn.neurons,
        "roles": conn.role,
        "classes": conn.cell_class,
        "activation": brain.cfg.activation,
        "W": _coo(brain.W),  # chemical, per-neuron normalised and signed
        "M": _coo(brain.M),  # gap junctions, per-neuron normalised
        "R": _coo(brain.R),  # neuron -> muscle slot (quadrant * 24 + row - 1)
        "tau": vec("tau"),
        "bias": vec("bias"),
        "gain": vec("gain"),
        "adapt": vec("adapt") if p["adapt"] is not None else None,
        "adaptTau": scalar("adapt_tau") if p["adapt_tau"] is not None else None,
        "gChem": scalar("g_chem"),
        "gGap": scalar("g_gap"),
        "saltOn": scalar("salt_on"),
        "saltOff": scalar("salt_off"),
        "saltTau": scalar("salt_tau"),
        "concRef": brain.cfg.conc_ref,
        "onIdx": brain.on_idx.tolist(),
        "offIdx": brain.off_idx.tolist(),
        "propIdx": brain.prop_idx.tolist(),
        "propSide": brain.prop_side.tolist(),
        "jointsToProp": brain.joints_to_prop.tolist(),
        "proprioGain": scalar("proprio_gain"),
        "muscleGain": scalar("muscle_gain"),
        "muscleBias": scalar("muscle_bias"),
        "body": {
            "length": body.p.length,
            "nSegments": body.p.n_segments,
            "dragT": body.p.drag_tangential,
            "dragN": body.p.drag_normal,
            "kappaMax": body.p.kappa_max,
            "tauMuscle": body.p.tau_muscle,
            "rowsToJoints": body.rows_to_joints.tolist(),
        },
    }


def reference_run(run: dict, body_cfg: dict, field_cfg: dict, head, heading, steps: int,
                  dt: float, lesion=(), every: int = 50) -> dict:  # fmt: skip
    """Step-by-step Python run, in exactly the order ``env.run_episode`` uses."""
    brain = build_brain(run, lesion)
    body = Body(BodyParams(**body_cfg))
    field = Field(field_cfg)
    ctrl = BrainController(brain, np.array(run["x"])[None])
    state = body.reset(np.array([head], float), np.array([heading], float))
    ctrl.reset(1)
    out = {"step": [], "head": [], "theta0": [], "kappa": [], "v": []}
    for k in range(1, steps + 1):
        obs = {"t": (k - 1) * dt, "conc": field.conc(state.head), "kappa": state.kappa}
        body.step(state, ctrl.step(obs, dt), dt)
        if k % every == 0:
            out["step"].append(k)
            out["head"].append(state.head[0].tolist())
            out["theta0"].append(float(state.theta0[0]))
            out["kappa"].append(state.kappa[0].tolist())
            out["v"].append(ctrl.v[0].tolist())
    return out
