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
| forage_far2 | real exc s10 | 0.07 | 0.34 | 2.72 | 11 | -0.10 | 9% | 0.41 | 10.40 | 1.03 | 34% | 1.00 | 0.47 |
| forage_far2 | real exc s15 | 0.04 | 0.16 | 16.98 | 53 | 0.45 | 78% | 0.32 | 20.87 | 1.33 | 42% | 1.18 | 0.94 |
| forage_far2 | real exc s7 | 0.05 | 0.30 | 0.98 | 57 | 0.65 | 100% | 0.35 | 21.22 | 2.30 | 95% | 0.93 | 1.56 |
| forage_far2 | real exc s9 | 0.17 | 0.24 | 1.38 | 3 | 0.74 | 100% | 0.54 | 15.16 | 2.49 | 86% | 1.01 | 4.99 |
| forage_far2 | real inh s1 | 0.02 | 0.32 | 1.53 | 141 | 0.63 | 100% | 0.28 | 17.64 | 1.37 | 77% | 1.00 | 1.40 |
| forage_far2 | real inh s15 | 0.09 | 0.34 | 2.78 | 15 | -0.17 | 9% | 0.38 | 9.28 | 1.12 | 32% | 1.08 | 0.53 |
| forage_far2 | real inh s2 | 0.05 | 0.30 | 1.42 | 50 | 0.36 | 44% | 0.17 | 15.40 | 1.10 | 100% | 1.06 | 0.81 |
| forage_far2 | real inh s6 | 0.03 | 0.48 | 1.54 | 53 | 0.81 | 100% | 0.42 | 21.69 | 0.85 | 33% | 0.99 | 2.12 |
| hand-coded steering |  | 0.17 | 0.40 | 0.65 | 0 | 0.21 | 3% | 0.97 | 12.78 | 0.37 | 74% | 1.01 | 1.56 |
| blind straight |  | 0.17 | 0.40 | 0.65 | 0 | -1.30 | 6% | 0.94 | -0.31 | 0.99 | 1% | 1.00 | 0.53 |
