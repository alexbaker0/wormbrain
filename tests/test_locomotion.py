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
