# Is the food-contact sense used?

```
Do the foraging brains use their food-contact sense? Speed on food vs off it, and what
happens when the sense is cut.

    uv run python scripts/dwell_check.py reports/forage

Foraging world of configs/forage.yaml, 32 held-out starts, 240 s. "speed" is the body
centre's path speed. "sense cut" runs the same brain with the food-contact signal held at
zero (the smell is untouched). Writes <folder>/dwell.md.
```

| brain | foods eaten | time on food | speed on food | speed off food | foods, sense cut | speed on food, sense cut |
|---|---|---|---|---|---|---|
| real_glu-excitatory_seed0 | 2.68 | 22% | 0.256 | 0.263 | 2.77 | 0.256 |
| real_glu-excitatory_seed1 | 0.06 | 1% | 0.163 | 0.162 | 0.06 | 0.164 |
| real_glu-inhibitory_seed0 | 0.07 | 1% | 0.131 | 0.126 | 0.07 | 0.132 |
| real_glu-inhibitory_seed1 | 2.14 | 18% | 0.210 | 0.207 | 2.12 | 0.210 |
