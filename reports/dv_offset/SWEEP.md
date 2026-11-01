# One back/belly offset straightens circling brains

`scripts/dv_offset_sweep.py`: already-trained brains, nothing retrained; one number is
added to every dorsal muscle's input and subtracted from every ventral one. Flat field,
4 headings, 90 s. Turning per mm of crawling (straight is about 0; a 1 mm circle is 57°/mm).

| brain | offset 0 (as trained) | best offset | turning there | net progress (mm/s): as trained → best |
|---|---|---|---|---|
| milestone 6, inhibitory seed 0 | 493°/mm | −1.11 | 0.9°/mm | 0.090 → 0.214 |
| milestone 6, inhibitory seed 1 | 190°/mm | +1.27 | 5.5°/mm | 0.199 → 0.343 |
| milestone 6, excitatory seed 1 | 19°/mm | +0.49 | 0.2°/mm | 0.160 → 0.161 |
| patch world v2, inhibitory seed 0 | 6°/mm | 0.00 | 5.6°/mm | 0.200 → 0.200 |
| patch world v2, inhibitory seed 1 | 121°/mm | −0.25 | 11.5°/mm | 0.093 → 0.087 |
| patch world v2, excitatory seed 1 | 7°/mm | −0.25 | 3.9°/mm | 0.094 → 0.094 |

Turning changes smoothly with the offset, with a single minimum, so it is easy for
the optimiser to find. In the trained brains, circling is mostly a constant
dorsal–ventral imbalance, not a failure of the oscillator or of steering.
