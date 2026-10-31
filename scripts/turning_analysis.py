"""Why do trained worms circle? Turning bias, its dependence on smell, and its source.

    uv run python scripts/turning_analysis.py

For every milestone-6 run (and the hand-coded steering rule for reference):

1. Flat field (no gradient), 8 random headings, 120 s: mean turning rate (signed:
   + = counter-clockwise) and how consistent its sign is.
2. Salt gradient, the 32 test starts: turning rate while the concentration at the
   nose is rising vs falling (klinokinesis would turn less while rising).
3. Source: mean dorsal-minus-ventral muscle drive on the flat field, split into the
   contributions of each neuron class (release x neuron->muscle weights).

Writes reports/turning/turning.md and turning.png.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from wormbrain.body import MUSCLE_ROWS  # noqa: E402
from wormbrain.brain import ACTIVATION, BrainController  # noqa: E402
from wormbrain.chemotaxis import env_config, load_run_config  # noqa: E402
from wormbrain.controllers import GradientSteering  # noqa: E402
from wormbrain.env import Field, make_body, run_episode, start_positions  # noqa: E402
from wormbrain.export import build_brain  # noqa: E402

OUT = Path("reports/turning")
RUNS = Path("reports/comparison/runs")
FLAT = Field({"type": "linear", "slope": 0.0, "offset": 1.0})
DT, EVERY = 0.02, 5


class Recorder:
    """Wraps a controller; keeps dorsal/ventral muscle drive and neuron release."""

    def __init__(self, inner, brain=None):
        self.inner, self.brain = inner, brain

    def reset(self, n):
        self.inner.reset(n)
        self.dv, self.release, self.k = [], [], 0

    def step(self, obs, dt):
        m = self.inner.step(obs, dt)
        self.k += 1
        if self.k % EVERY == 0:
            self.dv.append(m[:, :2].mean((1, 2)) - m[:, 2:].mean((1, 2)))
            if self.brain is not None:
                p = self.inner.p
                rel = ACTIVATION[self.brain.cfg.activation](p["gain"] * self.inner.v)
                self.release.append(rel)
        return m


def turning_rate(ep, window=2.0):
    """Signed turning rate (deg/s) of the centroid's travel direction, (T', P)."""
    k = max(1, int(round(window / (ep.t[1] - ep.t[0]))))
    d = ep.centroid[k:] - ep.centroid[:-k]
    ang = np.unwrap(np.arctan2(d[..., 1], d[..., 0]), axis=0)
    return np.rad2deg(np.diff(ang, axis=0)) / (ep.t[1] - ep.t[0]), k


def analyse(controller_factory, brain, field, head, heading, body, duration):
    ctrl = Recorder(controller_factory(len(heading)), brain)
    ep = run_episode(ctrl, field, head, heading, duration=duration, dt=DT, body=body,
                     record_every=EVERY)  # fmt: skip
    return ep, ctrl


def main():
    run_cfg = load_run_config("configs/chemotaxis.yaml")
    env = env_config(run_cfg["env"], run_cfg["env_overrides"])
    body = make_body(env["body"])
    gauss = Field(env["field"])
    rng = np.random.default_rng(0)
    flat_head, flat_heading = np.zeros((8, 2)), rng.uniform(0, 2 * np.pi, 8)
    test_head, test_heading = start_positions(env["start"], gauss, 32,
                                              run_cfg["evaluation"]["test_seed"])  # fmt: skip

    runs = [json.loads(p.read_text()) for p in sorted(RUNS.glob("*.json"))]
    subjects = [(f"{r['condition']}_glu-{r['glutamate']}_seed{r['seed']}", r) for r in runs]
    subjects.append(("hand-coded steering", None))
    rows, contrib_rows, scatter = [], [], []
    for name, r in subjects:
        if r is None:
            brain = None

            def factory(n):
                return GradientSteering()
        else:
            brain = build_brain(r)
            x = np.array(r["x"])

            def factory(n, brain=brain, x=x):
                return BrainController(brain, np.repeat(x[None], n, 0))

        ep_f, rec_f = analyse(factory, brain, FLAT, flat_head, flat_heading, body, 120.0)
        tr_f, _ = turning_rate(ep_f)
        settle = int(20 / (EVERY * DT))  # skip the first 20 s
        mean_turn = tr_f[settle:].mean(0)  # per worm
        speed = np.linalg.norm(np.diff(ep_f.centroid[settle:], axis=0), axis=-1).sum(0) / 100.0
        radius = np.where(np.abs(mean_turn) > 1e-6,
                          speed / np.deg2rad(np.abs(mean_turn) + 1e-12), np.inf)  # fmt: skip
        dv = np.array(rec_f.dv)[settle:]

        ep_g, _ = analyse(factory, brain, gauss, test_head, test_heading, body, 90.0)
        tr_g, k = turning_rate(ep_g)
        c = ep_g.conc
        dc = (c[k:] - c[:-k])[1:]  # concentration change over the same 2 s windows
        rising, falling = np.abs(tr_g[dc > 0]), np.abs(tr_g[dc < 0])
        test_reward = r["test"]["gaussian"]["brain"]["reward_mean"] if r else 0.0
        rows.append(
            f"| {name} | {test_reward:+.2f} | {mean_turn.mean():+.0f} "
            f"| {np.mean(np.sign(mean_turn) == np.sign(mean_turn.mean())):.0%} "
            f"| {np.median(radius):.2f} | {dv.mean():+.3f} "
            f"| {rising.mean():.0f} | {falling.mean():.0f} |"
        )
        scatter.append((name, test_reward, mean_turn.mean(), rising.mean(), falling.mean()))

        if brain is not None and test_reward > 0.1:
            rel = np.array(rec_f.release)[settle:].mean((0, 1))  # mean release per neuron
            R = brain.R.reshape(brain.n, 4, MUSCLE_ROWS)
            dorsal_minus_ventral = R[:, :2].sum((1, 2)) / 2 - R[:, 2:].sum((1, 2)) / 2
            contrib = rel * dorsal_minus_ventral / MUSCLE_ROWS
            by_class: dict[str, float] = {}
            for i, cls in enumerate(brain.conn.cell_class):
                by_class[cls] = by_class.get(cls, 0.0) + contrib[i]
            top = sorted(by_class.items(), key=lambda kv: -abs(kv[1]))[:5]
            contrib_rows.append(f"| {name} | {contrib.sum():+.3f} | "
                                + ", ".join(f"{c} {v:+.3f}" for c, v in top) + " |")  # fmt: skip

    OUT.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    for name, rew, turn, ri, fa in scatter:
        col = "k" if name.startswith("hand") else {"real": "C2", "rewired": "C3",
                                                   "random": "C4"}[name.split("_")[0]]  # fmt: skip
        axes[0].scatter(turn, rew, color=col)
        axes[1].scatter(fa, ri, color=col)
    axes[0].axvline(0, color="0.7")
    axes[0].set_xlabel("mean turning rate on a flat field (deg/s, + = counter-clockwise)")
    axes[0].set_ylabel("test reward")
    lim = max(max(s[3] for s in scatter), max(s[4] for s in scatter)) * 1.05
    axes[1].plot([0, lim], [0, lim], color="0.7")
    axes[1].set_xlabel("turning rate while concentration falls (deg/s)")
    axes[1].set_ylabel("turning rate while it rises (deg/s)")
    axes[1].set_title("below the diagonal = turns less when things improve")
    for c, lab in [("C2", "real"), ("C3", "rewired"), ("C4", "random"), ("k", "hand-coded")]:
        axes[0].scatter([], [], color=c, label=lab)
    axes[0].legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "turning.png", dpi=110)

    lines = [
        "# Why do the trained worms circle?",
        "",
        "Generated by `scripts/turning_analysis.py`. Turning rate = rate of change of the "
        "centroid's travel direction over 2 s windows (+ = counter-clockwise).",
        "",
        "| run | test reward | mean turning on flat field (deg/s) | worms turning the same way "
        "| circle radius (mm) | dorsal − ventral muscle activation | turning while rising "
        "(deg/s) | turning while falling (deg/s) |",
        "|---|---|---|---|---|---|---|---|",
        *rows,
        "",
        "## Where the dorsal−ventral bias comes from (runs with test reward > 0.1)",
        "",
        "Mean release of each neuron on the flat field times its dorsal-minus-ventral "
        "neuromuscular weight; total and the five largest classes.",
        "",
        "| run | total | largest contributions |",
        "|---|---|---|",
        *contrib_rows,
        "",
        "![turning](turning.png)",
        "",
    ]
    (OUT / "turning.md").write_text("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
