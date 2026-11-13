import numpy as np
import pytest

from wormbrain.controllers import GradientSteering, TravelingWave
from wormbrain.env import (
    Field,
    load_env_config,
    mean_curvature,
    mean_turning_rate,
    path_speed,
    progress_speed,
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


def test_mean_turning_rate():
    f = Field({"type": "linear", "slope": 0.0, "offset": 1.0})
    straight = run_episode(TravelingWave(), f, np.zeros((1, 2)), np.zeros(1), duration=40.0)
    left = run_episode(TravelingWave(bias=0.2), f, np.zeros((1, 2)), np.zeros(1), duration=40.0)
    right = run_episode(TravelingWave(amplitude=-1.0, bias=-0.2), f, np.zeros((1, 2)),
                        np.zeros(1), duration=40.0)  # fmt: skip
    assert abs(mean_turning_rate(straight)[0]) < 1.0
    assert abs(mean_turning_rate(left)[0]) > 10.0
    np.testing.assert_allclose(mean_turning_rate(left), -mean_turning_rate(right), rtol=1e-6)


def test_curvature_does_not_reward_crawling_slowly():
    """The same circle crawled at half speed has half the turning rate, same curvature."""
    f = Field({"type": "linear", "slope": 0.0, "offset": 1.0})

    def circle(freq):
        return run_episode(TravelingWave(frequency=freq, bias=0.2), f, np.zeros((1, 2)),
                           np.zeros(1), duration=80.0)  # fmt: skip

    fast, slow = circle(0.4), circle(0.2)
    assert mean_turning_rate(slow)[0] == pytest.approx(mean_turning_rate(fast)[0] / 2, rel=0.15)
    assert mean_curvature(slow)[0] == pytest.approx(mean_curvature(fast)[0], rel=0.15)
    straight = run_episode(TravelingWave(), f, np.zeros((1, 2)), np.zeros(1), duration=40.0)
    assert mean_curvature(straight)[0] < 3.0


def test_progress_speed_ignores_wiggling_in_place():
    from wormbrain.body import Body, BodyParams

    f = Field({"type": "linear", "slope": 0.0, "offset": 1.0})
    # with equal drag in all directions the body undulates but goes nowhere
    wiggle = run_episode(TravelingWave(), f, np.zeros((1, 2)), np.zeros(1), duration=30.0,
                         body=Body(BodyParams(drag_normal=1.0)))  # fmt: skip
    crawl = run_episode(TravelingWave(), f, np.zeros((1, 2)), np.zeros(1), duration=30.0)
    assert progress_speed(wiggle)[0] < 0.01
    assert progress_speed(crawl)[0] == pytest.approx(0.17, abs=0.03)


def test_moving_food_and_food_time():
    f = Field({"type": "gaussian", "peak": [0.0, 0.0], "sigma": 4.0})
    head = np.array([[0.2, 0.0]])
    ep = run_episode(TravelingWave(amplitude=0.0), f, head, np.zeros(1), duration=20.0,
                     food_events=[(10.0, [5.0, 5.0])])  # fmt: skip
    assert np.allclose(ep.food[0], [0, 0]) and np.allclose(ep.food[-1], [5, 5])
    np.testing.assert_allclose(f.center, [0, 0])  # field restored afterwards
    eaten = reward(ep, f, {"type": "food_time", "radius": 1.0})
    assert 0.45 < eaten[0] < 0.56  # at the food until it moved half way through


def test_patch_world_eating_depletes_and_smell_fades():
    from wormbrain.env import PatchField

    f = PatchField({"n_patches": 4, "half_size": 10.0, "min_spacing": 5.0, "eat_rate": 0.1})
    patch = f.xy[0].copy()
    head = np.array([patch + [0.2, 0.0]])  # sitting on patch 0
    still = TravelingWave(amplitude=0.0)
    ep = run_episode(still, f, head, np.zeros(1), duration=20.0, dt=0.02)
    assert ep.eaten[-1, 0] == pytest.approx(1.0, abs=1e-6)  # whole patch eaten in 10 s
    assert ep.eaten[50, 0] == pytest.approx(1.0, abs=0.02)  # record every 0.2 s: 10 s in
    assert ep.conc[-1, 0] < 0.05 * ep.conc[0, 0]  # its smell has gone
    assert reward(ep, f, {"type": "eaten"})[0] == pytest.approx(1.0, abs=1e-6)
    # a fresh episode restores the food
    ep2 = run_episode(still, f, head, np.zeros(1), duration=2.0, dt=0.02)
    assert ep2.conc[0, 0] == pytest.approx(ep.conc[0, 0])


def test_patch_world_starts_and_layouts():
    from wormbrain.env import PatchField

    f = PatchField({"n_patches": 16, "half_size": 25.0})
    head, heading = start_positions({"half_size": 15.0, "clearance": 4.0}, f, 50, seed=3)
    layout = f.xy.copy()
    assert np.abs(head).max() <= 15.0
    assert np.min(np.linalg.norm(head[:, None] - layout[None], axis=-1)) >= 4.0
    start_positions({"half_size": 15.0}, f, 5, seed=4)
    assert not np.allclose(f.xy, layout)  # a new seed draws a new arena
    start_positions({"half_size": 15.0}, f, 5, seed=3)
    np.testing.assert_array_equal(f.xy, layout)  # and the same seed the same arena


def test_patch_world_periodic_wraps_smell_and_eating():
    from wormbrain.env import PatchField

    f = PatchField({"n_patches": 1, "half_size": 10.0, "periodic": True, "eat_radius": 1.0})
    f.xy = np.array([[9.5, 0.0]])
    across = np.array([[-9.8, 0.0]])  # 0.7 mm away through the edge
    assert f.conc(np.array([[9.5 - 0.7, 0.0]]))[0] == pytest.approx(f.conc(across)[0])
    f.reset_worms(1)
    assert f.consume(across, 1.0)[0] > 0
    flat = PatchField({"n_patches": 1, "half_size": 10.0, "eat_radius": 1.0})
    flat.xy = f.xy.copy()
    assert flat.conc(across)[0] < 1e-10


def test_forage_world_eats_respawns_and_shares_food_sequences():
    from wormbrain.env import ForageField

    f = ForageField({"sigma": 4.0, "eat_radius": 1.0, "eat_rate": 0.5, "respawn": [5.0, 9.0]})
    head0, heading = f.starts({}, 3, seed=7)
    assert head0.shape == (3, 2) and np.allclose(head0, 0)
    f.reset_worms(6)  # two candidates x three starts
    assert np.allclose(f.xy[:3], f.xy[3:])  # the same worlds for both candidates
    assert np.all((f.d0 >= 5.0) & (f.d0 <= 9.0))
    first = f.xy.copy()
    head = np.zeros((6, 2))
    head[0] = first[0]  # worm 0 sits on its food; the others stay at the origin
    assert f.conc(head)[0] == pytest.approx(1.0)
    eaten = sum(f.consume(head, 0.1) for _ in range(25))  # 2.5 s at 0.5/s: one food and more
    assert f.count[0] == 1 and f.count[1:].sum() == 0
    assert eaten[0] == pytest.approx(1.0, abs=0.06) and eaten[1:].sum() == 0
    assert not np.allclose(f.xy[0], first[0])  # a new food appeared ...
    assert 5.0 <= np.linalg.norm(f.xy[0] - head[0]) <= 9.0  # ... 5-9 mm from the worm
    assert f.closest[0] == 0.0 and np.all(f.closest[1:] == 0.0)
    head[1] = 0.5 * first[1]  # worm 1 goes halfway
    f.consume(head, 0.1)
    assert f.closest[1] == pytest.approx(0.5)
    head[1] = 0.0
    f.consume(head, 0.1)
    assert f.closest[1] == pytest.approx(0.5)  # best approach is kept


def test_forage_reward_has_no_freeze_trap():
    from wormbrain.env import ForageField, reward

    f = ForageField({"sigma": 4.0, "eat_rate": 0.05})
    head, heading = start_positions({}, f, 8, seed=3)
    cfg = {"type": "forage", "approach_weight": 1.0, "energy_weight": 0.2}

    class Frozen:
        def reset(self, n):
            self.n = n

        def step(self, obs, dt):
            return np.full((self.n, 4, 24), 0.5)

    scores = {}
    for name, c in [("frozen", Frozen()), ("blind", TravelingWave())]:
        ep = run_episode(c, f, head, heading, duration=120.0, dt=0.02)
        scores[name] = reward(ep, f, cfg).mean()
    # a frozen worm scores exactly 0 and blind crawling beats it, so stopping dead is
    # never the easy way out before steering has been learned
    assert scores["frozen"] == pytest.approx(0.0, abs=1e-9)
    assert scores["blind"] > 0.05


def test_forage_cone_smell_is_linear_with_random_height():
    from wormbrain.env import ForageField

    cfg = {"type": "forage", "shape": "cone", "reach": 20.0, "steepness": [0.3, 3.0]}
    f = ForageField(cfg)
    f.starts({}, 4, 7)
    f.reset_worms(4)
    assert np.all((f.height >= 0.3) & (f.height <= 3.0)) and np.ptp(f.height) > 0
    at, half = f.conc(f.xy), f.conc(f.xy + np.array([10.0, 0.0]))
    assert np.allclose(at, f.height) and np.allclose(half, f.height / 2)
    assert np.allclose(f.conc(f.xy + np.array([25.0, 0.0])), 0.0)
    g = ForageField({"type": "forage"})  # default stays Gaussian with unit peak
    assert np.allclose(g.conc(g.xy), 1.0)


def test_forage_smell_without_fade_ignores_food_left():
    f = make_field({"type": "forage", "shape": "cone", "reach": 10.0, "fade": False})
    f.starts({}, 2, 0)
    f.reset_worms(2)
    before = f.conc(np.zeros((2, 2)))
    f.left[:] = 0.25 * f.capacity
    assert np.allclose(f.conc(np.zeros((2, 2))), before)
