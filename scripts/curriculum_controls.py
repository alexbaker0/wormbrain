# ruff: noqa: E501
"""Real vs rewired vs random wiring under the curriculum (symmetric body).

    uv run python scripts/curriculum_controls.py

Pools the patch-world results of reports/curr_sym_patch (real, seeds 0-1) and
reports/curr_sym_patch_more (real seeds 2-3, rewired and random seeds 0-1). Held-out
food eaten in 12 minutes, gradient-climbing share and flat-field turning per run; real vs
each control with the stratified exact permutation test (strata = glutamate setting),
Holm-corrected, and a bootstrap 95% CI of the difference. Exploratory: few runs per
condition. Writes reports/curriculum_controls/REPORT.md.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from wormbrain.stats import bootstrap_ci, holm, stratified_permutation

FOLDERS = ["reports/curr_sym_patch", "reports/curr_sym_patch_more"]
OUT = Path("reports/curriculum_controls")


def main():
    rows = []
    for folder in FOLDERS:
        path = Path(folder, "results.json")
        if path.exists():
            rows += json.loads(path.read_text())
    OUT.mkdir(parents=True, exist_ok=True)

    def sample(cond, key, seeds=None):
        out = {}
        for g in ("excitatory", "inhibitory"):
            out[g] = np.array([key(r) for r in rows if r["condition"] == cond
                               and r["glutamate"] == g
                               and (seeds is None or r["seed"] in seeds)])  # fmt: skip
        return out

    eaten = lambda r: r["test"]["patches"]["brain"]["eaten_mean"]  # noqa: E731
    lines = ["# Real vs rewired vs random wiring under the curriculum", "", __doc__.split("\n\n")[2],
             "", "| condition | glutamate | seed | food eaten | found food | climbed gradient "
             "| flat-field turning (°/mm) |", "|---|---|---|---|---|---|---|"]  # fmt: skip
    for r in sorted(rows, key=lambda r: (r["condition"], r["glutamate"], r["seed"])):
        t, g = r["test"]["patches"]["brain"], r["test"]["gaussian"]["brain"]
        lines.append(f"| {r['condition']} | {r['glutamate']} | {r['seed']} | {t['eaten_mean']:.2f} "
                     f"| {t['found_food']:.0%} | {g['climbed_fraction']:.0%} "
                     f"| {r['flat_curvature_deg_mm']:.1f} |")  # fmt: skip
    lines += ["", "## Food eaten: real vs controls", "",
              "| comparison | real seeds | n real / n control | mean real | mean control "
              "| difference (95% CI) | p (exact) | p (Holm) |", "|---|---|---|---|---|---|---|---|"]  # fmt: skip
    tests = []
    for seeds, label in [((0, 1), "0-1 (matched)"), (None, "all")]:
        for ctrl in ("rewired", "random"):
            a, b = sample("real", eaten, seeds), sample(ctrl, eaten)
            if not all(len(b[s]) for s in b) or not all(len(a[s]) for s in a):
                continue
            diff, p, _ = stratified_permutation(a, b)
            lo, hi = bootstrap_ci(a, b)
            na, nb = sum(map(len, a.values())), sum(map(len, b.values()))
            tests.append([f"real vs {ctrl}", label, f"{na} / {nb}",
                          np.mean(np.concatenate(list(a.values()))),
                          np.mean(np.concatenate(list(b.values()))), diff, lo, hi, p])  # fmt: skip
    for t, ph in zip(tests, holm([t[-1] for t in tests]), strict=True):
        lines.append(f"| {t[0]} | {t[1]} | {t[2]} | {t[3]:.2f} | {t[4]:.2f} "
                     f"| {t[5]:+.2f} ({t[6]:+.2f} to {t[7]:+.2f}) | {t[8]:.3f} | {ph:.3f} |")  # fmt: skip
    (OUT / "REPORT.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
