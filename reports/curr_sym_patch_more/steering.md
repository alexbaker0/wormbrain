# Steering probe

On a flat field the smell at the head is replaced by a triangle wave (10 s rising from 0.05
to 0.6, then 10 s falling), whatever the worm does. A steering brain turns differently when
the smell rises than when it falls. Reports the signed turning rate (deg/s) in each phase
and the difference (the steering response), the share of turning that is one-way, and the
crawling speed. 8 headings x 120 s, the first 20 s ignored.

| brain | run | turning while smell rises (°/s) | while it falls (°/s) | steering response (fall − rise) | one-way share | net speed (mm/s) |
|---|---|---|---|---|---|---|
| curr_sym_patch_more | random_glu-excitatory_seed0 | -0.2 | +8.5 | +8.7 | 23% | 0.072 |
| curr_sym_patch_more | random_glu-excitatory_seed1 | +65.9 | +72.5 | +6.6 | 94% | 0.058 |
| curr_sym_patch_more | random_glu-inhibitory_seed0 | -6.4 | -0.1 | +6.3 | 10% | 0.027 |
| curr_sym_patch_more | random_glu-inhibitory_seed1 | +4.1 | +10.6 | +6.6 | 9% | 0.073 |
| curr_sym_patch_more | real_glu-excitatory_seed2 | +2.8 | -2.2 | -5.0 | 1% | 0.076 |
| curr_sym_patch_more | real_glu-excitatory_seed3 | -0.0 | -0.2 | -0.2 | 1% | 0.121 |
| curr_sym_patch_more | real_glu-inhibitory_seed2 | +9.5 | +9.8 | +0.4 | 21% | 0.018 |
| curr_sym_patch_more | real_glu-inhibitory_seed3 | -15.1 | -29.7 | -14.5 | 86% | 0.045 |
| curr_sym_patch_more | rewired_glu-excitatory_seed0 | -10.4 | -14.4 | -4.0 | 79% | 0.043 |
| curr_sym_patch_more | rewired_glu-excitatory_seed1 | +22.5 | +31.7 | +9.2 | 100% | 0.017 |
| curr_sym_patch_more | rewired_glu-inhibitory_seed0 | +49.6 | +16.5 | -33.1 | 41% | 0.031 |
| curr_sym_patch_more | rewired_glu-inhibitory_seed1 | -0.5 | -22.3 | -21.7 | 47% | 0.061 |
| hand-coded steering |  | -6.3 | -24.1 | -17.9 | 91% | 0.027 |
