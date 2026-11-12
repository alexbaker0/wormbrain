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
| real_glu-excitatory_seed1 | 1.75 | 15% | 0.163 | 0.184 | 1.19 | 0.191 |
| real_glu-excitatory_seed2 | 0.00 | 0% | 0.117 | 0.110 | 0.00 | 0.121 |
| real_glu-inhibitory_seed1 | 1.35 | 11% | 0.106 | 0.133 | 1.38 | 0.103 |
| real_glu-inhibitory_seed6 | 1.99 | 17% | 0.190 | 0.215 | 1.99 | 0.193 |
