# Data sources and assumptions

No connectivity is invented. Every number comes from one of the datasets below,
loaded at runtime through the `cect` package. Nothing raw is committed: `cect`
ships the published spreadsheets inside its wheel, and `wormbrain.data` caches
the extracted arrays in `data/cache/` (git-ignored; set `WORMBRAIN_CACHE` to move it).
Delete the cache, or call `load_raw(refresh=True)`, to rebuild it.

## Datasets

| What | Source | Version | Licence | How we get it |
|---|---|---|---|---|
| Chemical synapses, gap junctions, neuron→muscle synapses (hermaphrodite) | Cook et al. 2019, *Whole-animal connectomes of both* Caenorhabditis elegans *sexes*, Nature 571:63–71, doi:10.1038/s41586-019-1352-7 | Supplementary Information 5 adjacency matrices, **corrected July 2020** (WormWiring), symmetrised gap-junction sheet | Not stated in the files; data published with the Nature article and distributed by WormWiring. **Not redistributed here**; read from the `cect` wheel at runtime. | `cect.readers.Cook2019HermReader` |
| Neurotransmitter identity per neuron | Wang et al. 2024, *A neurotransmitter atlas of* C. elegans *males and hermaphrodites*, eLife 13:RP95402, doi:10.7554/eLife.95402 | Supplementary files 2 and 3 (v1), as bundled in `cect` | CC BY 4.0 (eLife) | `cect.readers.Wang2024HermReader(...).all_neurotransmitters` |
| Neuron names, sensory/inter/motor labels, pharyngeal list, muscle names | OpenWorm ConnectomeToolbox (`cect`) | 0.3.5 (pinned in `pyproject.toml`) | MIT | `cect.Cells` |
| Per-edge synaptic polarity (optional) | Fenyves et al. 2020, *Synaptic polarity and sign-balance prediction using gene expression data in the* Caenorhabditis elegans *chemical synapse neuronal connectome network*, PLOS Comput Biol 16:e1007974, doi:10.1371/journal.pcbi.1007974 | — | CC BY 4.0 (PLOS) | **Not yet obtained** (see below) |

Note: the `cect` documentation (and OpenWorm's DD020) still shows
`from cect.Cook2019HermReader import get_instance`; in 0.3.5 the module is
`cect.readers.Cook2019HermReader`.

### Getting the Fenyves signs

The PLOS supplementary files were not reachable from the environment this was
built in. To use them: download the supplementary table of predicted polarities
from the article page (or the EleganSign tool, http://EleganSign.linkgroup.hu),
convert it to a CSV with columns `pre,post,sign` (sign: positive excitatory,
negative inhibitory, using Cook/cect neuron names), save it as
`data/raw/fenyves2020_signs.csv`, and set in the config:

```yaml
signs:
  source: fenyves
  fenyves_csv: data/raw/fenyves2020_signs.csv
```

Edges the file doesn't cover fall back to the transmitter rule. Fenyves et al.
worked from the WormWiring connectome (297 neurons), so a few names may need mapping.

## What the numbers mean

- Matrices are `M[pre, post]`. A test checks this (AVAL→VA5 exists, VA5→AVAL does not).
- The values are the connection weights in the Cook et al. spreadsheets. Gap-junction
  values reach 401, too large to be counts of individual junctions, so we treat all
  values as **relative anatomical weights**, not synapse counts. The brain model
  normalises them. (To confirm the exact unit against the paper's Methods.)
- 302 neurons, 95 of the 96 body-wall muscles (MVL24 has no entries), 3,709 chemical
  edges and 1,098 gap-junction pairs among all neurons before the choices below.

## Modelling assumptions (all configurable in `configs/connectome.yaml`)

| Assumption | Default | Why / effect |
|---|---|---|
| Pharyngeal neurons | excluded (282 neurons left) | The pharyngeal system joins the rest only through RIPL/R and has no role in locomotion. `include_pharynx: true` keeps them. |
| Autapses | dropped (37 edges) | So the real graph and every control live in the same space of graphs without self-loops. 12 gap-junction self-entries are also zeroed. |
| One sign per presynaptic neuron | yes (Dale's principle) | Only for `source: transmitter`. Real synapses can differ by receptor; `source: fenyves` sets signs per edge. |
| Acetylcholine | excitatory | Most ACh synapses are excitatory, though C. elegans has inhibitory ACC chloride-channel receptors too. |
| GABA | inhibitory | |
| **Glutamate** | **excitatory** | **The biggest uncertainty.** Glutamate excites through GLR/NMR receptors and inhibits through GLC chloride channels, and a single neuron can do both. All-excitatory gives E:I = 15.7:1 by edges; all-inhibitory gives 1.8:1. Fenyves et al. predict about 4:1, in between. The main comparison will be repeated with `glutamate: inhibitory` as a sensitivity check. |
| Co-transmission | first of ACh, GABA, Glu decides | Affects 9 neurons: AFDL/R, DVA, PVNL/R (ACh + Glu → excitatory) and SMDDL/R, SMDVL/R (ACh + GABA → excitatory). |
| Neurons with no ACh, GABA or Glu | excitatory | 27 neurons: dopamine-only ADE and CEP, betaine-only ASI, GABA-uptake-only AVF, CANL/R (none identified), and AVH, AVK, BDU, PVM, PVQ, PVT, PVW, RID, RMG (unidentified "orphan" transmitter). `unknown: zero` silences their chemical outputs instead. |
| Neuromodulation | ignored | Monoamine and neuropeptide networks (Bentley et al. 2016; Ripoll-Sánchez et al. 2023, both bundled in `cect`) act outside the wired synapses. |
| Gap junctions | unsigned, symmetric | Current flows down the voltage difference. |
| Neuron classes for tying parameters | 104 classes | Left/right and dorsal/ventral members share a class (AIYL/R → AIY, RMDDL/RMDVR/RMDL → RMD); numbered motor neurons share one (VB1–11 → VB). Matches White et al. 1986's 118 classes minus 14 pharyngeal ones. |

Run `uv run python scripts/graph_stats.py` to regenerate the statistics in
`reports/graph_stats/` under any of these settings.
