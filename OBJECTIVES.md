# Training objectives: review and redesign

Why earlier training gave circling or blind worms, what the modelling literature does, the
objectives we now use, and what they produced. Status: the first foraging run is finished;
two follow-up runs (patch world, and the same training without the food-contact sense) are
still running and will be added here.

**Sources.** Four modelling papers have now been read in full (Izquierdo & Lockery 2010;
Izquierdo & Beer 2013; Izquierdo & Beer 2018; Olivares, Izquierdo & Beer 2021); section 2a
lists what they say. The behavioural papers (Iino & Yoshida, Pierce-Shimomura, Sawin,
Fang-Yen, Boyle) are still known only from search summaries and abstracts, so treat their
numbers as approximate.

## 1. What went wrong before

| Stage | Objective | What it actually rewarded | Result |
|---|---|---|---|
| Crawl | Go as fast as possible, head first | Any fast gait | 0.13–0.42 mm/s, 0.16–0.64 Hz; nothing about a normal gait |
| One food source | Mean smell late in the run, plus a "keep moving" rule | Being near the peak while still moving | Tight circles on the peak; the circling habit carried over to empty ground |
| Food patches from scratch | Food eaten | Nothing until a patch is found by luck | Straight but blind crawlers |
| Curriculum (crawl → gradient → patches) | The three above in order | Works, but inherits the circling of stage 2 | 3 of 4 brains forage well; one runs straight |

Three weaknesses run through all of it:

1. **The crawl stage had no target.** "As fast as possible" does not describe a worm.
2. **The gradient stage paid for staying near food but forbade stopping.** Circling is the
   only way to do both.
3. **The worm could not tell it was on food.** Smell peaks at the food, but nothing says
   "you are here, eating".

Two body problems were fixed earlier and are kept: the dorsal/ventral imbalance (now a
symmetric body) and the missing sense of head bending (now head proprioception).

## 2. What other models do

- **Crawl: match the real worm.** Izquierdo and Beer's group evolve locomotion circuits to
  match the worm's measured forward velocity, in stages, on a symmetric repeating body
  (Olivares, Izquierdo & Beer 2018, 2021; Izquierdo & Beer 2018). Measured crawling on agar
  is roughly 0.3 Hz with a wavelength near 0.65 body lengths, about 0.2 mm/s
  ([Fang-Yen et al. 2010](https://doi.org/10.1073/pnas.1003016107);
  [Boyle, Berri & Cohen 2012](https://doi.org/10.3389/fncom.2012.00010)).
- **Chemotaxis: reward the outcome, not the manoeuvre.** Izquierdo & Lockery (2010) and
  [Izquierdo & Beer (2013)](https://doi.org/10.1371/journal.pcbi.1002890) score a
  chemotaxis index from the time-averaged distance to the peak. Steering by head sweeps
  (klinotaxis) is never rewarded directly; it emerges.
- **What real worms do.** Gradual curving towards the peak ("weathervane", Iino & Yoshida
  2009), sharp turns when the smell falls ("pirouettes", Pierce-Shimomura et al. 1999), and
  slowing on food through dopamine neurons that sense the bacteria mechanically (Sawin,
  Ranganathan & Horvitz 2000).
- **Whole-connectome work** (FlyGM, BAAIWorm) trains with reinforcement learning or
  gradient methods and mostly targets locomotion and simple taxis.

We use these behaviours as a **yardstick, not as training targets**.

## 2a. Checked against the full papers

| Point | What the papers do | What we do | Verdict |
|---|---|---|---|
| Crawl fitness | 1 − \|v − 0.22\| / 0.22, v = net displacement of the body centre over 50 s (2018 eq. 2.6; 2021 eq. 5) | Same form, 0.2 mm/s, 60 s | Matches; 0.22 is the published value |
| Frequency | 2021 also rewards 0.44 Hz in the isolated motor unit; 2018 leaves it free and gets 0.34–0.43 Hz | Free; we get 0.28–0.44 Hz | Fine |
| Wavelength | Not in the fitness. Checked afterwards; real range 0.4–0.9 body lengths; 2021 discards solutions outside it | Not in the fitness; ours are 1.2–1.7 | Ours are too long; they filter, we have not |
| Chemotaxis fitness | CI = 1 − time-averaged distance / start distance, negatives set to 0 (2010 eq. 7) | Scorecard CI is the same idea; training uses food eaten | Matches as a yardstick |
| Steering never rewarded | Stated explicitly: weathervane-like turning "is an emergent property" (2013) | Same | Matches |
| Smell input | ON and OFF cells see a time derivative (recent average minus earlier average), rectified | ASEL ON / ASER OFF, concentration minus running average, rectified | Matches |
| Dorsal/ventral symmetry | Parameters symmetric across the midline (2013) | Symmetric body option | Matches |
| Gradient shape | **Conical, with random steepness**, because in a Gaussian "local steepness is systematically related to distance" and gives unrealistic strategies; Gaussian used only for testing | Gaussian in training | **Difference** |
| Assays per fitness value | **50** random starts (2010) | 6 | **Difference**: our fitness is much noisier |
| Runs | **100–160 seeds**, then keep the good ones | 2 seeds × 2 settings | **Difference** |
| Stopping, dwelling | Not modelled: a point worm at a constant 0.22 mm/s with a built-in oscillator; pirouettes imposed at random, not evolved | Full body, speed free | They never faced our circling-at-food problem |

Two things in the full texts change how our results should be read:

1. **A seed lottery is normal in this literature.** With only 8–20 parameters, 17 of 100
   chemotaxis runs failed outright and 27 of 100 reached CI ≥ 0.75 (2013). For crawling,
   46 of 100 (2018) and 65% of 160 (2021) passed. They report the successful ensemble.
   Our 2 of 4 is in line; our mistake is running 4 and expecting 4.
2. **Their worms cannot stop or choose a speed**, so their objective says nothing about
   behaviour at the food. Slowing on food is outside what those objectives were built for.

## 3. The new objectives

One idea throughout: **food eaten minus energy spent**, on a body that first learns a
realistic crawl.

1. **Gait** (`objective: gait`): score = 1 − |net head-first speed − 0.2 mm/s| / 0.2.
   Speed matching also rewards straightness, since net displacement is what counts.
   Frequency and wavelength are left free.
2. **Serial foraging** (`configs/forage.yaml`): one food source at a time, smelled from far
   away. The worm must reach it and stay within 1 mm for 20 s to eat it; then a new one
   appears 5–9 mm away. Score = foods eaten + closest approach to the unfinished food
   (at most one food's worth) − 0.2 × energy. There is no keep-moving rule, and a frozen
   worm scores exactly 0, so there is no freeze trap.
3. **Patch world** (`configs/forage_patch.yaml`): the same objective with many small
   patches. Running now.

New sense: CEP, ADE and PDE (the dopamine neurons of Sawin et al.) receive a signal while
the head touches food (`food_sense`).

**Validation, never trained on:** `scripts/scorecard.py` (speed, frequency, wavelength,
turning on an empty field, chemotaxis index, reaching, weathervane, turn ratio, one-way
turning, patches eaten) and `scripts/dwell_check.py` (speed on and off food, and with the
food sense cut). `scripts/reward_check_forage.py` checks the score ranks simple movers
sensibly before any training ([result](reports/reward_check_forage.md)).

## 4. Results so far

Real wiring, 2 seeds × 2 glutamate settings. Full tables:
[summary](reports/forage/summary.md), [scorecard](reports/forage/scorecard.md),
[food-sense check](reports/forage/dwell.md), [old brains](reports/scorecard/scorecard.md).

**Gait stage: worked on all four.** Scores 0.98–1.00; undulation 0.28–0.44 Hz although
frequency was not a target. Wavelength is still too long (1.2–1.7 body lengths, real 0.65).

**Foraging stage: two of four learned to forage.**

| Brain | Foods eaten (240 s, held-out) | Turning on empty field (°/mm) | Reached food | Weathervane (°/mm) | Turn ratio | One-way turning | Patches eaten, untrained world |
|---|---|---|---|---|---|---|---|
| inhibitory s1 | 2.14 | 1 | 100% | 36.7 | 1.46 | 19% | 4.21 |
| excitatory s0 | 2.68 | 104 | 100% | 27.2 | 1.56 | 51% | 0.69 |
| excitatory s1 | 0.06 | 12 | 12% | 9.4 | 1.03 | 36% | 0.45 |
| inhibitory s0 | 0.07 | 15 | 6% | 8.2 | 0.89 | 12% | 0.40 |
| hand-coded steering | 0.06 | 0 | 3% | 12.8 | 0.37 | 74% | 1.56 |
| old circler (gradient stage) | 2.62 | 260 | 100% | 24.7 | 1.90 | 93% | 1.00 |

- **Inhibitory s1 is the most worm-like brain so far.** Straight on empty ground, curves
  towards food from both sides, turns more when the smell falls, always arrives, and eats
  4.21 patches in a world it never trained in (the old curriculum needed a patch stage to
  reach 3.9–5.7).
- **Excitatory s0** eats the most but loops when there is no smell and barely moves
  forward on an empty field.
- **Two brains stalled** at "approach a bit, never eat". Training is still a seed lottery.

**The food-contact sense is not used.** Cutting it changes nothing (foods 2.14 → 2.12 and
2.68 → 2.77), and no brain slows on food (speed on food 0.21 vs 0.21 mm/s off food for the
best brain). The successful brains stay on food by steering tightly around it at full
speed.

## 5. Why no slowing, and what to change next

In this world a worm circling inside the 1 mm food radius eats exactly as fast as one that
stops, and the energy term is small (about 0.1 against 2–3 foods). So the objective gives
almost no reason to stop, and training did not find it. That is a property of the world we
built, not evidence about the wiring. Options that keep the "food − energy" principle:

1. **Make food smaller than a loop** (eating radius about 0.3 mm), so staying on it needs
   slowing down.
2. **Charge a realistic energy price**, so moving on food costs more than it gains.
3. **Follow the papers on the three differences:** many seeds with the best kept by
   validation score, more starts per fitness evaluation, and conical gradients of random
   steepness in training with Gaussian kept for testing.
4. **Filter on wavelength afterwards**, as Olivares et al. do, and use 0.22 mm/s.

## 6. Limits

- Four brains, one wiring; nothing here compares real with rewired or random wiring.
- Wavelength is unrealistic; only speed is matched.
- The approach term is a shaping aid. It is capped at one food's worth, but it is not
  "pure" food minus energy.
- The behavioural reference values still come from summaries (see Sources above).
