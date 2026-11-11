# Behaviour scorecard

```
Behaviour scorecard: does a trained worm behave like a real one?

    uv run python scripts/scorecard.py reports/A reports/B ...   (every run in <folder>/runs)

None of these measures is a training objective; they are the yardstick the objectives are
judged by. Real-worm reference values are in REFERENCE (sources in OBJECTIVES.md).

Flat field (60 s):
  speed        net crawling speed, mm/s                      real: about 0.2
  freq         undulation frequency, Hz                      real: about 0.3 (0.3-0.5)
  wavelength   bending wavelength, body lengths              real: about 0.65
  turning      path curvature, deg/mm (1 mm circle = 57)     real: near 0 (long runs)
One food source (Gaussian, sigma 4 mm, 32 starts 4-8 mm away, 150 s):
  CI           chemotaxis index 1 - mean(distance)/start distance, distance counted as 0
               once the head is within 1 mm (Izquierdo & Lockery 2010 use the time-averaged
               distance; "reached" stops the clock)       ideal: about 0.8
  reached      share of worms that get within 1 mm
  efficiency   straight-line distance / path length, for worms that reached (1 = direct)
  weathervane  curving towards the food side, deg/mm, while the food is to one side
               (Iino & Yoshida 2009: real worms curve towards the peak; > 0)
  turn ratio   |turning| while the smell falls / while it rises (pirouette-like; real > 1,
               Pierce-Shimomura et al. 1999)
  one-way      share of the approach turning that goes one way (circling = 100%)
  slowing      speed within 1 mm of food / speed far from it (real worms slow on food,
               Sawin et al. 2000; < 1)
Patch world v2 (12 min, held-out layout): patches eaten.
```

| brain | run | speed | freq | wavelength | turning | CI | reached | efficiency | weathervane | turn ratio | one-way | slowing | patches |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| *real worm* | | ≈0.2 | ≈0.3 | ≈0.65 | ≈0 | high | high | →1 | >0 | >1 | low | <1 | — |
| curr_sym_grad | real exc s0 | 0.01 | 0.58 | 0.82 | 259 | 0.89 | 100% | 0.62 | 24.67 | 1.90 | 93% | 0.88 | 1.00 |
| curr_sym_grad | real exc s1 | 0.01 | 0.42 | 1.77 | 125 | 0.80 | 100% | 0.49 | 22.36 | 1.87 | 79% | 0.97 | 0.56 |
| curr_sym_grad | real inh s0 | 0.06 | 0.16 | 2.24 | 35 | 0.57 | 94% | 0.54 | 28.94 | 0.86 | 16% | 1.02 | 1.74 |
| curr_sym_grad | real inh s1 | 0.03 | 0.48 | 1.77 | 95 | 0.77 | 100% | 0.45 | 18.44 | 3.76 | 77% | 1.39 | 0.69 |
| curr_sym_patch | real exc s0 | 0.30 | 0.48 | 0.98 | 2 | -0.04 | 72% | 0.53 | 9.20 | 0.25 | 76% | 1.00 | 5.74 |
| curr_sym_patch | real exc s1 | 0.09 | 0.28 | 1.62 | 1 | -0.41 | 6% | 0.76 | -0.24 | 0.99 | 7% | 1.02 | 0.53 |
| curr_sym_patch | real inh s0 | 0.10 | 0.16 | 1.73 | 13 | 0.59 | 97% | 0.59 | 34.06 | 1.07 | 19% | 1.12 | 3.94 |
| curr_sym_patch | real inh s1 | 0.19 | 0.52 | 1.77 | 12 | 0.65 | 34% | 0.43 | 23.22 | 0.52 | 59% | 0.90 | 5.03 |
| hand-coded steering |  | 0.17 | 0.40 | 0.65 | 0 | 0.21 | 3% | 0.97 | 12.78 | 0.37 | 74% | 1.01 | 1.56 |
| blind straight |  | 0.17 | 0.40 | 0.65 | 0 | -1.30 | 6% | 0.94 | -0.31 | 0.99 | 1% | 1.00 | 0.53 |
