"""Chemotaxis training in two stages, and evaluation on held-out conditions.

Stage 1 trains crawling (``wormbrain.locomotion``, forward speed on a flat field).
Stage 2 starts CMA-ES from the stage-1 result and maximises the chemotaxis reward
(``env.reward``: concentration gained minus an energy penalty). Every graph
condition goes through exactly the same stages and budget.

Within a generation all candidates face the same random start positions and
headings (common random numbers, so they are compared fairly); the starts change
every generation, so a candidate cannot overfit a few starts. At the end the best
candidate seen and the final search mean are compared on a validation set and the
better is kept; it is then tested on a separate, fixed test set, including arenas and
start distances never used in training.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import numpy as np
import yaml

from .brain import BrainController
from .controllers import GradientSteering, TravelingWave
from .env import (
    Field,
    load_env_config,
    mean_curvature,
    mean_turning_rate,
    path_speed,
    reward,
    run_episode,
    start_positions,
)
from .locomotion import FLAT, setup, train_locomotion
from .train import cmaes

LOCOMOTION_RUNS = Path("reports/locomotion_study/runs")


def load_run_config(path, **overrides) -> dict:
    cfg = yaml.safe_load(Path(path).read_text())
    for k, v in overrides.items():
        if v is not None:
            cfg[k] = v
    return cfg


def env_config(paths, overrides: dict | None = None) -> dict:
    env = load_env_config(*paths)
    for section, values in (overrides or {}).items():
        env[section] = {**env.get(section, {}), **values} if section != "field" else values
    return env


def run_name(cfg: dict) -> str:
    return f"{cfg['condition']}_glu-{cfg['glutamate']}_seed{cfg['seed']}"


def batch_rewards(brain, body, X, field, env, starts) -> np.ndarray:
    """Mean reward of each parameter vector in X (P, D) over the same starts."""
    head, heading = starts
    n = len(heading)
    Xr = np.repeat(X, n, axis=0)
    ep = run_episode(BrainController(brain, Xr), field, np.tile(head, (len(X), 1)),
                     np.tile(heading, len(X)), body=body, **env["episode"])  # fmt: skip
    return reward(ep, field, env["reward"]).reshape(len(X), n).mean(1)


def flat_turning(brain, body, X, n_headings: int, duration: float, dt: float, seed: int,
                 per_mm: bool = False):  # fmt: skip
    """Mean |turning| of each parameter vector crawling on a flat field.

    Degrees per second, or with ``per_mm`` degrees per mm of net progress.
    """
    headings = np.random.default_rng(seed).uniform(0, 2 * np.pi, n_headings)
    Xr = np.repeat(np.atleast_2d(X), n_headings, axis=0)
    ep = run_episode(BrainController(brain, Xr), FLAT, np.zeros((len(Xr), 2)),
                     np.tile(headings, len(Xr) // n_headings), duration=duration, dt=dt,
                     body=body)  # fmt: skip
    turn = mean_curvature(ep) if per_mm else np.abs(mean_turning_rate(ep))
    return turn.reshape(-1, n_headings).mean(1)


def straightness_penalty(brain, body, X, cfg: dict, seed: int) -> np.ndarray:
    """``weight`` x turning above ``threshold`` deg/s on a flat field (0 if not configured).

    Real worms crawl roughly straight when nothing guides them; without this term
    training settles on worms that circle one way and drift up the gradient.
    """
    st = cfg.get("straightness")
    if not st:
        return np.zeros(len(np.atleast_2d(X)))
    per_mm = st.get("measure") == "per_mm"
    turn = flat_turning(brain, body, X, st["n_headings"], st["duration"], st["dt"], seed, per_mm)
    threshold = st["threshold_deg_mm"] if per_mm else st["threshold_deg_s"]
    return st["weight"] * np.maximum(0.0, turn - threshold)


def stage1(cfg: dict, verbose: bool = False) -> dict:
    """Crawling stage; reuses the locomotion study's identical run if it exists."""
    s1 = cfg["stage1"]
    cached = LOCOMOTION_RUNS / f"{run_name(cfg)}.json"
    if cached.exists():
        r = json.loads(cached.read_text())
        same = (r["generations"], r["popsize"], r["sigma0"]) == (
            s1["generations"], s1["popsize"], s1["sigma0"])  # fmt: skip
        model = (r["adaptation"], r.get("bounded", False), r.get("activation", "sigmoid"))
        if same and model == (True, cfg.get("bounded", True), cfg.get("activation", "tanh")):
            return r | {"reused_from": str(cached)}
    return train_locomotion(cfg["condition"], cfg["seed"], cfg["glutamate"], True,
                            s1["generations"], s1["popsize"], s1["sigma0"],
                            verbose=verbose, bounded=cfg.get("bounded", True),
                            activation=cfg.get("activation", "tanh"))  # fmt: skip


def stage2(cfg: dict, x_start: np.ndarray, verbose: bool = False, log_path=None) -> dict:
    brain, body, _ = setup(cfg["condition"], cfg["seed"], cfg["glutamate"], True,
                           cfg.get("bounded", True), cfg.get("activation", "tanh"))  # fmt: skip
    env = env_config(cfg["env"], cfg.get("env_overrides"))
    field = Field(env["field"])
    s2 = cfg["stage2"]
    gen = {"k": 0}

    def objective(X):
        seed = 10_000 * (cfg["seed"] + 1) + gen["k"]  # new starts each generation
        gen["k"] += 1
        starts = start_positions(env["start"], field, s2["n_starts"], seed)
        r = batch_rewards(brain, body, X, field, env, starts)
        return r - straightness_penalty(brain, body, X, cfg, seed)

    res = cmaes(objective, x_start, sigma0=s2["sigma0"], popsize=s2["popsize"],
                generations=s2["generations"], seed=cfg["seed"], log_path=log_path,
                verbose=verbose)  # fmt: skip

    # choose between the best candidate seen and the final mean on a validation set
    val = cfg["evaluation"]
    starts = start_positions(env["start"], field, val["n_starts"], val["validation_seed"])
    cand = np.stack([res["best_x"], res["mean_x"]])
    scores = batch_rewards(brain, body, cand, field, env, starts)
    scores = scores - straightness_penalty(brain, body, cand, cfg, val["validation_seed"])
    chosen = int(np.argmax(scores))
    return {
        "x": cand[chosen].tolist(),
        "chosen": ["best_seen", "final_mean"][chosen],
        "validation_reward": [float(s) for s in scores],
        "history": res["history"],
    }


def _metrics(ep, field, env) -> dict:
    r = reward(ep, field, env["reward"])
    gain = reward(ep, field, env["reward"] | {"energy_weight": 0.0, "idle_penalty": 0.0})
    out = {
        "reward_mean": float(r.mean()),
        "reward_sd": float(r.std(ddof=1)),
        "conc_gain_mean": float(gain.mean()),
        "power_mean": float(ep.power[1:].mean()),
        "path_speed_mean": float(path_speed(ep).mean()),
        "climbed_fraction": float((gain > 0).mean()),
    }
    if field.kind != "linear":
        d = np.linalg.norm(ep.centroid[-1] - field.center, axis=1)
        out |= {"final_distance_mean": float(d.mean()), "reached_1mm": float((d < 1.0).mean())}
    return out


def evaluate(cfg: dict, x) -> dict:
    """Test-set performance in every evaluation arena, with hand-coded baselines."""
    brain, body, _ = setup(cfg["condition"], cfg["seed"], cfg["glutamate"], True,
                           cfg.get("bounded", True), cfg.get("activation", "tanh"))  # fmt: skip
    ev = cfg["evaluation"]
    out = {}
    for arena, spec in ev["arenas"].items():
        env = env_config(
            spec["env"], copy.deepcopy(cfg.get("env_overrides")) | spec.get("overrides", {})
        )
        field = Field(env["field"])
        head, heading = start_positions(env["start"], field, ev["n_starts"], ev["test_seed"])
        n = len(heading)
        controllers = {
            "brain": BrainController(brain, np.repeat(np.atleast_2d(x), n, axis=0)),
            "blind_crawling": TravelingWave(),
            "gradient_steering": GradientSteering(),
        }
        out[arena] = {
            name: _metrics(
                run_episode(c, field, head, heading, body=body, **env["episode"]), field, env
            )  # fmt: skip
            for name, c in controllers.items()
        }
    return out


def flat_field_measures(cfg: dict, x) -> dict:
    """Turning of a trained brain on a flat field, 8 headings x 120 s, both measures."""
    brain, body, _ = setup(cfg["condition"], cfg["seed"], cfg["glutamate"], True,
                           cfg.get("bounded", True), cfg.get("activation", "tanh"))  # fmt: skip
    seed = cfg["evaluation"]["test_seed"]
    return {
        "flat_turning_deg_s": float(flat_turning(brain, body, x, 8, 120.0, 0.02, seed)[0]),
        "flat_curvature_deg_mm": float(
            flat_turning(brain, body, x, 8, 120.0, 0.02, seed, per_mm=True)[0]
        ),
    }


def _same_stage1(cfg: dict, other: Path) -> bool:
    """Was the crawling stage in ``other`` run with identical settings and model?"""
    if not (other / "stage1.json").exists() or not (other / "config.yaml").exists():
        return False
    o = yaml.safe_load((other / "config.yaml").read_text())
    keys = ("condition", "glutamate", "seed", "bounded", "activation", "stage1")
    return all(o.get(k) == cfg.get(k) for k in keys)


def train_and_evaluate(cfg: dict, out_dir: Path, verbose: bool = False) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "config.yaml").write_text(yaml.safe_dump(cfg, sort_keys=False))
    s1_path, s2_path = out_dir / "stage1.json", out_dir / "stage2.json"
    reuse = Path(cfg["stage1_from"]) / run_name(cfg) if cfg.get("stage1_from") else None
    if s1_path.exists():
        s1 = json.loads(s1_path.read_text())
    elif cfg.get("init_from"):
        # fine-tuning: start the chemotaxis stage from an earlier trained brain
        src_path = Path(cfg["init_from"]) / f"{run_name(cfg)}.json"
        src = json.loads(src_path.read_text())
        s1 = {"best_x": src["x"], "forward_speed_mm_s": src["stage1_speed_mm_s"],
              "reused_from": str(src_path), "init_test_reward":
              src["test"]["gaussian"]["brain"]["reward_mean"]}  # fmt: skip
        s1_path.write_text(json.dumps(s1))
    elif reuse and _same_stage1(cfg, reuse):
        s1 = json.loads((reuse / "stage1.json").read_text()) | {"reused_from": str(reuse)}
        s1_path.write_text(json.dumps(s1))
    else:
        s1 = stage1(cfg, verbose)
        s1_path.write_text(json.dumps(s1))
    if s2_path.exists():
        s2 = json.loads(s2_path.read_text())
    else:
        s2 = stage2(cfg, np.array(s1["best_x"]), verbose, log_path=out_dir / "stage2.log.json")
        s2_path.write_text(json.dumps(s2))
    result = {
        "run": run_name(cfg),
        "condition": cfg["condition"],
        "glutamate": cfg["glutamate"],
        "seed": cfg["seed"],
        "bounded": cfg.get("bounded", True),
        "activation": cfg.get("activation", "tanh"),
        "stage1_speed_mm_s": s1["forward_speed_mm_s"],
        "stage1_reused": "reused_from" in s1,
        "chosen": s2["chosen"],
        "curve": [h["best"] for h in s2["history"]],
        "curve_mean": [h["mean"] for h in s2["history"]],
        "stage2_seconds": s2["history"][-1]["seconds"],
        "test": evaluate(cfg, np.array(s2["x"])),
        **flat_field_measures(cfg, np.array(s2["x"])),
        "x": s2["x"],
    }
    (out_dir / "result.json").write_text(json.dumps(result))
    return result
