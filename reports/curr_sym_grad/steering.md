# Steering probe

On a flat field the smell at the head is replaced by a triangle wave (10 s rising from 0.05
to 0.6, then 10 s falling), whatever the worm does. A steering brain turns differently when
the smell rises than when it falls. Reports the signed turning rate (deg/s) in each phase
and the difference (the steering response), the share of turning that is one-way, and the
crawling speed. 8 headings x 120 s, the first 20 s ignored.

| brain | run | turning while smell rises (°/s) | while it falls (°/s) | steering response (fall − rise) | one-way share | net speed (mm/s) |
|---|---|---|---|---|---|---|
| curr_sym_grad | real_glu-excitatory_seed0 | -10.9 | -17.5 | -6.6 | 95% | 0.006 |
| curr_sym_grad | real_glu-excitatory_seed1 | -3.0 | -2.9 | +0.1 | 47% | 0.053 |
| curr_sym_grad | real_glu-inhibitory_seed0 | +7.4 | -3.2 | -10.6 | 5% | 0.039 |
| curr_sym_grad | real_glu-inhibitory_seed1 | -16.0 | -12.4 | +3.5 | 87% | 0.002 |
| hand-coded steering |  | -6.3 | -24.1 | -17.9 | 91% | 0.027 |
