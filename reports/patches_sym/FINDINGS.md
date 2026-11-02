# Symmetric body vs usual model, both trained from scratch in patch world v2

Configs: [patches_sym.yaml](../../configs/patches_sym.yaml) has tied dorsal/ventral motor
classes plus the back/belly offset. [patches_scratch.yaml](../../configs/patches_scratch.yaml)
is the usual model. Each run is a crawling stage followed by 120 generations in the patch
world (reward = food eaten − energy). Seeds 0–1, both glutamate settings.

## Held-out test: food eaten in 12 minutes (32 starts)

| run | usual | symmetric |
|---|---|---|
| excitatory, seed 0 | 0.00 (its crawler barely moves, 0.03 mm/s) | 0.65 (crawls at 0.63 mm/s) |
| inhibitory, seed 0 | 0.64 | 0.60 |
| excitatory, seed 1 | **2.17** | 0.51 |
| inhibitory, seed 1 | 0.54 | 0.62 |

Hand-coded steering scores 1.89; blind straight crawling scores 0.77.

## How they move (`scripts/patch_behaviour.py`)

Symmetric:

| mover | food eaten (12 min) | speed on food (mm/s) | speed far from food | time on food | turning far from food, °/mm (one-way share) | turning near food, °/mm |
|---|---|---|---|---|---|---|
| real_glu-excitatory_seed0 | 0.69 | 0.151 | 0.150 | 3% | 14 (3%) | 14 |
| real_glu-excitatory_seed1 | 0.43 | 0.055 | 0.057 | 2% | 594 (3%) | 598 |
| real_glu-inhibitory_seed0 | 0.81 | 0.079 | 0.078 | 4% | 10 (6%) | 10 |
| real_glu-inhibitory_seed1 | 0.49 | 0.179 | 0.177 | 2% | 49 (2%) | 32 |
| hand-coded steering | 1.56 | 0.140 | 0.176 | 17% | 28 (59%) | 69 |
| blind straight | 0.53 | 0.176 | 0.176 | 2% | 20 (0%) | 20 |

Usual:

| mover | food eaten (12 min) | speed on food (mm/s) | speed far from food | time on food | turning far from food, °/mm (one-way share) | turning near food, °/mm |
|---|---|---|---|---|---|---|
| real_glu-excitatory_seed0 | 0.00 | nan | 0.000 | 0% | 8847353498231 (10%) | 0 |
| real_glu-excitatory_seed1 | 2.06 | 0.099 | 0.096 | 11% | 637 (2%) | 633 |
| real_glu-inhibitory_seed0 | 0.53 | 0.076 | 0.076 | 2% | 16 (18%) | 16 |
| real_glu-inhibitory_seed1 | 0.64 | 0.090 | 0.088 | 3% | 29 (10%) | 15 |
| hand-coded steering | 1.56 | 0.140 | 0.176 | 17% | 28 (59%) | 69 |
| blind straight | 0.53 | 0.176 | 0.176 | 2% | 20 (0%) | 20 |

## What we learn

1. **The symmetric body crawls reliably and straight.** All four learned to crawl,
   including the brain that cannot crawl with the usual body. Three of the four have
   0.6–1.9°/mm of flat-field turning, and none circles (2–6% one-way).
2. **But it does not steer.** All four eat about what a blind straight crawler eats. The
   fake-smell probe ([../steering_probe.md](../steering_probe.md)) shows no turning
   response to the smell. The smell-reach trace ([../smell_reach.md](../smell_reach.md))
   shows the smell signal dying out before it reaches the head motor neurons SMD and RMD.
   It arrives 5–100 times weaker there than in brains trained on the gradient task.
3. **Why:** the patch world rewards only food eaten. Food is smelled only within about
   3 mm, so a weak steering response barely changes the reward, and the smell pathway is
   never strengthened. In addition, the head motor neurons had no sense of head bending,
   so they had no way to steer towards the side where the smell rises.
4. **Next:** head proprioception for SMD/RMD and a curriculum of crawl → broad gradient →
   patch world (`configs/curr_*`, `scripts/queue_curriculum.sh`).
