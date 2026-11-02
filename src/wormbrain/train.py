"""Evolution strategies over brain parameters.

Objectives are batched: ``objective(X)`` takes a (P, D) array of parameter
vectors and returns (P,) fitness values, higher is better, so a whole CMA-ES
population is simulated as one batch of worms.
"""

from __future__ import annotations

import json
import pickle
import time
from collections.abc import Callable
from pathlib import Path

import cma
import numpy as np


def cmaes(
    objective: Callable[[np.ndarray], np.ndarray],
    x0: np.ndarray,
    sigma0: float = 0.5,
    popsize: int = 24,
    generations: int = 100,
    seed: int = 0,
    log_path: str | Path | None = None,
    verbose: bool = True,
    checkpoint: str | Path | None = None,
    on_resume: Callable[[int], None] | None = None,
) -> dict:
    """Maximise ``objective`` with CMA-ES.

    With ``checkpoint``, the optimiser state is saved after every generation and an
    interrupted run continues from it; ``on_resume(next_generation)`` lets the caller
    restore its own per-generation state (e.g. which arenas to draw next).
    """
    es = cma.CMAEvolutionStrategy(
        x0, sigma0, {"popsize": popsize, "seed": seed + 1, "verbose": -9}
    )  # cma treats seed 0 as "random", so offset it
    history, best_x, best_f = [], x0.copy(), -np.inf
    first = 0
    if checkpoint and Path(checkpoint).exists():
        state = pickle.loads(Path(checkpoint).read_bytes())
        es, history, best_x, best_f = (
            state["es"],
            state["history"],
            state["best_x"],
            state["best_f"],
        )
        first = len(history)
        if on_resume:
            on_resume(first)
    start = time.time() - (history[-1]["seconds"] if history else 0.0)
    for gen in range(first, generations):
        X = np.array(es.ask())
        f = np.asarray(objective(X), dtype=float)
        es.tell(list(X), list(-f))
        if f.max() > best_f:
            best_f, best_x = float(f.max()), X[f.argmax()].copy()
        row = {
            "generation": gen,
            "evaluations": (gen + 1) * popsize,
            "best": float(f.max()),
            "mean": float(f.mean()),
            "best_so_far": best_f,
            "sigma": float(es.sigma),
            "seconds": round(time.time() - start, 1),
        }
        history.append(row)
        if verbose:
            print(json.dumps(row), flush=True)
        if log_path:
            Path(log_path).write_text(json.dumps(history))
        if checkpoint:
            tmp = Path(str(checkpoint) + ".tmp")
            state = {"es": es, "history": history, "best_x": best_x, "best_f": best_f}
            tmp.write_bytes(pickle.dumps(state))
            tmp.replace(checkpoint)
    return {"best_x": best_x, "best_f": best_f, "history": history, "mean_x": es.mean.copy()}
