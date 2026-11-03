# Does the real wiring matter under the curriculum?

Setup: symmetric body, head proprioception and back/belly offset. Each run is crawl →
broad gradient → patch world (reward = food eaten − energy). Runs:

- real wiring, seeds 0–3 (8 runs: 0–1 from `curr_sym_patch`, 2–3 from `curr_sym_patch_more`)
- rewired wiring (degree-preserving shuffle), seeds 0–1 (4 runs)
- random (Erdős–Rényi) wiring, seeds 0–1 (4 runs)

Each seed has both glutamate settings. Statistics: stratified exact permutation tests (strata
= glutamate setting), Holm-corrected, with bootstrap 95% CIs. Full table:
[REPORT.md](REPORT.md). This is exploratory: there are only 4 runs per control, and it was
not pre-registered.

## Food eaten in 12 minutes (held-out test)

| wiring | runs | patches eaten per run | mean |
|---|---|---|---|
| real | 8 | 5.65, 4.39, 0.69, 5.09, 0.67, 1.24, 0.68, 7.35 | 3.22 (seeds 0–1: 3.96) |
| rewired | 4 | 3.48, 7.01, 2.52, 5.05 | 4.52 |
| random | 4 | 1.36, 1.11, 0.54, 3.03 | 1.51 |

| comparison | mean difference (95% CI) | p (exact) | p (Holm) |
|---|---|---|---|
| real − rewired, matched seeds | −0.56 (−2.29 to +1.17) | 0.78 | 0.78 |
| real − random, matched seeds | +2.45 (+0.73 to +4.16) | 0.11 | 0.44 |
| real − rewired, all real seeds | −1.30 (−2.92 to +0.44) | 0.36 | 0.73 |
| real − random, all real seeds | +1.71 (+0.08 to +3.39) | 0.20 | 0.60 |

**No significant difference in food eaten.** Real wiring does no better than rewired wiring.
It tends to beat random wiring, but not significantly with this few runs.

## How straight they crawl (flat-field turning, °/mm; a 1 mm circle is 57°/mm)

| wiring | median | per run |
|---|---|---|
| real | **7.8** | 2.3, 12.9, 0.9, 11.5, 46.7, 72.7, 0.6, 4.1 |
| rewired | 139 | 74.7, 370.8, 203, 6.5 |
| random | 239 | 2.8, 13.5, 1157, 464 |

Real-wiring brains turn about 15–30 times less on an empty field than the controls. This is
consistent across seeds: on log turning, real − rewired is −1.09 (95% CI −1.83 to −0.34),
p = 0.067, and real − random is −1.03 (−2.16 to +0.08), p = 0.076, all real seeds. That is
suggestive but not significant at this sample size. The rewired foragers that eat well do it
by circling tightly once near food, then breaking away. The best real-wiring foragers make
straight runs between patches.

## What we learn

1. **Food eaten:** the curriculum and the symmetric body, not the specific wiring, are what
   make good foragers. Rewired wiring matches the real wiring. This agrees with the
   milestone-6 comparison, which found the real wiring has no advantage on task score.
2. **Movement:** real wiring gives the straighter, more worm-like crawl, and it is the only
   wiring where most good foragers make straight runs. With 4 runs per control this is a
   lead, not a result. It is the most promising thing to test properly.
3. **Glutamate matters:** with real wiring, 3 of 4 inhibitory-glutamate runs became strong
   foragers, but only 1 of 4 excitatory runs did.
4. **Next:** a pre-registered comparison of turning and food eaten, with more seeds per
   condition (e.g. 6 per glutamate setting), and including sign-shuffled wiring.
