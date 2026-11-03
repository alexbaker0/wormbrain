# Steering probe

On a flat field the smell at the head is replaced by a triangle wave (10 s rising from 0.05
to 0.6, then 10 s falling), whatever the worm does. A steering brain turns differently when
the smell rises than when it falls. Reports the signed turning rate (deg/s) in each phase
and the difference (the steering response), the share of turning that is one-way, and the
crawling speed. 8 headings x 120 s, the first 20 s ignored.

| brain | run | turning while smell rises (°/s) | while it falls (°/s) | steering response (fall − rise) | one-way share | net speed (mm/s) |
|---|---|---|---|---|---|---|
| curr_sym_patch | real_glu-excitatory_seed0 | -2.5 | -22.0 | -19.4 | 69% | 0.058 |
| curr_sym_patch | real_glu-excitatory_seed1 | -0.0 | -0.1 | -0.0 | 1% | 0.087 |
| curr_sym_patch | real_glu-inhibitory_seed0 | -0.5 | -6.6 | -6.1 | 11% | 0.013 |
| curr_sym_patch | real_glu-inhibitory_seed1 | -13.9 | -17.9 | -4.0 | 80% | 0.110 |
| hand-coded steering |  | -6.3 | -24.1 | -17.9 | 91% | 0.027 |
