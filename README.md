# wormbrain

Can the *C. elegans* connectome, used as a fixed-wiring neural network, learn to
steer a simulated worm up a chemical gradient? And does the real wiring do better
than rewired or random wiring with exactly the same number of trained parameters?

This project scales down the idea of FlyGM (Jin, Zhu, Zhang & Sui 2026,
[arXiv:2602.17997](https://arxiv.org/abs/2602.17997)), which used the whole fruit-fly
connectome as a fixed graph inside a body controller, to the 302-neuron worm.
Unlike FlyGM it trains with evolution strategies rather than deep RL, and it runs
on a laptop CPU.

**Status: milestone 4 of 8** (the connectome brain drives the body and can learn to
crawl forward). No chemotaxis yet.

## Plan

1. ~~Research data sources and agree the plan~~
2. ~~Connectome loader, sign assignment, control graphs, graph statistics~~
3. ~~2D worm body (resistive force theory) and arena, driven by a hand-coded oscillator~~
4. ~~Graded leaky-integrator brain on the connectome, wired to body and sensors; stability tests~~
5. CMA-ES training on the real connectome until the worm reaches the food
6. Control conditions, multi-seed experiments, `make report`
7. Lesion study compared with published ablations (Iino & Yoshida 2009; Gray et al. 2005)
8. In-browser demo on GitHub Pages

## Design in brief

- **Graph (fixed):** Cook et al. 2019 hermaphrodite chemical synapses and gap
  junctions, 282 non-pharyngeal neurons, with signs from the Wang et al. 2024
  neurotransmitter atlas. See [DATA.md](DATA.md) for every source and assumption.
- **Readout (fixed):** the real neuron→muscle synapses from the same dataset map
  motor neurons onto 95 body-wall muscles, so the readout is biological rather than learned.
- **Brain:** one graded leaky-integrator unit per neuron with a slow adaptation
  current (`src/wormbrain/brain.py`). Inputs: ASEL as a salt ON cell and ASER as an
  OFF cell; VB/DB motor neurons sense body curvature.
- **Trained:** time constant, bias, gain and adaptation strength per neuron class
  (104 classes), plus 9 global values (chemical and gap-junction scales, sensor and
  muscle gains, time constants): 425 parameters, identical for every graph.
- **Controls:** degree-preserving rewiring, an Erdős–Rényi graph, shuffled signs and
  shuffled weights. Only neuron-to-neuron wiring changes; inputs, outputs and the
  parameter count stay identical (`src/wormbrain/controls.py`).
- **Body:** 16 rigid segments on a plane (the worm lies on its side, so dorsal/ventral
  bends are in the plane), moved by resistive force theory with no inertia: each step
  solves for the motion that makes drag force and torque vanish. Muscle activations
  in the connectome's own layout (4 quadrants × 24 rows) set the target curvature
  (`src/wormbrain/body.py`).
- **Arena:** open plane with a Gaussian peak, several peaks or a linear gradient;
  random start 4–6 mm from food, random heading; reward = concentration gained
  (`src/wormbrain/env.py`, `configs/env*.yaml`).

## Setup

```bash
uv sync                     # Python 3.11+, installs cect and the rest
uv run pytest               # tests (first run builds the data cache, ~20 s)
make stats                  # graph statistics -> reports/graph_stats/
make oscillator             # body sanity checks -> reports/oscillator/ (~1 min)
```

## Layout

```
src/wormbrain/   data.py (load + cache) · signs.py · connectome.py · controls.py · graphstats.py
                 body.py · env.py · controllers.py
configs/         YAML configs (connectome.yaml holds every data assumption)
scripts/         command-line entry points
notebooks/       exploratory notebooks
reports/         generated figures and tables
tests/           pytest suite
```

## Graph statistics so far

From [`reports/graph_stats/graph_stats.md`](reports/graph_stats/graph_stats.md):
the real graph has far more reciprocal connections (36% of edges vs 7% after
degree-preserving rewiring) and clustering (0.32 vs 0.15) than its controls. One
caveat for the comparison: in rewired and random graphs nearly every sensory neuron
connects directly to a motor neuron, against 73 of 83 (88%) in the real graph,
which could make the controls *easier* to train on a simple task.

## Body sanity checks

From [`reports/oscillator/oscillator.md`](reports/oscillator/oscillator.md): a
hand-coded head-to-tail bending wave (0.4 Hz) crawls forward at 0.18 mm/s, close to real
worms on agar; reversing the wave reverses the worm; a dorsal or ventral bias turns
it in mirror-image circles. With equal drag in all directions the worm cannot move,
the textbook result for this physics, and the tests check it. A crude hand-coded
steering rule (turn while concentration falls) ends 3.2 mm from food on average versus
20.7 mm for blind crawling, so the reward measures what it should. 32 worms × 120 s
simulate in about 8 s on one CPU core.

## Locomotion: first attempt failed, adaptation added

Before chemotaxis, the brain must make the body crawl. Trained only to crawl forward
(CMA-ES, 200 generations), the first brain model reached 0.009 mm/s, about 5% of the
hand-coded wave: the network settled to fixed states and the body froze in a bent
posture. A wider search, inhibitory glutamate and a random graph all failed the
same way ([`reports/locomotion/`](reports/locomotion/)), so the neuron model, not the
wiring, was the limit. Each neuron now has a slow adaptation current (a standard
mechanism for turning steady states into rhythms), adding 105 parameters. In a
one-seed prototype a random graph then crawled at 0.21 mm/s while the real
connectome still stalled.

## Locomotion study (3 seeds per cell)

From [`reports/locomotion_study/summary.md`](reports/locomotion_study/summary.md),
crawling forward for 30 s, 100 generations of CMA-ES, 425 parameters everywhere:

| graph | glutamate excitatory: crawled / mean speed | glutamate inhibitory: crawled / mean speed |
|---|---|---|
| real | 1/3, 0.04 mm/s | 2/3, 0.20 mm/s |
| rewired | 3/3, 0.27 mm/s | 1/3, 0.13 mm/s |
| random | 3/3, 0.26 mm/s | 1/3, 0.20 mm/s |

- **Go:** the real connectome can learn to crawl, with a head-to-tail bending wave
  (the direction of real forward crawling) in every run that moved.
- With glutamate treated as excitatory (the default) the real wiring learned worse than
  both controls in this small sample; with glutamate inhibitory there is no clear
  difference. The sign assumption matters more for the real graph than for the
  controls, which receive the same signs shuffled.
- Outcomes are close to all-or-nothing per seed (a run either finds a rhythm or
  stalls), so 3 seeds cannot settle anything: the chemotaxis comparison needs more
  seeds and generations.
- Several fast gaits undulate at 1.4–2.3 Hz, faster than real crawling; the body
  model has no energy cost or force limit to stop this.

## Limitations (so far)

- Synapse signs are inferred from transmitter identity; glutamate's sign is a
  global assumption that changes the excitatory:inhibitory ratio from 16:1 to 2:1.
- Connection weights are anatomical, not physiological strengths.
- Neuromodulation (monoamines, neuropeptides) is left out.
- The body's shape is set by the muscles alone (no passive bending from the
  environment), there are no walls, and the agar drag ratio (20) is an assumption;
  only the ratio matters for the motion and it is a config option.
- Left and right muscles in each dorsal/ventral pair act together, since the body is 2D.
- Nothing limits undulation frequency except the muscle time constant; trained gaits
  can be faster than real worms'.
