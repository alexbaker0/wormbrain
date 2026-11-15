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
| real_glu-excitatory_seed15 | 3.36 | 28% | 0.005 | 0.186 | 1.51 | 0.203 |
| real_glu-excitatory_seed2 | 3.90 | 33% | 0.158 | 0.160 | 3.89 | 0.156 |
| real_glu-excitatory_seed7 | 3.91 | 33% | 0.153 | 0.158 | 3.91 | 0.152 |
| real_glu-excitatory_seed9 | 4.96 | 41% | 0.155 | 0.166 | 5.16 | 0.157 |
| real_glu-inhibitory_seed1 | 3.63 | 30% | 0.240 | 0.233 | 3.03 | 0.241 |
| real_glu-inhibitory_seed12 | 4.52 | 38% | 0.320 | 0.336 | 4.20 | 0.324 |
| real_glu-inhibitory_seed2 | 1.32 | 11% | 0.233 | 0.229 | 1.63 | 0.230 |
| real_glu-inhibitory_seed6 | 4.04 | 34% | 0.217 | 0.225 | 4.08 | 0.217 |
