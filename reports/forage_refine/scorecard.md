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
| forage_refine | real exc s1 | 0.00 | 0.34 | 1.15 | 145 | 0.77 | 100% | 0.58 | 24.26 | 2.91 | 75% | 1.07 | 0.75 |
| forage_refine | real exc s2 | 0.06 | 0.32 | 1.19 | 13 | -0.07 | 9% | 0.42 | 5.31 | 0.97 | 11% | 1.01 | 0.44 |
| forage_refine | real inh s1 | 0.15 | 0.22 | 1.01 | 4 | 0.69 | 100% | 0.58 | 29.23 | 1.76 | 50% | 1.17 | 4.56 |
| forage_refine | real inh s6 | 0.20 | 0.40 | 0.96 | 5 | 0.79 | 100% | 0.51 | 20.00 | 0.94 | 30% | 1.03 | 4.73 |
| hand-coded steering |  | 0.17 | 0.40 | 0.65 | 0 | 0.21 | 3% | 0.97 | 12.78 | 0.37 | 74% | 1.01 | 1.56 |
| blind straight |  | 0.17 | 0.40 | 0.65 | 0 | -1.30 | 6% | 0.94 | -0.31 | 0.99 | 1% | 1.00 | 0.53 |
