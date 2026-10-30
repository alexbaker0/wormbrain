import numpy as np
import pytest

from wormbrain.controllers import GradientSteering, TravelingWave
from wormbrain.env import (
    Field,
    load_env_config,
    path_speed,
    reward,
    run_episode,
    start_positions,
)

FIELDS = [
    {"type": "gaussian", "peak": [1.0, -2.0], "sigma": 3.0},
    {"type": "peaks", "peaks": [{"xy": [0, 0], "sigma": 4}, {"xy": [6, 2], "amplitude": 0.5}]},
    {"type": "linear", "direction_deg": 30.0, "slope": 0.2},
]  # fmt: skip


@pytest.mark.parametrize("cfg", FIELDS)
def test_gradient_matches_finite_differences(cfg):
    f = Field(cfg)
    pos = np.random.default_rng(0).uniform(-6, 6, (20, 2))
    h = 1e-5
    num = np.stack(
        [(f.conc(pos + h * e) - f.conc(pos - h * e)) / (2 * h) for e in np.eye(2)], axis=-1
    )
    np.testing.assert_allclose(f.grad(pos), num, atol=1e-7)


def test_gaussian_peak_and_move():
    f = Field(FIELDS[0])
    assert f.conc(np.array([1.0, -2.0])) == pytest.approx(1.0)
    assert f.conc(np.array([4.0, 2.0])) < 1.0
    f.move_peak([5.0, 5.0])
    assert f.conc(np.array([5.0, 5.0])) == pytest.approx(1.0)
    np.testing.assert_allclose(f.center, [5.0, 5.0])


def test_start_positions_in_range_and_deterministic():
    f = Field(FIELDS[0])
    head, heading = start_positions({"distance": [4, 6]}, f, 200, seed=7)
    r = np.linalg.norm(head - f.center, axis=1)
    assert r.min() >= 4 and r.max() <= 6
    h2, hd2 = start_positions({"distance": [4, 6]}, f, 200, seed=7)
    np.testing.assert_array_equal(head, h2)
    np.testing.assert_array_equal(heading, hd2)
    h3, _ = start_positions({"distance": [4, 6]}, f, 200, seed=8)
    assert not np.array_equal(head, h3)


def test_config_merge():
    cfg = load_env_config("configs/env.yaml", "configs/env_linear.yaml")
    assert cfg["field"] == {"type": "linear", "direction_deg": 0.0, "slope": 0.1, "offset": 2.0}
    assert cfg["body"]["n_segments"] == 16 and cfg["episode"]["duration"] == 120.0


def test_reward_prefers_steering_over_blind_crawling():
    f = Field({"type": "gaussian", "sigma": 4.0})
    head, heading = start_positions({"distance": [4, 6]}, f, 16, seed=0)
    blind = run_episode(TravelingWave(), f, head, heading, duration=60.0)
    steer = run_episode(GradientSteering(), f, head, heading, duration=60.0)
    assert reward(steer, f).mean() > reward(blind, f).mean() + 0.2
    assert (
        reward(steer, f, {"type": "final_distance"}).mean()
        > reward(blind, f, {"type": "final_distance"}).mean()
    )
    penalised = reward(steer, f, {"energy_weight": 1.0})
    assert np.all(penalised < reward(steer, f))


def test_idle_penalty_punishes_stopping_but_not_crawling():
    f = Field({"type": "gaussian", "sigma": 4.0})
    head, heading = start_positions({"distance": [4, 6]}, f, 4, seed=1)
    still = run_episode(TravelingWave(amplitude=0.0), f, head, heading, duration=20.0)
    crawl = run_episode(TravelingWave(), f, head, heading, duration=20.0)
    cfg = {"min_speed": 0.1, "idle_penalty": 0.5}
    np.testing.assert_allclose(reward(still, f, cfg) - reward(still, f), -0.5)
    np.testing.assert_allclose(reward(crawl, f, cfg), reward(crawl, f))  # 0.17 mm/s > 0.1
    assert np.all(path_speed(crawl) > 0.15) and np.all(path_speed(still) < 1e-9)
