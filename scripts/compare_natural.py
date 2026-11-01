"""Overnight study: which "natural" reward gives real-worm-like chemotaxis?

    uv run python scripts/compare_natural.py

Every trained brain is scored on the same tests, whatever reward it was trained with:

- static food: 32 starts 4-8 mm from food, 150 s. Share of worms that reach the food
  (head within 1 mm at any time), median time to reach it, share of time spent at
  the food, share of starts that climbed.
- moving food: the same starts; at 60 s the food jumps 5-7 mm. Share of worms at the
  new food (within 1 mm) at any time in the following 90 s.
- flat field: turning per mm of net progress (8 headings, 120 s; real worms crawl
  roughly straight, a 1 mm circle is 57 deg/mm).

Rows: the starting milestone-6 brains, the straightness-penalty fine-tune, the natural-
reward scenarios A-E, and hand-coded baselines. Writes reports/natural_rewards/.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from wormbrain.brain import BrainController  # noqa: E402
from wormbrain.chemotaxis import env_config, load_run_config  # noqa: E402
from wormbrain.controllers import Forager, GradientSteering, TravelingWave  # noqa: E402
from wormbrain.env import (  # noqa: E402
    Field,
    PatchField,
    make_body,
    mean_curvature,
    run_episode,
    start_positions,
)
from wormbrain.export import build_brain  # noqa: E402
from wormbrain.locomotion import FLAT  # noqa: E402

OUT = Path("reports/natural_rewards")
SCENARIOS = [  # (label, results folder, config)
    ("start: milestone-6 brains", "reports/comparison/runs", "configs/chemotaxis.yaml"),
    ("straightness penalty (fine-tune)", "reports/chemotaxis_finetune_pilot/runs",
     "configs/chemotaxis_finetune.yaml"),
    ("A. fast approach", "reports/natural_fast/runs", "configs/natural_fast.yaml"),
    ("B. time eating", "reports/natural_eat/runs", "configs/natural_eat.yaml"),
    ("C. net energy", "reports/natural_energy/runs", "configs/natural_energy.yaml"),
    ("D. moving food", "reports/natural_moving/runs", "configs/natural_moving.yaml"),
    ("E. far food, longer", "reports/natural_far/runs", "configs/natural_far.yaml"),
    ("F. patch world, from scratch", "reports/patches/runs", "configs/patches.yaml"),
    ("G. patch world v2 (12 min, wrap-around)", "reports/patches_long/runs",
     "configs/patches_long.yaml"),
]  # fmt: skip
RUN_NAMES = [f"real_glu-{g}_seed{s}" for g in ("excitatory", "inhibitory") for s in (0, 1)]
DT, DURATION, N = 0.02, 150.0, 32


def tests(make_controller, body):
    field = Field({"type": "gaussian", "peak": [0.0, 0.0], "sigma": 4.0})
    head, heading = start_positions({"distance": [4.0, 8.0]}, field, N, seed=4242)
    ep = run_episode(make_controller(N), field, head, heading, duration=DURATION, dt=DT,
                     body=body)  # fmt: skip
    d = np.linalg.norm(ep.head - ep.food[:, None, :], axis=-1)
    at = d < 1.0
    reached = at.any(0)
    first = np.where(reached, at.argmax(0) * (ep.t[1] - ep.t[0]), np.inf)
    climbed = (ep.conc.mean(0) - ep.conc[0]) > 0
    rng = np.random.default_rng(4243)
    r, a = rng.uniform(5, 7), rng.uniform(0, 2 * np.pi)
    new = [r * np.cos(a), r * np.sin(a)]
    ep2 = run_episode(make_controller(N), field, head, heading, duration=DURATION, dt=DT,
                      body=body, food_events=[(60.0, new)])  # fmt: skip
    after = ep2.t > 60.0
    d2 = np.linalg.norm(ep2.head[after] - np.array(new), axis=-1)
    patches = PatchField({"half_size": 25.0, "n_patches": 24, "sigma": 1.5, "eat_radius": 1.0,
                          "eat_rate": 0.03, "min_spacing": 6.0, "periodic": True})  # fmt: skip
    ph, phd = start_positions({"half_size": 15.0, "clearance": 4.0}, patches, N, seed=9999)
    ep3 = run_episode(make_controller(N), patches, ph, phd, duration=720.0, dt=DT, body=body)
    flat = run_episode(make_controller(8), FLAT, np.zeros((8, 2)),
                       np.random.default_rng(4244).uniform(0, 2 * np.pi, 8), duration=120.0,
                       dt=DT, body=body)  # fmt: skip
    return {
        "reached": float(reached.mean()),
        "median_time_to_food_s": float(np.median(first)),
        "time_at_food": float(at.mean()),
        "climbed": float(climbed.mean()),
        "moving_food_reached": float((d2 < 1.0).any(0).mean()),
        "flat_curvature_deg_mm": float(mean_curvature(flat).mean()),
        "patch_food": float(ep3.eaten[-1].mean()),
        "patch_power": float(ep3.power[1:].mean()),
        "_paths": ep.centroid[:, :8].tolist(),
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    cfg = load_run_config("configs/chemotaxis.yaml")
    body = make_body(env_config(cfg["env"], cfg["env_overrides"])["body"])
    rows, paths = [], {}
    for label, folder, _ in SCENARIOS:
        for name in RUN_NAMES:
            path = Path(folder) / f"{name}.json"
            if not path.exists():
                continue
            run = json.loads(path.read_text())
            brain, x = build_brain(run), np.array(run["x"])
            m = tests(lambda n, brain=brain, x=x: BrainController(brain, np.repeat(x[None], n, 0)),
                      body)  # fmt: skip
            paths[(label, name)] = m.pop("_paths")
            rows.append({"scenario": label, "run": name} | m)
            print(label, name, {k: round(v, 3) for k, v in m.items()})
    for label, factory in [("hand-coded forager", lambda n: Forager()),
                           ("hand-coded steering", lambda n: GradientSteering()),
                           ("blind crawling", lambda n: TravelingWave())]:  # fmt: skip
        m = tests(factory, body)
        paths[(label, "")] = m.pop("_paths")
        rows.append({"scenario": label, "run": ""} | m)
    (OUT / "results.json").write_text(json.dumps(rows, indent=1))

    def fmt_time(t):
        return "never" if not np.isfinite(t) else f"{t:.0f} s"

    lines = [
        "# Natural rewards: which one gives real-worm-like chemotaxis?",
        "",
        "Generated by `scripts/compare_natural.py`. Every brain is scored on the same tests, "
        f"whatever it was trained with: {N} starts 4–8 mm from food, {DURATION:g} s; a "
        "moving-food test (food jumps 5–7 mm at 60 s); and turning on a flat field per mm "
        "of progress (a 1 mm circle is 57°/mm; straight is about 0). All runs: the real "
        "connectome, fine-tuned from the milestone-6 brains (seeds 0–1, both glutamate "
        "settings) for 100 generations.",
        "",
        "| scenario | run | reached food | median time to food | time at food "
        "| climbed | moving food re-reached | flat-field turning (°/mm) "
        "| patch world v2: food eaten in 12 min |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r['scenario']} | {r['run']} | {r['reached']:.0%} "
            f"| {fmt_time(r['median_time_to_food_s'])} | {r['time_at_food']:.0%} "
            f"| {r['climbed']:.0%} | {r['moving_food_reached']:.0%} "
            f"| {r['flat_curvature_deg_mm']:.0f} | {r['patch_food']:.2f} |"
        )
    lines += ["", "## Mean over the four runs of each scenario", "",
              "| scenario | reached food | time at food | moving food re-reached "
              "| flat-field turning (°/mm) | patch world: food eaten |",
              "|---|---|---|---|---|---|"]  # fmt: skip
    for label in dict.fromkeys(r["scenario"] for r in rows):
        rs = [r for r in rows if r["scenario"] == label]
        lines.append(
            f"| {label} | {np.mean([r['reached'] for r in rs]):.0%} "
            f"| {np.mean([r['time_at_food'] for r in rs]):.0%} "
            f"| {np.mean([r['moving_food_reached'] for r in rs]):.0%} "
            f"| {np.mean([r['flat_curvature_deg_mm'] for r in rs]):.0f} "
            f"| {np.mean([r['patch_food'] for r in rs]):.2f} |"
        )
    lines += ["", "![paths](paths.png)", ""]
    (OUT / "REPORT.md").write_text("\n".join(lines))

    # paths of the best run (most time at food) in each scenario
    labels = list(dict.fromkeys(r["scenario"] for r in rows))
    fig, axes = plt.subplots(2, (len(labels) + 1) // 2, figsize=(4 * ((len(labels) + 1) // 2), 8),
                             squeeze=False)  # fmt: skip
    g = np.linspace(-10, 10, 120)
    xx, yy = np.meshgrid(g, g)
    conc = np.exp(-(xx**2 + yy**2) / 32)
    for ax, label in zip(axes.ravel(), labels, strict=False):
        best = max((r for r in rows if r["scenario"] == label), key=lambda r: r["time_at_food"])
        ax.contourf(xx, yy, conc, levels=12, cmap="Greens")
        for p in np.array(paths[(label, best["run"])]).transpose(1, 0, 2):
            ax.plot(p[:, 0], p[:, 1], lw=0.8, color="C0")
        ax.set_title(f"{label}\n{best['run']}: reached {best['reached']:.0%}", fontsize=8)
        ax.set_aspect("equal")
        ax.set_xlim(-10, 10)
        ax.set_ylim(-10, 10)
    for ax in axes.ravel()[len(labels) :]:
        ax.axis("off")
    fig.tight_layout()
    fig.savefig(OUT / "paths.png", dpi=100)
    print("\n".join(lines))


if __name__ == "__main__":
    main()
