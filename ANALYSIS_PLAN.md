# Analysis plan: does the real wiring beat rewired and random wiring? (milestone 6)

Written and committed before any comparison run. Changes after this point are listed at
the bottom with their reason and date.

## Question

With identical trainable parameters (425), inputs, outputs, training procedure and
budget, does a worm whose brain is the real C. elegans connectome learn chemotaxis
better than one whose brain is a degree-preserving rewiring of it, or a random graph?

## Design

| | |
|---|---|
| Graphs | `real`, `rewired` (in/out degrees, weights and each neuron's sign kept), `random` (Erdős–Rényi: same number of chemical and gap edges, real weights and signs dealt out at random) |
| Glutamate sign | `excitatory` and `inhibitory`, both run (the sign is unresolved; picking one after seeing the pilot would bias the result) |
| Seeds | 4 per graph x glutamate setting (0–3); the seed sets the control graph and the training randomness |
| Runs | 3 x 2 x 4 = 24. The 4 real-graph runs for seeds 0–1 are the milestone-5 pilot, which used this exact configuration; they are reused, not rerun |
| Training | `configs/chemotaxis.yaml` as committed with this plan: crawling stage (100 generations), then chemotaxis stage (150 generations, 8 shared starts per generation), CMA-ES population 24 |
| Test | 32 fixed starts per arena (test seed 1000), never used in training: training arena, far starts, two peaks, linear gradient |

Every run is counted. Runs whose crawling stage fails are failures of that graph, not
excluded.

## Primary outcome and test

- **Outcome:** each run's mean test reward in the training arena (`gaussian`).
- **Comparisons:** real vs rewired, real vs random.
- **Test:** two-sided permutation test on the difference in mean outcome, permuting
  graph labels within each glutamate setting (stratified), so 8 runs per graph with
  the sign setting held fixed. Exact enumeration (70 x 70 relabellings per comparison).
- **Multiplicity:** Holm correction over the two comparisons, alpha = 0.05.
- **Effect size:** difference in means with a 95% bootstrap interval (resampling runs
  within each graph x glutamate cell, 10,000 resamples).

## Secondary outcomes (reported, not tested for significance)

1. The same comparison within each glutamate setting separately (4 runs per graph).
2. Success rate: share of runs whose worms end within 1 mm of the peak in at least
   half of the test starts; share of test starts climbed.
3. Generalisation: test reward in the far-start, two-peak and linear arenas.
4. Sample efficiency: the mean over chemotaxis generations of the best-so-far
   training reward (area under the learning curve), and the curves themselves.
5. Crawling stage: forward speed, and the share of runs above 0.05 mm/s.
6. Sensor use: for every run with positive test reward, the test reward with ASEL and
   ASER silenced.

## Interpretation, decided in advance

- With 8 runs per graph the study can only detect large differences. A
  non-significant result will be reported as "no detectable difference at this
  sample size", not as evidence that the wiring does not matter.
- If the real wiring does worse, that is reported as found.
- Known confound, reported alongside the results: in rewired and random graphs nearly
  every sensory neuron connects directly to a motor neuron (88% in the real graph),
  which may make the controls easier to train.

## Changes after this plan was committed

None yet.
