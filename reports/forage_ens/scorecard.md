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
| forage_ens | real exc s0 | 0.04 | 0.16 | 1.75 | 47 | 0.03 | 6% | 0.43 | 12.48 | 0.79 | 7% | 0.94 | 0.26 |
| forage_ens | real exc s1 | 0.03 | 0.36 | 1.22 | 76 | 0.67 | 100% | 0.48 | 19.69 | 1.85 | 49% | 1.10 | 0.64 |
| forage_ens | real exc s2 | 0.02 | 0.42 | 1.71 | 49 | 0.34 | 56% | 0.22 | 15.56 | 1.10 | 74% | 1.01 | 0.61 |
| forage_ens | real exc s3 | 0.14 | 0.34 | 0.96 | 11 | -0.58 | 6% | 0.86 | 9.06 | 1.07 | 28% | 1.00 | 0.15 |
| forage_ens | real exc s4 | 0.12 | 0.32 | 1.55 | 17 | -0.20 | 16% | 0.47 | 9.74 | 1.01 | 50% | 1.00 | 0.34 |
| forage_ens | real exc s5 | 0.11 | 0.26 | 3.61 | 15 | -0.33 | 6% | 0.66 | 9.48 | 1.01 | 87% | 0.98 | 0.55 |
| forage_ens | real exc s6 | 0.16 | 0.40 | 2.03 | 14 | 0.00 | 28% | 0.45 | 8.03 | 0.96 | 37% | 1.01 | 0.35 |
| forage_ens | real exc s7 | 0.12 | 0.20 | 1.19 | 13 | -0.52 | 6% | 0.67 | 9.30 | 1.03 | 23% | 1.03 | 0.33 |
| forage_ens | real inh s0 | 0.10 | 0.34 | 2.57 | 14 | -0.40 | 6% | 0.81 | 8.16 | 0.93 | 68% | 1.03 | 0.33 |
| forage_ens | real inh s1 | 0.20 | 0.30 | 1.02 | 2 | 0.77 | 100% | 0.55 | 24.68 | 1.06 | 38% | 1.06 | 4.49 |
| forage_ens | real inh s2 | 0.12 | 0.38 | 1.59 | 14 | -0.33 | 22% | 0.58 | 10.69 | 1.13 | 93% | 1.01 | 0.43 |
| forage_ens | real inh s3 | 0.12 | 0.20 | 1.40 | 16 | -0.44 | 16% | 0.54 | 9.46 | 1.03 | 29% | 1.04 | 0.30 |
| forage_ens | real inh s4 | 0.18 | 0.50 | 1.34 | 12 | -0.10 | 19% | 0.58 | 9.12 | 1.01 | 73% | 1.02 | 0.29 |
| forage_ens | real inh s5 | 0.11 | 0.20 | 1.09 | 10 | -0.24 | 16% | 0.77 | 9.94 | 1.07 | 27% | 1.00 | 0.35 |
| forage_ens | real inh s6 | 0.16 | 0.32 | 1.75 | 5 | 0.74 | 100% | 0.45 | 21.86 | 1.11 | 31% | 1.00 | 4.10 |
| forage_ens | real inh s7 | 0.10 | 0.28 | 6.20 | 19 | -0.18 | 3% | 0.65 | 8.98 | 0.92 | 22% | 1.13 | 0.43 |
| hand-coded steering |  | 0.17 | 0.40 | 0.65 | 0 | 0.21 | 3% | 0.97 | 12.78 | 0.37 | 74% | 1.01 | 1.56 |
| blind straight |  | 0.17 | 0.40 | 0.65 | 0 | -1.30 | 6% | 0.94 | -0.31 | 0.99 | 1% | 1.00 | 0.53 |
