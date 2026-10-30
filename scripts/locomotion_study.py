"""Locomotion study: can each graph learn to crawl forward? (milestone 4)

    uv run python scripts/locomotion_study.py [--seeds 3] [--generations 100] [--workers 4]

Conditions (real, rewired, random) x seeds x glutamate sign, all with the same
trainable parameters and budget. Runs in parallel, one process per run, and skips
runs whose results already exist. Writes reports/locomotion_study/:
runs/*.json, summary.md, summary.json, curves.png.
"""

from __future__ import annotations

import argparse
import itertools
import json
import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

OUT = Path("reports/locomotion_study")


def run_one(job):
    condition, seed, glutamate, generations = job
    from wormbrain.locomotion import train_locomotion

    path = OUT / "runs" / f"{condition}_glu-{glutamate}_seed{seed}.json"
    if path.exists():
        return json.loads(path.read_text())
    res = train_locomotion(condition, seed, glutamate, True, generations)
    path.write_text(json.dumps(res))
    print(f"done {path.name}: {res['forward_speed_mm_s']:.3f} mm/s in {res['seconds']:.0f}s",
          flush=True)  # fmt: skip
    return res


def regait(result):
    """Recompute gait measures from the saved best parameters (deterministic)."""
    import numpy as np

    from wormbrain.locomotion import evaluate, setup

    brain, body, _ = setup(result["condition"], result["seed"], result["glutamate"],
                           result["adaptation"])  # fmt: skip
    _, _, gait = evaluate(brain, body, np.array(result["best_x"]))
    return {k: v for k, v in result.items() if k != "wave_lag_s"} | gait


def summarise(results, conditions, glutamates):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    rows, table = [], {}
    fig, axes = plt.subplots(1, len(glutamates), figsize=(6 * len(glutamates), 4), sharey=True)
    for ax, glu in zip(np.atleast_1d(axes), glutamates, strict=True):
        for k, cond in enumerate(conditions):
            rs = [r for r in results if r["condition"] == cond and r["glutamate"] == glu]
            speed = np.array([r["forward_speed_mm_s"] for r in rs])
            wave = np.array([r["wave_direction"] for r in rs])
            hz = np.array([r["undulation_hz"] for r in rs])
            table[(cond, glu)] = speed
            rows.append(
                f"| {cond} | {glu} | {len(rs)} | {speed.mean():.3f} ± {speed.std(ddof=1):.3f} "
                f"| {', '.join(f'{s:.3f}' for s in speed)} "
                f"| {(speed > 0.05).sum()}/{len(rs)} "
                f"| {', '.join(f'{x:+.2f}' for x in wave)} "
                f"| {', '.join(f'{x:.2f}' for x in hz)} |"
            )
            curves = np.array([r["curve"] for r in rs])
            x = np.arange(1, curves.shape[1] + 1) * rs[0]["popsize"]
            ax.plot(x, curves.mean(0), color=f"C{k}", label=cond)
            ax.fill_between(x, curves.min(0), curves.max(0), color=f"C{k}", alpha=0.15)
        ax.axhline(0.175, color="k", ls=":", label="hand-coded wave")
        ax.set_title(f"glutamate {glu}")
        ax.set_xlabel("evaluations")
    np.atleast_1d(axes)[0].set_ylabel("best forward speed so far (mm/s)")
    np.atleast_1d(axes)[0].legend(frameon=False)
    fig.tight_layout()
    fig.savefig(OUT / "curves.png", dpi=120)

    r0 = results[0]
    lines = [
        "# Locomotion study",
        "",
        f"Task: crawl forward on a flat field for 30 s; fitness = mean forward speed after 5 s. "
        f"CMA-ES, population {r0['popsize']}, {r0['generations']} generations, "
        f"{r0['n_params']} trained parameters in every condition (adaptation on).",
        "Shaded bands in curves.png span the best and worst seed.",
        "",
        "| graph | glutamate | seeds | speed mean ± SD (mm/s) | per seed | crawling (> 0.05) "
        "| wave direction per seed (+1 head-to-tail) | undulation per seed (Hz) |",
        "|---|---|---|---|---|---|---|---|",
        *rows,
        "",
        "Hand-coded wave for reference: 0.175 mm/s.",
        "",
        "![learning curves](curves.png)",
        "",
    ]
    (OUT / "summary.md").write_text("\n".join(lines))
    (OUT / "summary.json").write_text(json.dumps(
        [{k: v for k, v in r.items() if k != "best_x"} for r in results], indent=1))  # fmt: skip
    print("\n".join(lines))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--seeds", type=int, default=3)
    p.add_argument("--generations", type=int, default=100)
    p.add_argument("--workers", type=int, default=os.cpu_count())
    p.add_argument("--conditions", nargs="+", default=["real", "rewired", "random"])
    p.add_argument("--glutamate", nargs="+", default=["excitatory", "inhibitory"])
    args = p.parse_args()

    for var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ[var] = "1"  # one core per run; parallelism comes from the processes
    (OUT / "runs").mkdir(parents=True, exist_ok=True)
    jobs = list(itertools.product(args.conditions, range(args.seeds), args.glutamate,
                                  [args.generations]))  # fmt: skip
    with ProcessPoolExecutor(args.workers) as pool:
        results = list(pool.map(run_one, jobs))
        results = list(pool.map(regait, results))
    summarise(results, args.conditions, args.glutamate)


if __name__ == "__main__":
    main()
