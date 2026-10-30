# wormbrain

Can the *C. elegans* connectome, used as a fixed-wiring neural network, learn to
steer a simulated worm up a chemical gradient? And does the real wiring do better
than rewired or random wiring with exactly the same number of trained parameters?

This project scales down the idea of FlyGM (Jin, Zhu, Zhang & Sui 2026,
[arXiv:2602.17997](https://arxiv.org/abs/2602.17997)), which used the whole fruit-fly
connectome as a fixed graph inside a body controller, to the 302-neuron worm.
Unlike FlyGM it trains with evolution strategies rather than deep RL, and it runs
on a laptop CPU.

**Status: milestone 2 of 8** (connectome loaded, signs assigned, control graphs built).
No behaviour or results yet.

## Plan

1. ~~Research data sources and agree the plan~~
2. ~~Connectome loader, sign assignment, control graphs, graph statistics~~
3. 2D worm body (resistive force theory) and arena, driven by a hand-coded oscillator
4. Graded leaky-integrator brain on the connectome, wired to body and sensors; stability tests
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
- **Trained:** time constant, bias and gain per neuron class (104 classes), a few
  global scales, and per-quadrant muscle gains: a few hundred parameters in all.
- **Controls:** degree-preserving rewiring, an Erdős–Rényi graph, shuffled signs and
  shuffled weights. Only neuron-to-neuron wiring changes; inputs, outputs and the
  parameter count stay identical (`src/wormbrain/controls.py`).

## Setup

```bash
uv sync                     # Python 3.11+, installs cect and the rest
uv run pytest               # tests (first run builds the data cache, ~20 s)
make stats                  # graph statistics -> reports/graph_stats/
```

## Layout

```
src/wormbrain/   data.py (load + cache) · signs.py · connectome.py · controls.py · graphstats.py
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

## Limitations (so far)

- Synapse signs are inferred from transmitter identity; glutamate's sign is a
  global assumption that changes the excitatory:inhibitory ratio from 16:1 to 2:1.
- Connection weights are anatomical, not physiological strengths.
- Neuromodulation (monoamines, neuropeptides) is left out.
