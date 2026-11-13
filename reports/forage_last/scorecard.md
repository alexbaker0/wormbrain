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
| forage_last | real exc s9 | 0.02 | 0.30 | 1.19 | 76 | 0.50 | 75% | 0.22 | 18.68 | 1.42 | 98% | 1.03 | 0.87 |
| forage_last | real inh s1 | 0.04 | 0.12 | 2.19 | 268 | 0.66 | 100% | 0.46 | -39.55 | 1.17 | 83% | 0.99 | 2.45 |
| forage_last | real inh s2 | 0.01 | 0.36 | 1.14 | 367 | 0.75 | 100% | 0.41 | 21.17 | 1.40 | 77% | 0.97 | 0.75 |
| forage_last | real inh s6 | 0.01 | 0.26 | 1.00 | 293 | 0.67 | 100% | 0.58 | 24.84 | 2.50 | 20% | 0.87 | 0.75 |
| hand-coded steering |  | 0.17 | 0.40 | 0.65 | 0 | 0.21 | 3% | 0.97 | 12.78 | 0.37 | 74% | 1.01 | 1.56 |
| blind straight |  | 0.17 | 0.40 | 0.65 | 0 | -1.30 | 6% | 0.94 | -0.31 | 0.99 | 1% | 1.00 | 0.53 |
