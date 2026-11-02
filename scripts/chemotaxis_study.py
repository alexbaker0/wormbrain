"""Train and test chemotaxis for graph conditions x seeds x glutamate sign.

    uv run python scripts/chemotaxis_study.py --conditions real --seeds 2 \\
        [--glutamate excitatory inhibitory] [--config configs/chemotaxis.yaml] [--workers 4]

Each run lives in runs/chemotaxis/<condition>_glu-<sign>_seed<k>/ (stages are
checkpointed, so an interrupted study resumes). Summaries, learning curves and the
trained parameters go to reports/<--out>/ (default reports/chemotaxis).
"""

from __future__ import annotations

import argparse
import itertools
import json
import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

RUNS = Path("runs/chemotaxis")


def run_one(job):
    config, condition, glutamate, seed, report = job
    from wormbrain.chemotaxis import load_run_config, run_name, train_and_evaluate

    cfg = load_run_config(config, condition=condition, glutamate=glutamate, seed=seed)
    stem = Path(config).stem  # milestone-6 runs (chemotaxis.yaml) live directly in RUNS
    out = (RUNS if stem == "chemotaxis" else RUNS / stem) / run_name(cfg)
    copy = Path(report) / "runs" / f"{run_name(cfg)}.json"
    copy.parent.mkdir(parents=True, exist_ok=True)
    if (out / "result.json").exists():
        res = json.loads((out / "result.json").read_text())
        copy.write_text(json.dumps(res))
        return res
    res = train_and_evaluate(cfg, out)
    copy.write_text(json.dumps(res))  # each finished run lands in the report at once
    g = res["test"]["gaussian"]["brain"]
    print(f"done {res['run']}: test reward {g['reward_mean']:+.3f}, "
          f"reached {g['reached_1mm']:.0%}, {res['stage2_seconds']:.0f}s", flush=True)  # fmt: skip
    return res


def summarise(results, out: Path):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    arenas = list(results[0]["test"])
    groups = sorted({(r["condition"], r["glutamate"]) for r in results})
    lines = ["# Chemotaxis results", "",
             "Test set: 32 fixed starts per arena, never used in training. Reward = "
             "mean concentration over the second half minus the start (fraction of peak), "
             "minus 0.05 x mean power, minus 0.5 x max(0, 1 - path speed / 0.1 mm/s). "
             "'Concentration gain' leaves out both penalties. "
             "'reached' = ends within 1 mm of the main peak.", ""]  # fmt: skip
    for arena in arenas:
        lines += [f"## {arena}", "",
                  "| graph | glutamate | seeds | reward per seed | reward mean | "
                  "concentration gain | reached 1 mm | crawl speed after stage 1 (mm/s) |",
                  "|---|---|---|---|---|---|---|---|"]  # fmt: skip
        for cond, glu in groups:
            rs = [r for r in results if (r["condition"], r["glutamate"]) == (cond, glu)]
            t = [r["test"][arena]["brain"] for r in rs]
            rew = np.array([m["reward_mean"] for m in t])
            reached = [m.get("reached_1mm", float("nan")) for m in t]
            speeds = ", ".join(f"{r['stage1_speed_mm_s']:.2f}" for r in rs)
            lines.append(
                f"| {cond} | {glu} | {len(rs)} | {', '.join(f'{x:+.3f}' for x in rew)} "
                f"| {rew.mean():+.3f} | {np.mean([m['conc_gain_mean'] for m in t]):+.3f} "
                f"| {np.nanmean(reached):.0%} "
                f"| {speeds} |"
            )
        base = results[0]["test"][arena]
        for name in ("blind_crawling", "gradient_steering"):
            m = base[name]
            lines.append(f"| *{name.replace('_', ' ')}* | — | — | — | {m['reward_mean']:+.3f} "
                         f"| {m['conc_gain_mean']:+.3f} | {m.get('reached_1mm', float('nan')):.0%} "
                         f"| — |")  # fmt: skip
        lines.append("")
    lines += ["![learning curves](curves.png)", ""]

    fig, ax = plt.subplots(figsize=(7, 4))
    for k, (cond, glu) in enumerate(groups):
        for r in (r for r in results if (r["condition"], r["glutamate"]) == (cond, glu)):
            ax.plot(np.maximum.accumulate(r["curve"]), color=f"C{k}", alpha=0.8,
                    label=f"{cond}, glutamate {glu}")  # fmt: skip
    h, lab = ax.get_legend_handles_labels()
    keep = {lb: hd for hd, lb in zip(h, lab, strict=True)}
    ax.legend(keep.values(), keep.keys(), frameon=False, fontsize=8)
    ax.set_xlabel("stage-2 generation")
    ax.set_ylabel("best training reward so far")
    fig.tight_layout()
    out.mkdir(parents=True, exist_ok=True)
    fig.savefig(out / "curves.png", dpi=120)
    (out / "summary.md").write_text("\n".join(lines))
    (out / "results.json").write_text(json.dumps(results))
    print("\n".join(lines))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config", default="configs/chemotaxis.yaml")
    p.add_argument("--conditions", nargs="+", default=["real"])
    p.add_argument("--glutamate", nargs="+", default=["excitatory", "inhibitory"])
    p.add_argument("--seeds", type=int, default=2)
    p.add_argument("--workers", type=int, default=os.cpu_count())
    p.add_argument("--out", default="reports/chemotaxis")
    p.add_argument("--skip", nargs="*", default=[], help="run names to leave out")
    args = p.parse_args()

    for var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ[var] = "1"
    # seed by seed across graphs, so an interrupted study leaves balanced results
    order = itertools.product(range(args.seeds), args.conditions, args.glutamate)
    jobs = [(args.config, c, g, s, args.out) for s, c, g in order
            if f"{c}_glu-{g}_seed{s}" not in args.skip]  # fmt: skip
    with ProcessPoolExecutor(args.workers) as pool:
        results = list(pool.map(run_one, jobs))
    summarise(results, Path(args.out))


if __name__ == "__main__":
    main()
