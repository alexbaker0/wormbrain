"""Do the foraging brains use their food-contact sense? Speed on food vs off it, and what
happens when the sense is cut.

    uv run python scripts/dwell_check.py reports/forage [config, default configs/forage.yaml]

Foraging world of configs/forage.yaml, 32 held-out starts, 240 s. "speed" is the body
centre's path speed. "sense cut" runs the same brain with the food-contact signal held at
zero (the smell is untouched). Writes <folder>/dwell.md.
"""

import json
import sys
from pathlib import Path

import numpy as np

from wormbrain.brain import BrainController
from wormbrain.chemotaxis import env_config, load_run_config
from wormbrain.env import make_body, make_field, run_episode, start_positions
from wormbrain.export import build_brain


def measure(make, cfg, body, n=32, cut=False):
    field = make_field(cfg["field"])
    head, heading = start_positions(cfg["start"], field, n, seed=4242)
    touch = []
    real_contact = field.contact

    def contact(h):
        c = real_contact(h)
        touch.append(c.copy())
        return np.zeros_like(c) if cut else c

    field.contact = contact
    dt = cfg["episode"]["dt"]
    ep = run_episode(make(n), field, head, heading, duration=240.0, dt=dt, body=body)
    on = np.array(touch)[9::10][: len(ep.t) - 1] > 0.5  # (T-1, n), matches recorded steps
    step = np.linalg.norm(np.diff(ep.centroid, axis=0), axis=-1) / np.diff(ep.t)[:, None]
    return {
        "foods": float(ep.eaten[-1].mean()),
        "on_food": float(on.mean()),
        "speed_on": float(step[on].mean()) if on.any() else float("nan"),
        "speed_off": float(step[~on].mean()),
    }


def main(folder, config="configs/forage.yaml"):
    cfg = load_run_config(config)
    env = env_config(cfg["env"], cfg["env_overrides"])
    body = make_body(env["body"])
    lines = [
        "# Is the food-contact sense used?",
        "",
        "```",
        __doc__.strip(),
        "```",
        "",
        "| brain | foods eaten | time on food | speed on food | speed off food | "
        "foods, sense cut | speed on food, sense cut |",
        "|---|---|---|---|---|---|---|",
    ]
    for path in sorted(Path(folder, "runs").glob("*.json")):
        run = json.loads(path.read_text())
        brain, x = build_brain(run), np.array(run["x"])
        make = lambda n, b=brain, x=x: BrainController(b, np.repeat(x[None], n, 0))  # noqa: E731
        a, c = measure(make, env, body), measure(make, env, body, cut=True)
        lines.append(
            f"| {path.stem} | {a['foods']:.2f} | {a['on_food']:.0%} | {a['speed_on']:.3f} | "
            f"{a['speed_off']:.3f} | {c['foods']:.2f} | {c['speed_on']:.3f} |"
        )
        print(lines[-1], flush=True)
    Path(folder, "dwell.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main(*sys.argv[1:3])
