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
| real_glu-excitatory_seed10 | 0.15 | 1% | 0.132 | 0.146 | 0.06 | 0.149 |
| real_glu-excitatory_seed15 | 3.77 | 31% | 0.010 | 0.153 | 2.38 | 0.174 |
| real_glu-excitatory_seed7 | 3.94 | 33% | 0.188 | 0.192 | 3.96 | 0.183 |
| real_glu-excitatory_seed9 | 5.08 | 42% | 0.157 | 0.166 | 5.21 | 0.159 |
| real_glu-inhibitory_seed1 | 3.87 | 32% | 0.226 | 0.234 | 2.96 | 0.228 |
| real_glu-inhibitory_seed15 | 0.13 | 1% | 0.160 | 0.157 | 0.14 | 0.160 |
| real_glu-inhibitory_seed2 | 1.06 | 9% | 0.237 | 0.224 | 0.75 | 0.235 |
| real_glu-inhibitory_seed6 | 4.31 | 36% | 0.271 | 0.283 | 4.28 | 0.270 |
