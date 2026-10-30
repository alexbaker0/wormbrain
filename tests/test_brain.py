import numpy as np
import pytest

from wormbrain.brain import Brain, BrainConfig, BrainController
from wormbrain.controls import make_condition
from wormbrain.env import Field, run_episode

FLAT = Field({"type": "linear", "slope": 0.0, "offset": 1.0})


@pytest.fixture(scope="module")
def brain(conn):
    return Brain(conn)


def obs(n, n_joints=15, conc=1.0, t=0.0):
    return {"t": t, "conc": np.full(n, conc), "kappa": np.zeros((n, n_joints))}


def test_parameter_count_is_the_same_for_every_condition(conn, brain):
    assert brain.n_params == 4 * 104 + 9  # tau, bias, gain, adaptation per class + globals
    assert Brain(conn, BrainConfig(adaptation=False)).n_params == 3 * 104 + 8
    for c in ("rewired", "random", "sign_shuffled", "weight_shuffled"):
        assert Brain(make_condition(conn, c, seed=0)).n_params == brain.n_params


def test_normalised_wiring(brain, conn):
    has_input = (conn.chem > 0).any(0)
    np.testing.assert_allclose(np.abs(brain.W).sum(0)[has_input], 1.0)
    has_gap = (conn.gap > 0).any(0)
    np.testing.assert_allclose(brain.gap_self[has_gap], 1.0)
    # every muscle with any input gets inputs summing to 1 in magnitude
    total = np.abs(brain.R).sum(0)
    assert np.all((total == 0) | np.isclose(total, 1.0))


def test_gaba_motor_neurons_relax_muscle(brain, conn):
    dd = conn.index(["DD3"])[0]
    assert brain.R[dd].min() < 0 and brain.R[dd].max() == 0
    vb = conn.index(["VB5"])[0]
    assert brain.R[vb].min() == 0 and brain.R[vb].max() > 0


def test_proprioceptive_neurons_and_positions(brain, conn):
    names = [conn.neurons[k] for k in brain.prop_idx]
    assert sorted({n[:2] for n in names}) == ["DB", "VB"] and len(names) == 18
    pos = dict(zip(names, brain.prop_pos, strict=True))
    assert pos["VB1"] < pos["VB5"] < pos["VB11"]  # ordered head to tail


@pytest.mark.parametrize("adaptation", [False, True])
def test_bounded_and_stable_for_extreme_parameters(conn, adaptation):
    brain = Brain(conn, BrainConfig(adaptation=adaptation))
    rng = np.random.default_rng(0)
    x = brain.spec.x0() + rng.normal(0, 4.0, (16, brain.n_params))
    ctrl = BrainController(brain, x, record_every=1)
    ctrl.reset(16)
    for k in range(2000):
        o = obs(16, conc=1.0 + 0.5 * np.sin(k / 50), t=k * 0.01)
        o["kappa"] = rng.normal(0, 8, (16, 15))
        m = ctrl.step(o, dt=0.05)  # five times the usual step
    v = np.array(ctrl.activity)
    assert np.isfinite(v).all()
    p = brain.decode(x)
    bound = np.abs(p["bias"]) + p["g_chem"] + 100 * (p["salt_on"] + p["salt_off"])
    bound += np.abs(p["proprio_gain"]) * 10
    if adaptation:  # the adaptation current can overshoot by at most its own strength
        bound = bound * (1 + p["adapt"])
    assert np.all(np.abs(v).max(0) <= bound + 1e-9)
    assert m.shape == (16, 4, 24) and m.min() >= 0 and m.max() <= 1


def test_small_step_converges(brain):
    """Halving dt changes the trajectory by a small amount (first-order scheme)."""
    x = brain.spec.x0() + np.random.default_rng(1).normal(0, 0.5, brain.n_params)

    def run(dt):
        ctrl = BrainController(brain, x)
        ctrl.reset(1)
        for k in range(int(round(2.0 / dt))):
            ctrl.step(obs(1, conc=1.0 + 0.2 * np.sin(2 * k * dt), t=k * dt), dt)
        return ctrl.v

    v1, v2, v3 = run(0.01), run(0.005), run(0.0025)
    assert np.abs(v1 - v3).max() < 2 * np.abs(v1).max() * 0.05
    assert np.abs(v2 - v3).max() < np.abs(v1 - v3).max()


def test_salt_sensors_respond_to_changes_with_the_right_sign(brain, conn):
    x = brain.spec.x0()
    ase = conn.index(["ASEL", "ASER"])
    for step, expect in [(+0.5, (1, 0)), (-0.5, (0, 1))]:
        ctrl = BrainController(brain, x)
        ctrl.reset(1)
        ctrl.sensory_input(obs(1, conc=1.0), 0.01)
        inp = ctrl.sensory_input(obs(1, conc=1.0 + step), 0.01)[0, ase]
        assert (inp > 0).tolist() == [bool(e) for e in expect]
    # adaptation: a constant concentration gives no input after a while
    ctrl = BrainController(brain, x)
    ctrl.reset(1)
    for _ in range(3000):
        inp = ctrl.sensory_input(obs(1, conc=2.0), 0.01)
    assert np.abs(inp[0, ase]).max() < 1e-9


def test_adaptation_opposes_sustained_input(conn):
    """A constant drive gives a peak, then the response sags as adaptation builds up."""
    x = Brain(conn).spec.x0()
    brain = Brain(conn)
    ctrl = BrainController(brain, x)
    ctrl.reset(1)
    ase = conn.index(["ASEL"])[0]
    ctrl.p["bias"] = ctrl.p["bias"].copy()
    ctrl.p["bias"][:, ase] += 2.0
    trace = []
    for k in range(1000):
        ctrl.step(obs(1, t=k * 0.01), 0.01)
        trace.append(ctrl.v[0, ase])
    trace = np.array(trace)
    assert trace.max() > trace[-1] + 0.1  # sag
    assert ctrl.a[0, ase] > 0
    no_adapt = BrainController(Brain(conn, BrainConfig(adaptation=False)),
                               Brain(conn, BrainConfig(adaptation=False)).spec.x0())  # fmt: skip
    no_adapt.reset(1)
    no_adapt.p["bias"] = no_adapt.p["bias"].copy()
    no_adapt.p["bias"][:, ase] += 2.0
    for k in range(1000):
        no_adapt.step(obs(1, t=k * 0.01), 0.01)
    assert no_adapt.v[0, ase] > trace[-1]


def test_lesion_silences_neuron(conn):
    lesioned = Brain(conn, BrainConfig(lesion=("AIZL", "AIZR")))
    x = lesioned.spec.x0() + np.random.default_rng(2).normal(0, 1.0, lesioned.n_params)
    ctrl = BrainController(lesioned, x)
    run_episode(ctrl, FLAT, np.zeros((1, 2)), np.zeros(1), duration=2.0)
    aiz = conn.index(["AIZL", "AIZR"])
    assert np.all(ctrl.v[:, aiz] == 0)
    assert np.all(lesioned.W[aiz] == 0) and np.all(lesioned.M[aiz] == 0)


def test_brain_episode_deterministic_and_batch_consistent(brain):
    x = brain.spec.x0() + np.random.default_rng(3).normal(0, 1.0, (3, brain.n_params))

    def run(xs):
        n = len(xs)
        return run_episode(BrainController(brain, xs), FLAT, np.zeros((n, 2)), np.zeros(n),
                           duration=5.0).centroid  # fmt: skip

    both = run(x)
    np.testing.assert_array_equal(both, run(x))
    np.testing.assert_allclose(both[:, 1], run(x[1:2])[:, 0], atol=1e-12)


def test_bounded_parameters_stay_in_range(conn):
    from wormbrain.brain import BOUNDS

    brain = Brain(conn)
    rng = np.random.default_rng(4)
    x = rng.normal(0, 50.0, (64, brain.n_params))  # far outside any sensible range
    p = brain.decode(x)
    for key, (lo, hi) in [("gain", BOUNDS["gain"]), ("g_chem", BOUNDS["g_chem"]),
                          ("g_gap", BOUNDS["g_gap"]), ("adapt", BOUNDS["adapt"]),
                          ("salt_on", BOUNDS["salt_gain"])]:  # fmt: skip
        assert p[key].min() >= lo - 1e-12 and p[key].max() <= hi + 1e-12, key
    assert np.abs(p["bias"]).max() <= BOUNDS["bias"]
    # the starting point decodes to (nearly) the old starting values
    p0 = brain.decode(brain.spec.x0())
    assert p0["g_chem"][0, 0] == pytest.approx(np.sqrt(0.9))
    assert p0["salt_on"][0, 0] == pytest.approx(20.0)
    assert p0["adapt"][0, 0] == pytest.approx(0.5)


def test_unbounded_model_still_available(conn):
    brain = Brain(conn, BrainConfig(bounded=False))
    x = brain.spec.x0()
    x[brain.spec.slices["g_chem"]] = np.log(0.01)
    assert brain.decode(x)["g_chem"][0, 0] == pytest.approx(0.01)
