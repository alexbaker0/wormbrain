# Steering probe

On a flat field the smell at the head is replaced by a triangle wave (10 s rising from 0.05
to 0.6, then 10 s falling), whatever the worm does. A steering brain turns differently when
the smell rises than when it falls. Reports the signed turning rate (deg/s) in each phase
and the difference (the steering response), the share of turning that is one-way, and the
crawling speed. 8 headings x 120 s, the first 20 s ignored.

| brain | run | turning while smell rises (°/s) | while it falls (°/s) | steering response (fall − rise) | one-way share | net speed (mm/s) |
|---|---|---|---|---|---|---|
| curr_usual_patch | real_glu-excitatory_seed0 | +5.2 | -4.8 | -9.9 | 1% | 0.079 |
| curr_usual_patch | real_glu-excitatory_seed1 | +10.5 | +11.6 | +1.1 | 28% | 0.044 |
| curr_usual_patch | real_glu-inhibitory_seed0 | +0.2 | +0.3 | +0.1 | 8% | 0.063 |
| curr_usual_patch | real_glu-inhibitory_seed1 | -12.1 | -16.4 | -4.3 | 99% | 0.019 |
| hand-coded steering |  | -6.3 | -24.1 | -17.9 | 91% | 0.027 |
