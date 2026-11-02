# Steering probe

On a flat field the smell at the head is replaced by a triangle wave (10 s rising from 0.05
to 0.6, then 10 s falling), whatever the worm does. A steering brain turns differently when
the smell rises than when it falls. Reports the signed turning rate (deg/s) in each phase
and the difference (the steering response), the share of turning that is one-way, and the
crawling speed. 8 headings x 120 s, the first 20 s ignored.

| brain | run | turning while smell rises (°/s) | while it falls (°/s) | steering response (fall − rise) | one-way share | net speed (mm/s) |
|---|---|---|---|---|---|---|
| milestone 6 (gradient reward) | real_glu-excitatory_seed1 | +19.4 | +22.9 | +3.5 | 83% | 0.004 |
| milestone 6 (gradient reward) | real_glu-inhibitory_seed1 | +35.6 | +38.7 | +3.1 | 100% | 0.023 |
| E. far food (straight steerer) | real_glu-excitatory_seed1 | +19.7 | +23.2 | +3.5 | 89% | 0.002 |
| patch v2 + offset | real_glu-excitatory_seed1 | +8.7 | +16.4 | +7.7 | 22% | 0.052 |
| from scratch, usual | real_glu-excitatory_seed1 | +4.3 | +0.2 | -4.1 | 4% | 0.048 |
| from scratch, usual | real_glu-inhibitory_seed0 | -0.3 | -0.1 | +0.2 | 19% | 0.075 |
| from scratch, symmetric | real_glu-excitatory_seed0 | -0.1 | -0.1 | -0.1 | 5% | 0.071 |
| from scratch, symmetric | real_glu-inhibitory_seed0 | +0.0 | +0.1 | +0.0 | 6% | 0.078 |
| from scratch, symmetric | real_glu-excitatory_seed1 | -0.8 | -0.6 | +0.1 | 2% | 0.050 |
| from scratch, symmetric | real_glu-inhibitory_seed1 | -0.2 | -0.5 | -0.3 | 6% | 0.146 |
| hand-coded steering |  | -6.3 | -24.1 | -17.9 | 91% | 0.027 |
