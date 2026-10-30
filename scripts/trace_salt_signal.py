"""Trace the salt signal through trained pilot brains (milestone 5 diagnosis).

    uv run python scripts/trace_salt_signal.py > reports/chemotaxis_pilot/signal_trace.txt

Clamps ASEL on and prints, for neurons along the salt pathway, membrane value and
transmitter release with and without the signal, plus their trained gain and bias.
"""

import json

import numpy as np

from wormbrain.brain import BrainController, _sigmoid
from wormbrain.env import run_episode
from wormbrain.locomotion import FLAT, setup

PATH = ["ASEL", "ASER", "AIYL", "AIYR", "AIBL", "AIZL", "AIAL", "RIAL", "RIBL", "SMDDL",
        "SMDVL", "RMDDL", "RMDVL", "AVBL", "AVAL", "VB5", "DB3"]  # fmt: skip


class Clamp(BrainController):
    def __init__(self, brain, x, on):
        super().__init__(brain, x, record_every=1)
        self.on = on

    def sensory_input(self, obs, dt):
        inp = super().sensory_input(obs, dt)
        inp[:, self.brain.on_idx] += self.on
        return inp


for r in json.load(open("reports/chemotaxis_pilot/results.json"))[1:2] + json.load(
    open("reports/chemotaxis_pilot/results.json"))[3:4]:  # fmt: skip
    # the pilot brains were trained before parameter bounds existed
    brain, body, _ = setup(r["condition"], r["seed"], r["glutamate"], True,
                           r.get("bounded", False), r.get("activation", "sigmoid"))  # fmt: skip
    x = np.array(r["x"])
    outs = []
    for on in (0.0, 3.0):
        c = Clamp(brain, x, on)
        run_episode(c, FLAT, np.zeros((1, 2)), np.zeros(1), duration=20, dt=0.02, body=body)
        v = np.array(c.activity)[500:, 0]
        outs.append((v.mean(0), _sigmoid(c.p["gain"][0] * v).mean(0)))
    p = brain.decode(x[None])
    idx = brain.conn.index(PATH)
    print(f"\n{r['run']}: salt_on gain {p['salt_on'][0, 0]:.1f}, g_chem {p['g_chem'][0, 0]:.2f}")
    print(
        f"{'neuron':8s} {'v base':>8s} {'v ASEL on':>10s} {'release base':>13s} "
        f"{'release on':>11s} {'gain':>6s} {'bias':>6s}"
    )
    for name, k in zip(PATH, idx, strict=True):
        print(
            f"{name:8s} {outs[0][0][k]:+8.3f} {outs[1][0][k]:+10.3f} {outs[0][1][k]:13.3f} "
            f"{outs[1][1][k]:11.3f} {p['gain'][0, k]:6.2f} {p['bias'][0, k]:+6.2f}"
        )
    changed = np.abs(outs[1][1] - outs[0][1]) > 0.01
    print("neurons whose release changes by > 0.01:", int(changed.sum()), "of", brain.n)
