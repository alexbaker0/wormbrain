# Is the food-contact sense used?

```
Do the foraging brains use their food-contact sense? Speed on food vs off it, and what
happens when the sense is cut.

    uv run python scripts/dwell_check.py reports/forage [config, default configs/forage.yaml]

Foraging world of configs/forage.yaml, 32 held-out starts, 240 s. "speed" is the body
centre's path speed. "sense cut" runs the same brain with the food-contact signal held at
zero (the smell is untouched). Writes <folder>/dwell.md.
```

| brain | foods eaten | time on food | speed on food | speed off food | foods, sense cut | speed on food, sense cut |
|---|---|---|---|---|---|---|
| real_glu-excitatory_seed9 | 1.39 | 12% | 0.188 | 0.196 | 1.44 | 0.187 |
| real_glu-inhibitory_seed1 | 3.82 | 32% | 0.189 | 0.180 | 3.85 | 0.192 |
| real_glu-inhibitory_seed2 | 3.71 | 31% | 0.187 | 0.212 | 3.31 | 0.213 |
| real_glu-inhibitory_seed6 | 4.00 | 33% | 0.095 | 0.121 | 3.97 | 0.097 |
