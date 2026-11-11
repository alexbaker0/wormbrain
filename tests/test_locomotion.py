import numpy as np
import pytest

from wormbrain.controllers import TravelingWave
from wormbrain.env import run_episode
from wormbrain.locomotion import FLAT, KappaRecorder, undulation_frequency, wave_direction


def curvature(**wave):
    rec = KappaRecorder(TravelingWave(**wave))
    run_episode(rec, FLAT, np.zeros((1, 2)), np.zeros(1), duration=20.0)
    return np.array(rec.kappa)[500:, 0]


@pytest.mark.parametrize("frequency", [0.4, 1.8])
def test_gait_measures_on_known_waves(frequency):
    fwd = curvature(frequency=frequency)
    back = curvature(frequency=frequency, direction=-1)
    assert wave_direction(fwd) > 0.8
    assert wave_direction(back) < -0.8
    assert undulation_frequency(fwd) == pytest.approx(frequency, abs=0.06)


def test_frozen_posture_has_no_direction():
    still = curvature(amplitude=0.0, bias=0.5)
    assert abs(wave_direction(still)) < 1e-6


def test_gait_fitness_prefers_a_straight_head_first_crawl_at_the_target_speed():
    from wormbrain.controllers import TravelingWave
    from wormbrain.env import run_episode
    from wormbrain.locomotion import FLAT, gait_fitness

    def score(**kw):
        ep = run_episode(TravelingWave(**kw), FLAT, np.zeros((1, 2)), np.zeros(1), duration=40.0,
                         dt=0.02)  # fmt: skip
        return gait_fitness(ep, 0.2)[0]

    straight, circling, backward, fast = (score(), score(bias=0.3), score(direction=-1),
                                          score(frequency=1.2))  # fmt: skip
    assert straight > 0.8  # the hand-coded 0.4 Hz wave crawls at about 0.18 mm/s
    assert straight > circling and straight > fast
    assert backward < 0 < straight
