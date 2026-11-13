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
| real_glu-excitatory_seed10 | 0.82 | 7% | 0.126 | 0.138 | 0.84 | 0.134 |
| real_glu-excitatory_seed15 | 0.76 | 6% | 0.042 | 0.138 | 0.19 | 0.143 |
| real_glu-excitatory_seed7 | 3.35 | 28% | 0.107 | 0.132 | 3.38 | 0.106 |
| real_glu-excitatory_seed9 | 4.57 | 38% | 0.237 | 0.255 | 4.35 | 0.241 |
| real_glu-inhibitory_seed1 | 5.35 | 45% | 0.242 | 0.207 | 5.03 | 0.225 |
| real_glu-inhibitory_seed15 | 3.79 | 32% | 0.174 | 0.200 | 3.85 | 0.150 |
| real_glu-inhibitory_seed2 | 7.04 | 59% | 0.163 | 0.236 | 4.08 | 0.223 |
| real_glu-inhibitory_seed6 | 6.00 | 50% | 0.265 | 0.255 | 6.09 | 0.259 |
