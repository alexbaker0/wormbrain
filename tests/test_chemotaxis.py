import json

import numpy as np

from wormbrain.chemotaxis import (
    batch_rewards,
    env_config,
    load_run_config,
    train_and_evaluate,
)
from wormbrain.env import Field, start_positions
from wormbrain.locomotion import setup


def tiny_config(**over):
    cfg = load_run_config("configs/chemotaxis.yaml", seed=99, **over)
    cfg["env_overrides"]["episode"] = {"duration": 3.0, "dt": 0.01}
    cfg["stage1"] = {"generations": 1, "popsize": 4, "sigma0": 0.5}
    cfg["stage2"] = {"generations": 2, "popsize": 4, "sigma0": 0.3, "n_starts": 2}
    cfg["evaluation"]["n_starts"] = 3
    for arena in cfg["evaluation"]["arenas"].values():
        arena.setdefault("overrides", {})["episode"] = {"duration": 3.0, "dt": 0.01}
    return cfg


def test_candidates_share_starts_and_scores_are_deterministic():
    cfg = tiny_config()
    brain, body, _ = setup("real", 0)
    env = env_config(cfg["env"], cfg["env_overrides"])
    field = Field(env["field"])
    starts = start_positions(env["start"], field, 2, seed=5)
    x = brain.spec.x0() + np.random.default_rng(0).normal(0, 0.5, (3, brain.n_params))
    a = batch_rewards(brain, body, x, field, env, starts)
    b = batch_rewards(brain, body, x, field, env, starts)
    np.testing.assert_array_equal(a, b)
    # a candidate's score does not depend on who else is in the batch
    alone = batch_rewards(brain, body, x[1:2], field, env, starts)
    np.testing.assert_allclose(a[1], alone[0], atol=1e-12)


def test_tiny_run_trains_checkpoints_and_evaluates(tmp_path):
    cfg = tiny_config()
    res = train_and_evaluate(cfg, tmp_path)
    for f in ("config.yaml", "stage1.json", "stage2.json", "result.json"):
        assert (tmp_path / f).exists()
    assert set(res["test"]) == {"gaussian", "far_start", "two_peaks", "linear"}
    for arena in res["test"].values():
        assert set(arena) == {"brain", "blind_crawling", "gradient_steering"}
        assert np.isfinite(arena["brain"]["reward_mean"])
    assert "reached_1mm" not in res["test"]["linear"]["brain"]
    # resuming reuses the checkpoints and gives the same answer
    again = train_and_evaluate(cfg, tmp_path)
    assert again["x"] == res["x"]
    assert json.loads((tmp_path / "result.json").read_text())["run"] == res["run"]


def test_fine_tuning_starts_from_an_earlier_brain(tmp_path):
    cfg = tiny_config()
    first = train_and_evaluate(cfg, tmp_path / "first")
    src = tmp_path / "earlier"
    src.mkdir()
    (src / f"{first['run']}.json").write_text(json.dumps(first))
    tuned_cfg = tiny_config(init_from=str(src))
    tuned = train_and_evaluate(tuned_cfg, tmp_path / "tuned")
    s1 = json.loads((tmp_path / "tuned" / "stage1.json").read_text())
    assert s1["best_x"] == first["x"] and s1["reused_from"].endswith(f"{first['run']}.json")
    assert np.isfinite(tuned["test"]["gaussian"]["brain"]["reward_mean"])
