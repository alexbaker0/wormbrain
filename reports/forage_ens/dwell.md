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
| real_glu-excitatory_seed0 | 0.44 | 4% | 0.123 | 0.124 | 0.43 | 0.122 |
| real_glu-excitatory_seed1 | 1.65 | 14% | 0.160 | 0.178 | 1.21 | 0.196 |
| real_glu-excitatory_seed2 | 0.72 | 6% | 0.240 | 0.231 | 0.69 | 0.235 |
| real_glu-excitatory_seed3 | 0.06 | 0% | 0.168 | 0.168 | 0.06 | 0.164 |
| real_glu-excitatory_seed4 | 0.06 | 0% | 0.164 | 0.160 | 0.09 | 0.157 |
| real_glu-excitatory_seed5 | 0.08 | 1% | 0.148 | 0.146 | 0.08 | 0.146 |
| real_glu-excitatory_seed6 | 0.13 | 1% | 0.267 | 0.271 | 0.12 | 0.274 |
| real_glu-excitatory_seed7 | 0.01 | 0% | 0.134 | 0.131 | 0.01 | 0.140 |
| real_glu-inhibitory_seed0 | 0.03 | 0% | 0.111 | 0.109 | 0.03 | 0.106 |
| real_glu-inhibitory_seed1 | 1.45 | 12% | 0.170 | 0.186 | 1.57 | 0.168 |
| real_glu-inhibitory_seed2 | 0.05 | 0% | 0.139 | 0.138 | 0.05 | 0.138 |
| real_glu-inhibitory_seed3 | 0.03 | 0% | 0.139 | 0.139 | 0.03 | 0.139 |
| real_glu-inhibitory_seed4 | 0.26 | 2% | 0.272 | 0.271 | 0.27 | 0.271 |
| real_glu-inhibitory_seed5 | 0.17 | 1% | 0.131 | 0.127 | 0.18 | 0.128 |
| real_glu-inhibitory_seed6 | 1.73 | 14% | 0.200 | 0.195 | 1.77 | 0.198 |
| real_glu-inhibitory_seed7 | 0.10 | 1% | 0.132 | 0.126 | 0.10 | 0.133 |
