# Steering probe

On a flat field the smell at the head is replaced by a triangle wave (10 s rising from 0.05
to 0.6, then 10 s falling), whatever the worm does. A steering brain turns differently when
the smell rises than when it falls. Reports the signed turning rate (deg/s) in each phase
and the difference (the steering response), the share of turning that is one-way, and the
crawling speed. 8 headings x 120 s, the first 20 s ignored.

| brain | run | turning while smell rises (°/s) | while it falls (°/s) | steering response (fall − rise) | one-way share | net speed (mm/s) |
|---|---|---|---|---|---|---|
| curr_usual_grad | real_glu-excitatory_seed0 | +2.2 | +2.2 | -0.0 | 44% | 0.057 |
| curr_usual_grad | real_glu-excitatory_seed1 | +13.6 | +15.0 | +1.4 | 47% | 0.019 |
| curr_usual_grad | real_glu-inhibitory_seed0 | +3.4 | +4.0 | +0.6 | 27% | 0.001 |
| curr_usual_grad | real_glu-inhibitory_seed1 | -7.9 | -12.3 | -4.4 | 98% | 0.029 |
| hand-coded steering |  | -6.3 | -24.1 | -17.9 | 91% | 0.027 |
