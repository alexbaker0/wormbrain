# ruff: noqa: E501
"""Behaviour scorecard: does a trained worm behave like a real one?

    uv run python scripts/scorecard.py reports/A reports/B ...   (every run in <folder>/runs)

None of these measures is a training objective; they are the yardstick the objectives are
judged by. Real-worm reference values are in REFERENCE (sources in OBJECTIVES.md).

Flat field (60 s):
  speed        net crawling speed, mm/s                      real: about 0.2
  freq         undulation frequency, Hz                      real: about 0.3 (0.3-0.5)
  wavelength   bending wavelength, body lengths              real: about 0.65
  turning      path curvature, deg/mm (1 mm circle = 57)     real: near 0 (long runs)
One food source (Gaussian, sigma 4 mm, 32 starts 4-8 mm away, 150 s):
  CI           chemotaxis index 1 - mean(distance)/start distance, distance counted as 0
               once the head is within 1 mm (Izquierdo & Lockery 2010 use the time-averaged
               distance; "reached" stops the clock)       ideal: about 0.8
  reached      share of worms that get within 1 mm
  efficiency   straight-line distance / path length, for worms that reached (1 = direct)
  weathervane  curving towards the food side, deg/mm, while the food is to one side
               (Iino & Yoshida 2009: real worms curve towards the peak; > 0)
  turn ratio   |turning| while the smell falls / while it rises (pirouette-like; real > 1,
               Pierce-Shimomura et al. 1999)
  one-way      share of the approach turning that goes one way (circling = 100%)
  slowing      speed within 1 mm of food / speed far from it (real worms slow on food,
               Sawin et al. 2000; < 1)
Patch world v2 (12 min, held-out layout): patches eaten.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

from wormbrain.brain import BrainController
from wormbrain.chemotaxis import env_config, load_run_config
from wormbrain.controllers import GradientSteering, TravelingWave
from wormbrain.env import Field, PatchField, make_body, mean_curvature, run_episode, start_positions
from wormbrain.export import build_brain
from wormbrain.locomotion import FLAT, KappaRecorder, undulation_frequency, wave_direction

REFERENCE = {
    "speed": "≈0.2",
    "freq": "≈0.3",
    "wavelength": "≈0.65",
    "turning": "≈0",
    "CI": "high",
    "reached": "high",
    "efficiency": "→1",
    "weathervane": ">0",
    "turn ratio": ">1",
    "one-way": "low",
    "slowing": "<1",
    "patches": "—",
}
COLS = list(REFERENCE)
PATCHES = {
    "half_size": 25.0,
    "n_patches": 24,
    "sigma": 1.5,
    "eat_radius": 1.0,
    "eat_rate": 0.03,
    "min_spacing": 6.0,
    "periodic": True,
}
DT = 0.02


def wavelength(kappa: np.ndarray, dt: float) -> float:
    """Bending wavelength in body lengths, from the phase lag along the body at the
    undulation frequency."""
    k = kappa - kappa.mean(0)
    spec = np.fft.rfft(k, axis=0)
    b = 1 + (np.abs(spec[1:]) ** 2).sum(1).argmax()
    phase = np.unwrap(np.angle(spec[b]))
    s = (np.arange(k.shape[1]) + 1) / (k.shape[1] + 1)
    slope = np.polyfit(s, phase, 1, w=np.abs(spec[b]))[0]
    return float(2 * np.pi / abs(slope)) if abs(slope) > 1e-6 else float("inf")


def flat_card(make, body) -> dict:
    rec = KappaRecorder(make(1))
    ep = run_episode(rec, FLAT, np.zeros((1, 2)), np.zeros(1), duration=60.0, dt=DT, body=body)
    kappa = np.array(rec.kappa)[int(10 / DT) :, 0]
    k = np.searchsorted(ep.t, 10.0)
    speed = np.linalg.norm(ep.centroid[-1, 0] - ep.centroid[k, 0]) / (ep.t[-1] - ep.t[k])
    moving = kappa.std(0).mean() > 1e-3
    ep8 = run_episode(
        make(8),
        FLAT,
        np.zeros((8, 2)),
        np.linspace(0, 2 * np.pi, 8, endpoint=False),
        duration=120.0,
        dt=DT,
        body=body,
    )
    return {
        "speed": float(speed),
        "freq": undulation_frequency(kappa, DT) if moving else 0.0,
        "wavelength": wavelength(kappa, DT) if moving else float("nan"),
        "wave": wave_direction(kappa) if moving else 0.0,
        "turning": float(mean_curvature(ep8).mean()),
    }


def taxis_card(make, body, n=32) -> dict:
    field = Field({"type": "gaussian", "peak": [0.0, 0.0], "sigma": 4.0})
    head, heading = start_positions({"distance": [4.0, 8.0]}, field, n, seed=4242)
    ep = run_episode(make(n), field, head, heading, duration=150.0, dt=DT, body=body)
    rdt = ep.t[1] - ep.t[0]
    d = np.linalg.norm(ep.head, axis=-1)  # (T, n) distance of the head from the food
    at = d < 1.0
    reached = at.any(0)
    first = np.where(reached, at.argmax(0), len(ep.t))  # record index of arrival
    idx = np.arange(len(ep.t))[:, None]
    before = idx < first[None, :]
    ci = 1.0 - (d * before).mean(0) / d[0]
    path = np.linalg.norm(np.diff(ep.centroid, axis=0), axis=-1)
    plen = (path * before[1:]).sum(0)
    eff = np.where(reached, (d[0] - 1.0) / np.maximum(plen, 1e-9), np.nan)
    # travel direction and turning over 4 s windows (longer than one undulation)
    w = int(round(4.0 / rdt))
    c = ep.centroid
    disp = c[w:] - c[:-w]
    ang = np.unwrap(np.arctan2(disp[..., 1], disp[..., 0]), axis=0)
    turn = np.diff(ang, axis=0) / rdt  # rad/s, + = left; index i ~ time i + w/2
    mid = c[w // 2 : w // 2 + len(turn)]
    spd = np.linalg.norm(disp[:-1], axis=-1) / (w * rdt)
    to_food = np.arctan2(-mid[..., 1], -mid[..., 0])
    bearing = np.angle(np.exp(1j * (to_food - ang[:-1])))  # + = food on the left
    appr = before[w // 2 : w // 2 + len(turn)] & (np.arange(len(turn))[:, None] * rdt > 10.0)
    side = (
        appr
        & (np.abs(bearing) > np.deg2rad(30))
        & (np.abs(bearing) < np.deg2rad(150))
        & (spd > 0.02)
    )
    weather = (
        np.rad2deg((turn * np.sign(bearing))[side].sum() / max((spd[side]).sum(), 1e-9))
        if side.any()
        else np.nan
    )
    dc = (ep.conc[w:] - ep.conc[:-w])[:-1]
    fall, rise = appr & (dc < 0), appr & (dc > 0)
    ratio = (
        np.abs(turn[fall]).mean() / max(np.abs(turn[rise]).mean(), 1e-9)
        if fall.any() and rise.any()
        else np.nan
    )
    one_way = sum(abs(turn[:, j][appr[:, j]].sum()) for j in range(n)) / max(
        np.abs(turn[appr]).sum(), 1e-9
    )
    inst = path / rdt
    near, far = at[1:], d[1:] > 3.0
    slowing = (
        inst[near].mean() / max(inst[far].mean(), 1e-9) if near.any() and far.any() else np.nan
    )
    return {
        "CI": float(ci.mean()),
        "reached": float(reached.mean()),
        "efficiency": float(np.nanmean(eff)) if reached.any() else float("nan"),
        "weathervane": float(weather),
        "turn ratio": float(ratio),
        "one-way": float(one_way),
        "slowing": float(slowing),
    }


def patch_card(make, body, n=16) -> dict:
    field = PatchField(PATCHES)
    field.relayout(9999)
    head, heading = field.starts({"half_size": 15.0, "clearance": 4.0}, n, 9999)
    ep = run_episode(make(n), field, head, heading, duration=720.0, dt=DT, body=body)
    return {"patches": float(ep.eaten[-1].mean())}


def card(make, body, patches=True) -> dict:
    out = flat_card(make, body) | taxis_card(make, body)
    return out | (patch_card(make, body) if patches else {"patches": float("nan")})


def fmt(key, v):
    if v != v:
        return "—"
    if key in ("reached", "one-way"):
        return f"{v:.0%}"
    if key in ("turning",):
        return f"{v:.0f}"
    return f"{v:.2f}"


def main(folders):
    cfg = load_run_config("configs/chemotaxis.yaml")
    body = make_body(env_config(cfg["env"], cfg["env_overrides"])["body"])
    lines = [
        "| brain | run | " + " | ".join(COLS) + " |",
        "|---|---|" + "---|" * len(COLS),
        "| *real worm* | | " + " | ".join(REFERENCE[c] for c in COLS) + " |",
    ]
    rows = []
    entries = [(Path(f).name, p) for f in folders for p in sorted(Path(f, "runs").glob("*.json"))]
    for label, path in entries + [("hand-coded steering", None), ("blind straight", None)]:
        if path is None:
            make = (
                (lambda n: GradientSteering())
                if "steering" in label
                else (lambda n: TravelingWave())
            )
            name = ""
        else:
            run = json.loads(path.read_text())
            brain, x = build_brain(run), np.array(run["x"])
            make = lambda n, b=brain, x=x: BrainController(b, np.repeat(x[None], n, 0))  # noqa: E731
            name = (
                path.stem.replace("_glu-", " ")
                .replace("itatory", "")
                .replace("ibitory", "")
                .replace("_seed", " s")
            )
        m = card(make, body)
        rows.append({"brain": label, "run": name} | m)
        lines.append(f"| {label} | {name} | " + " | ".join(fmt(c, m[c]) for c in COLS) + " |")
        print(lines[-1], flush=True)
    out = Path(folders[0]) if len(folders) == 1 else Path("reports/scorecard")
    out.mkdir(parents=True, exist_ok=True)
    (out / "scorecard.md").write_text(
        "\n".join(["# Behaviour scorecard", "", "```", __doc__.strip(), "```", "", *lines, ""])
    )
    (out / "scorecard.json").write_text(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main(sys.argv[1:])
