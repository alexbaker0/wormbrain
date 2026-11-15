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
| forage_far3 | real exc s15 | 0.03 | 0.32 | 1.18 | 50 | 0.34 | 59% | 0.26 | 11.55 | 0.89 | 21% | 1.14 | 0.62 |
| forage_far3 | real exc s2 | 0.07 | 0.26 | 3.37 | 60 | 0.59 | 97% | 0.33 | 28.56 | 1.45 | 16% | 1.02 | 2.05 |
| forage_far3 | real exc s7 | 0.05 | 0.26 | 1.04 | 89 | 0.58 | 100% | 0.33 | 17.83 | 2.28 | 88% | 0.90 | 1.32 |
| forage_far3 | real exc s9 | 0.15 | 0.24 | 1.56 | 10 | 0.74 | 100% | 0.57 | 23.48 | 1.26 | 43% | 0.96 | 3.92 |
| forage_far3 | real inh s1 | 0.02 | 0.34 | 1.38 | 111 | 0.62 | 100% | 0.31 | 19.24 | 1.42 | 69% | 1.10 | 0.84 |
| forage_far3 | real inh s12 | 0.00 | 0.52 | 1.27 | 47 | 0.78 | 100% | 0.31 | 20.89 | 1.29 | 98% | 1.06 | 1.75 |
| forage_far3 | real inh s2 | 0.04 | 0.28 | 1.93 | 51 | 0.39 | 56% | 0.19 | 13.35 | 1.15 | 88% | 1.05 | 1.37 |
| forage_far3 | real inh s6 | 0.13 | 0.38 | 1.59 | 18 | 0.76 | 100% | 0.43 | 21.66 | 1.18 | 41% | 1.01 | 2.75 |
| hand-coded steering |  | 0.17 | 0.40 | 0.65 | 0 | 0.21 | 3% | 0.97 | 12.78 | 0.37 | 74% | 1.01 | 1.56 |
| blind straight |  | 0.17 | 0.40 | 0.65 | 0 | -1.30 | 6% | 0.94 | -0.31 | 0.99 | 1% | 1.00 | 0.53 |
