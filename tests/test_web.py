"""The JavaScript simulation (web/sim.js) must match Python step for step."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from wormbrain.brain import convert_params
from wormbrain.chemotaxis import env_config, load_run_config
from wormbrain.export import build_brain, export_model, reference_run

RUNS = Path("reports/comparison/runs")
CASES = [
    ("real_glu-inhibitory_seed0", ()),
    ("random_glu-inhibitory_seed0", ()),
    ("real_glu-inhibitory_seed0", ("ASEL", "ASER")),  # lesions too
    ("real_glu-inhibitory_seed0", "dv"),  # back/belly offset and tied D/V classes
    ("real_glu-inhibitory_seed0", "head"),  # ... plus head proprioception
]


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
@pytest.mark.parametrize(("run_name", "lesion"), CASES)
def test_python_and_javascript_agree(tmp_path, run_name, lesion):
    run = json.loads((RUNS / f"{run_name}.json").read_text())
    if lesion in ("dv", "head"):
        new = run | {"muscle_dv": True, "dv_tie": True, "head_proprio": lesion == "head"}
        dst = build_brain(new)
        x = convert_params(build_brain(run), dst, run["x"])
        x[dst.spec.slices["muscle_dv"]] = -0.6  # a clearly non-zero offset
        if lesion == "head":
            x[dst.spec.slices["head_proprio_gain"]] = 0.8
        run, lesion = new | {"x": x.tolist()}, ()
    cfg = load_run_config("configs/chemotaxis.yaml")
    env = env_config(cfg["env"], cfg["env_overrides"])
    field = {"type": "gaussian", "peak": [0.0, 0.0], "sigma": 4.0, "amplitude": 1.0}
    head, heading, steps, dt = [3.0, -1.5], 2.0, 1500, 0.02  # 30 s of simulated time
    ref = {
        "field": field, "lesion": list(lesion), "head0": head, "heading0": heading,
        "steps": steps, "dt": dt,
        "out": reference_run(run, env["body"], field, head, heading, steps, dt, lesion),
    }  # fmt: skip
    model_path, ref_path = tmp_path / "model.json", tmp_path / "ref.json"
    model_path.write_text(json.dumps(export_model(run, run_name, env["body"])))
    ref_path.write_text(json.dumps(ref))
    res = subprocess.run(["node", "web/agree.mjs", str(model_path), str(ref_path)],
                         capture_output=True, text=True, check=True)  # fmt: skip
    err = json.loads(res.stdout)
    assert err["checked"] == steps // 50
    # agreement to rounding error (measured about 1e-12 over 120 s)
    for key in ("head", "theta0", "kappa", "v"):
        assert err[key] < 1e-9, err


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_python_and_javascript_agree_in_the_patch_world(tmp_path):
    """The best curriculum brain (offset, tied classes, head proprioception) eating patches,
    across the wrap-around edge."""
    run = json.loads(Path("reports/curr_sym_patch/runs/real_glu-excitatory_seed0.json").read_text())
    cfg = load_run_config("configs/chemotaxis.yaml")
    env = env_config(cfg["env"], cfg["env_overrides"])
    field = {"type": "patches", "half_size": 5.0, "sigma": 1.5, "capacity": 1.0,
             "eat_radius": 1.0, "eat_rate": 0.03, "periodic": True,
             "xy": [[-4.6, 0.4], [1.0, 3.0], [2.5, -3.5]]}  # fmt: skip
    head, heading, steps, dt = [-3.8, 0.2], 3.0, 2500, 0.02
    out = reference_run(run, env["body"], field, head, heading, steps, dt)
    ref = {"field": field, "lesion": [], "head0": head, "heading0": heading, "steps": steps,
           "dt": dt, "out": out}  # fmt: skip
    assert ref["out"]["eaten"][-1] > 0  # the test is only useful if the worm eats
    model_path, ref_path = tmp_path / "model.json", tmp_path / "ref.json"
    model_path.write_text(json.dumps(export_model(run, "patch", env["body"])))
    ref_path.write_text(json.dumps(ref))
    res = subprocess.run(["node", "web/agree.mjs", str(model_path), str(ref_path)],
                         capture_output=True, text=True, check=True)  # fmt: skip
    err = json.loads(res.stdout)
    for key in ("head", "theta0", "kappa", "v", "eaten"):
        assert err[key] < 1e-9, err
