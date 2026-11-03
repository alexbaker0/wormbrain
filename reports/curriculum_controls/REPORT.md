# Real vs rewired vs random wiring under the curriculum

Pools the patch-world results of reports/curr_sym_patch (real, seeds 0-1) and
reports/curr_sym_patch_more (real seeds 2-3, rewired and random seeds 0-1). Held-out
food eaten in 12 minutes, gradient-climbing share and flat-field turning per run; real vs
each control with the stratified exact permutation test (strata = glutamate setting),
Holm-corrected, and a bootstrap 95% CI of the difference. Exploratory: few runs per
condition. Writes reports/curriculum_controls/REPORT.md.


| condition | glutamate | seed | food eaten | found food | climbed gradient | flat-field turning (°/mm) |
|---|---|---|---|---|---|---|
| random | excitatory | 0 | 1.36 | 100% | 38% | 2.8 |
| random | excitatory | 1 | 0.54 | 56% | 50% | 1157.2 |
| random | inhibitory | 0 | 1.11 | 97% | 56% | 13.5 |
| random | inhibitory | 1 | 3.03 | 100% | 34% | 463.6 |
| real | excitatory | 0 | 5.65 | 100% | 59% | 2.3 |
| real | excitatory | 1 | 0.69 | 78% | 44% | 0.9 |
| real | excitatory | 2 | 0.67 | 78% | 47% | 46.7 |
| real | excitatory | 3 | 0.68 | 97% | 41% | 0.6 |
| real | inhibitory | 0 | 4.39 | 100% | 88% | 12.9 |
| real | inhibitory | 1 | 5.09 | 100% | 100% | 11.5 |
| real | inhibitory | 2 | 1.24 | 94% | 100% | 72.7 |
| real | inhibitory | 3 | 7.35 | 100% | 100% | 4.1 |
| rewired | excitatory | 0 | 3.48 | 100% | 100% | 74.7 |
| rewired | excitatory | 1 | 2.52 | 94% | 100% | 203.0 |
| rewired | inhibitory | 0 | 7.01 | 100% | 100% | 370.8 |
| rewired | inhibitory | 1 | 5.05 | 100% | 38% | 6.5 |

## Food eaten: real vs controls

| comparison | real seeds | n real / n control | mean real | mean control | difference (95% CI) | p (exact) | p (Holm) |
|---|---|---|---|---|---|---|---|
| real vs rewired | 0-1 (matched) | 4 / 4 | 3.96 | 4.52 | -0.56 (-2.29 to +1.17) | 0.778 | 0.778 |
| real vs random | 0-1 (matched) | 4 / 4 | 3.96 | 1.51 | +2.45 (+0.73 to +4.16) | 0.111 | 0.444 |
| real vs rewired | all | 8 / 4 | 3.22 | 4.52 | -1.30 (-2.92 to +0.44) | 0.364 | 0.729 |
| real vs random | all | 8 / 4 | 3.22 | 1.51 | +1.71 (+0.08 to +3.39) | 0.200 | 0.600 |
