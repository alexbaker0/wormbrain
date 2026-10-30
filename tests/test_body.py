import numpy as np
import pytest

from wormbrain.body import Body, BodyParams
from wormbrain.controllers import TravelingWave
from wormbrain.env import Field, run_episode

FIELD = Field({"type": "gaussian"})


def crawl(controller, head=((0.0, 0.0),), heading=(0.0,), duration=20.0, **body):
    return run_episode(
        controller, FIELD, np.array(head), np.array(heading), duration=duration,
        body=Body(BodyParams(**body)),
    )  # fmt: skip


def displacement(ep, t_from=5.0):
    """Centroid displacement after the start-up transient (body bending from straight)."""
    k = np.searchsorted(ep.t, t_from)
    return ep.centroid[-1] - ep.centroid[k]


def test_forces_and_torques_balance():
    body = Body()
    rng = np.random.default_rng(0)
    s = body.reset(np.zeros((4, 2)), rng.uniform(0, 6, 4))
    s.kappa = rng.normal(0, 5, s.kappa.shape)
    _, _, _, force = body.velocities(s, rng.normal(0, 20, s.kappa.shape))
    x = body.nodes(s)
    r = 0.5 * (x[:, 1:] + x[:, :-1]) - s.head[:, None]
    torque = (r[..., 0] * force[..., 1] - r[..., 1] * force[..., 0]).sum(1)
    assert np.abs(force.sum(1)).max() < 1e-12
    assert np.abs(torque).max() < 1e-12
    assert np.abs(force).max() > 0.01  # the test is not vacuous


def test_segment_lengths_fixed():
    body = Body()
    s = body.reset([[1.0, 2.0]], [0.3])
    s.kappa = np.random.default_rng(1).normal(0, 6, s.kappa.shape)
    seg = np.linalg.norm(np.diff(body.nodes(s), axis=1), axis=-1)
    np.testing.assert_allclose(seg, body.ds)


def test_no_activation_no_motion():
    still = TravelingWave(amplitude=0.0)
    ep = crawl(still)
    assert np.abs(ep.head - ep.head[0]).max() < 1e-12


def test_forward_wave_moves_forward_at_plausible_speed():
    ep = crawl(TravelingWave(), heading=(0.0,))
    d = displacement(ep)[0]
    speed = d[0] / 15.0
    assert 0.1 < speed < 0.3  # mm/s; real worms crawl at roughly 0.1-0.3 mm/s on agar
    assert abs(d[1]) < 0.1 * d[0]


def test_reversed_wave_moves_backward():
    ep = crawl(TravelingWave(direction=-1), heading=(0.0,))
    assert displacement(ep)[0, 0] < -1.0


def test_isotropic_drag_gives_no_propulsion():
    # with equal drag in all directions the drag forces summing to zero means the
    # centroid cannot move at all; this also checks the integrator has no drift
    ep = crawl(TravelingWave(), drag_normal=1.0)
    assert np.abs(ep.centroid - ep.centroid[0]).max() < 1e-4  # mm


def test_dorsal_and_ventral_bias_mirror():
    a = crawl(TravelingWave(bias=0.3))
    b = crawl(TravelingWave(amplitude=-1.0, bias=-0.3))  # exact mirror image of a
    np.testing.assert_allclose(a.centroid[..., 0], b.centroid[..., 0], atol=1e-9)
    np.testing.assert_allclose(a.centroid[..., 1], -b.centroid[..., 1], atol=1e-9)
    assert np.abs(a.centroid[:, 0, 1]).max() > 0.5  # it did turn


@pytest.mark.parametrize("angle", [0.7, -2.0])
def test_rotation_invariance(angle):
    a = crawl(TravelingWave(bias=0.1), heading=(0.0,))
    b = crawl(TravelingWave(bias=0.1), heading=(angle,))
    rot = np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])
    np.testing.assert_allclose(a.centroid @ rot.T, b.centroid, atol=1e-9)


def test_batch_matches_single_and_is_deterministic():
    heads, headings = np.array([[0.0, 0.0], [3.0, -1.0]]), np.array([0.5, 2.5])
    both = crawl(TravelingWave(bias=0.2), heads, headings)
    again = crawl(TravelingWave(bias=0.2), heads, headings)
    np.testing.assert_array_equal(both.centroid, again.centroid)
    for k in range(2):
        alone = crawl(TravelingWave(bias=0.2), heads[k : k + 1], headings[k : k + 1])
        np.testing.assert_allclose(both.centroid[:, k], alone.centroid[:, 0], atol=1e-12)
