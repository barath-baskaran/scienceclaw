# Environmental fate and hazard prediction from a structure and/or a measured spectrum

Plata lab hackathon work on environmental fate and toxicity.

## What this project is

AI agents built and tested a model that predicts how a chemical behaves in the environment (fate
properties such as water solubility, vapour pressure and soil sorption) and some of its hazards
(such as acute lethality and receptor activity). The model can start from three kinds of input:

- a structure, written as a SMILES string;
- a structure plus a measured MS/MS (tandem mass) spectrum;
- **a spectrum alone**, with no structure.

Each prediction comes with:

- an uncertainty interval (a split-conformal interval, see [Terms used](#terms-used)). Next to it we
  report the **empirical** coverage measured on held-out test data, not just the nominal level the
  interval was designed for;
- a domain flag. It separates two different problems with different answers: "far from anything we
  trained on" and "physically undefined for this species";
- the EPI Suite estimate, as a comparator, wherever EPI Suite has a module for that endpoint;
- the features that drove the prediction.

The full method and all results, including the negative ones, are in `paper/whitepaper.pdf`. A shorter
read is `paper/review_summary.pdf`.

## What is in this repository, and what is not

This repository is the public record of the work.

| Included | Not included |
|---|---|
| The paper and review summary (`paper/`) | The trained models |
| The result tables the paper and this README quote (`data/`) | The large per-compound prediction tables the result tables were computed from |
| Every figure, and the numbers files they are built from (`paper/`) | The split/label table that defines the training and test sets (see [Reproducing results](#reproducing-results)) |
| The prediction code and model notes (`tool/`) | A runnable package (see below) |
| A dashboard page with precomputed examples (`dashboard/`) | |

What this means in practice:

- **You cannot predict for a new structure from this repository.** The trained models are not
  included, so the prediction code in `tool/` and the server in `dashboard/tool/` have nothing to run.
  `tool/MODEL_NOTES.md` describes what the models contain and how they were frozen.
- **The dashboard shows precomputed examples only.** Open `dashboard/index.html` in a browser to browse
  **precomputed predictions for a fixed set of example compounds**, offline. It cannot predict for a new
  structure on its own.
- **A runnable package exists but is not published yet.** It contains the models plus a local server,
  with launchers for Windows and macOS, and it has been tested to reproduce the original predictions
  exactly. It bundles training data and cached comparator outputs whose licence terms need review
  before they can be redistributed. Until then it is shared on request.

### Folder guide

| Folder | What it contains |
|---|---|
| `paper/` | Whitepaper and review summary, every figure, and the numbers files they are built from |
| `data/` | The derived result tables the paper and this README quote |
| `tool/` | Prediction code (`tool/fatev5.py`) and model notes |
| `dashboard/` | The offline dashboard page (`dashboard/index.html`) |
| `analysis/` | Method notes on the test splits, the physics descriptors, the spectra and the chemistry reviews |
| `tools/` | The safety scan run before each push, used by `CHECKLIST.md` |

File names in the paper that start with an agent's name in capitals (for example W-MODEL or W-SPECTRA) refer
to the agents' working folders, which are not part of this repository. Those citations are marked
`[not redistributed; ...]` so that no citation sends a reader to a file that is absent.

## Terms used

- **Endpoint**: one property being predicted, for example melting point or logKow.
- **EPI Suite**: the US EPA's standard estimation software for physical-chemical and fate properties.
  We use it as the comparator.
- **RMSE, % of naive**: RMSE (root-mean-square error) is the typical size of a prediction error.
  We divide it by the RMSE of a naive guess that always predicts the average of the training data.
  This shows skill independent of the endpoint's units. 100% means no skill; 50% means half the error
  of knowing nothing. Lower is better.
- **Morgan fingerprint and Tanimoto similarity**: a Morgan fingerprint encodes a structure as the set
  of small atom-centred fragments it contains. Tanimoto similarity is the share of fragments two
  structures have in common, from zero (none) to one (identical fingerprints).
- **Leak-free test set**: test compounds that have no close analogue in the training data, defined as
  no training compound at Tanimoto >= 0.40 on Morgan radius-2, 2048-bit fingerprints. "Leak" means
  information about a test compound reaching the model through a near-copy in the training data.
- **Bemis-Murcko scaffold**: the ring systems of a molecule plus the chains that link them, with side
  chains removed. Two compounds with the same scaffold share the same core skeleton.
- **Novel-scaffold cut**: a stricter test set that keeps only test compounds whose Bemis-Murcko scaffold
  does not appear among the training compounds.
- **Split by chemical-space cluster**: compounds are grouped into clusters of similar structures, and
  whole clusters go to either training or test, so the test set is not made of near-duplicates of
  training compounds.
- **Split-conformal interval**: an uncertainty interval whose width is set from the errors the model
  made on a separate calibration set of compounds it was not trained on.
- **Nominal vs empirical coverage**: the nominal level is the fraction of true values the interval is
  designed to contain. The empirical coverage is the fraction it actually contained on held-out test
  compounds. If empirical is below nominal, the interval is too narrow ("under-covers").
- **Confidence interval (CI)**: the range the score itself is likely to lie in, given the limited
  number of test compounds. If the interval for "% of naive" includes the no-skill value, skill is not
  established.
- **Frozen model**: the final trained model, saved and fixed so that every reported number comes from
  the same model.
- **AIMNet2**: a machine-learned interatomic potential used to relax each molecule's three-dimensional geometry and
  compute physics-based descriptors (the "physics" feature block).
- **Precision, recall and PR-AUC**: for yes/no calls with few positives. Precision is the share of
  predicted actives that are truly active; recall is the share of true actives that are found; PR-AUC
  (area under the precision-recall curve) summarises both across all thresholds. It is compared with
  the base rate, the share of actives in that group of compounds.
- **Familiarity bin**: test compounds grouped by how similar they are to their nearest training
  compound.
- **Pre-registered bar**: a pass/fail threshold fixed before the results were computed.
- **Bonferroni correction**: a stricter significance threshold used when many comparisons are made at
  once, so that some do not pass by chance.

## How to read the results

### How accuracy is reported

All errors are given as RMSE as a percentage of the naive guess (see [Terms used](#terms-used)).

Headline numbers come from the **leak-free** test compounds, and they come first everywhere in this
repository. Numbers on the full test set look better and are always labelled as such.

"Leak-free" depends on the fingerprint used. 57.4% of leak-free test rows still share a Bemis-Murcko
scaffold with a training compound of the same endpoint. The paper therefore also reports the stricter
novel-scaffold cut (`paper/whitepaper.md`, Sections 3 and 4.1).

### Fate endpoints, structure input (leak-free)

| endpoint | leak-free n | RMSE, % of the naive guess |
|---|---|---|
| vapor_pressure | 305 | 45% |
| water_solubility | 405 | 51% |
| logkow | 454 | 51% |
| koc | 27 | 52% |
| henry | 123 | 52% |
| melting_point | 822 | 53% |
| boiling_point | 368 | 53% |
| koh_gas | 30 | 58% |
| pka_basic | 54 | 74% |
| bcf | 52 | 88% |
| pka_acidic | 38 | 97% |
| logkoa | 3 | not scored (n < 20) |

Source: `data/fate_headline_leakfree.csv`.

How to read this table:

- Two rows are **not** evidence of skill. bcf (88%, 95% CI [68.3, 104.5]) and pka_acidic (97%,
  [82.1, 115.0]) have confidence intervals that cross 100%, so skill is not established for either.
  100% = no skill; acidic pKa is at 97%, and the model has no skill there on novel chemistry.
- "Leak-free" here means no training analogue at Tanimoto >= 0.40 **on Morgan r2/2048 fingerprints**.
  Under other fingerprints some of these compounds do have close analogues. The stricter test in the
  paper is the novel-scaffold cut. There, melting point and water solubility still beat EPI Suite and
  survive every control we applied.

### Spectrum only, no structure

This is a separate spectrum-only model, not the shipped fate model. It takes **one measured high-resolution
positive-mode electrospray (HR ESI+) MS/MS spectrum and no structure**. Leak-free error, % of naive,
with the confidence interval in brackets (`data/spectrum_only_leak_free.csv`):

| endpoint | spectrum only |
|---|---|
| water solubility | 74.7% [67.0, 82.4] |
| vapour pressure | 70.3% [56.4, 87.0] |
| logKow | 78.9% [70.1, 87.6] |
| melting point | 86.1% [79.3, 93.1] |

- When the structure is known, the same endpoints reach 46-60%.
- The spectrum-only intervals under-cover on novel chemistry (empirical 0.81-0.96 against a nominal
  0.90). Treat them as approximate.
- For acute lethality, a spectrum alone carries essentially no skill: 96% of naive, against 82% from
  the structure on the same 345 compounds (`data/hazard_spectrum_only_ld50.json`). The tool says so
  rather than printing a number.

### Hazard endpoints

- Hazard endpoints are trained on measured labels and are weaker than the fate endpoints.
- The receptor-activity tasks have rare positives. They are scored with precision, recall and PR-AUC
  against each familiarity bin's own base rate, never with accuracy (`data/hazard_results.json`).

## What changed after review (read this before the results)

This is the corrected version of the paper. In a second review round, agents that did not write the
text removed or qualified several claims made in the first draft. They are listed here so a reader
knows what was taken out before reading what was left in.

- **The fate model uses no spectra.** The frozen model that produces every fate number contains
  **zero spectral features**. It has exactly two feature blocks: structure descriptors (2265 columns)
  and AIMNet2 physics (31 columns), 2296 in total. The spectral models are separate runs.
- **Comparison with EPI Suite.** "Beats EPI Suite on six endpoints" is now: better on 6 of the 9
  comparisons that could be made, 4 of which survive a Bonferroni correction, with one clear loss
  (gas-phase OH rate constant) that we cannot explain. The difference is unresolved on 2 (bcf, henry).
  The denominator is nine because EPI Suite has no pKa module and logkoa has 3 leak-free rows.
- **Only two wins survive every control.** Of those four, only melting point and water solubility
  survive every control we applied, including a one-line control that clips EPI Suite's output to the
  range of the training labels.
- **BCF is not "at the measurement noise floor".** That claim compared two different statistics. No
  endpoint here is limited by noise in the measured labels: leak-free RMSE is 1.3x-7.6x the
  replicate-scatter floor (the error you would expect from disagreement between repeat measurements)
  across three estimators (`data/attack_noise_floor_ratio.csv`). BCF is simply an endpoint where skill
  is not established.
- **Physics descriptors.** Their contribution is shown on scaffolds already seen in training. Whether
  they help on new scaffolds is neither shown nor refuted at these sample sizes.
- **Spectra.** A measured spectrum adds nothing on top of a known structure. For acute lethality a
  spectrum alone carries essentially no skill.
- **Spectrum-only results are reported per endpoint**, with the model and ion mode named, because two
  defensible models disagree about which endpoints clear the pre-registered bar.

Each of these is traced to a named result file in the paper. The aggregated files behind them are in
`data/`.

Documents in `paper/` are the **v8 (corrected)** versions. The corrections are listed in the box at the
top of `paper/whitepaper.md`. All of them remove or narrow claims: withdrawn causal claims, a
multiplicity denominator, a corrected like-for-like comparison, a disclosed label gate, and the
statement that the frozen model contains no spectral features.

## Reproducing results

Every number in the paper is generated by code, not typed by hand.

### What you can reproduce with this repository alone

`paper/scribe_numbers.json` and `paper/scribe_addendum.json` are the two files every number in the
paper is read from, and both are included. From them you can rebuild the paper's numbers, figures and
PDF:

```bash
python -m venv .venv && . .venv/bin/activate
pip install matplotlib markdown xhtml2pdf
cd paper
python make_fig6.py           # -> figures_v5/fig6_toxicity.png, from scribe_numbers.json
python make_fig_q003.py       # -> figures_v5/figS_q003_corrected.png, from CRITIC/undefined_vs_gap_cells_q003.csv
python build_whitepaper.py    # -> whitepaper.md/.pdf and review_summary.md/.pdf
```

- This regenerates the paper, and so every number in it, from the numbers files. If a number in the
  text does not match the file it is read from, the build is wrong, and you can see where.
- `paper/make_fig7.py` is included for inspection but is not in the list above. It reads the inventory
  tables at their original size, and only their summaries are redistributed here (`data/inventory_*`),
  so Figure 7 is included pre-built.

### What you cannot reproduce from this repository alone

- **The numbers files themselves.** `paper/make_figures.py` and `paper/make_addendum.py` recompute them
  from the frozen per-row prediction tables listed in `paper/sources.json`. Those tables are large and
  are not redistributed here. `data/` contains the aggregated results they produce.
- **The split/label table** used for every number in the paper (`labels_v2.parquet  [not redistributed; VM-internal]`,
  built from the CompTox `exp_props` table). It defines the train/calibration/test partition and the
  held-out evaluation, and it carries third-party licence terms. Where a shipped aggregate carries the
  same numbers (for example `data/fate_vs_epi_suite.csv` for the model-versus-EPI-Suite comparison),
  the paper cites the aggregate and says so.
- **The models.** Rebuilding them also needs the model directories, which are not published yet (see
  [What is in this repository, and what is not](#what-is-in-this-repository-and-what-is-not)). There is
  no one-command reproduction of the models from this repository.
- **Predictions for new structures.** `dashboard/index.html` shows precomputed predictions for its
  example compounds only; predicting for a new structure needs the model package described above.

## Data and provenance

- **Labels** are experimental values from the US EPA CompTox Chemicals Dashboard.
- **Receptor potencies** are measured values from ChEMBL (CC BY-SA 3.0).
- **The NMR input mode** uses NMRexp (CC BY 4.0, doi:10.5281/zenodo.17296666).
- **Splits** are by chemical-space cluster, and the maximum Tanimoto similarity to the training set is
  recorded for every test compound.
- **A further validation set** is held out by a person and appears nowhere in this repository.
- **Compound identity** is matched by standardised InChIKey with stereochemistry kept, never by name or
  CAS number.

## Limitations

- **Physics descriptors** (from AIMNet2 geometry relaxations) help a little and not reliably. The set of
  endpoints where the gain has a confidence interval excluding zero changed with every defensible
  scoring choice. We report that instability rather than the best version of it.
- **Rebuilding the spectral representation** did not beat the previous one. That negative result is in
  the main text, not an appendix.
- **Transformation chemistry.** The model predicts the property change from a parent compound to its
  transformation product no better than the change between two arbitrary similar compounds.
- **A simple model already beats EPI Suite on several endpoints.** A LightGBM (a standard
  gradient-boosted tree model) on ten standard RDKit descriptors, trained on the same pool, beats EPI
  Suite on melting point, water solubility, boiling point and vapour pressure on the same leak-free
  rows (`data/attack_cheap_vs_epi.csv`). Much of the margin over EPI Suite is available to any modern
  learner.
- **Disputed, left open: how far EPI Suite's "home-turf" advantage extends.** PhysProp is the database
  EPI Suite was fitted on, so EPI Suite may do unusually well on PhysProp rows. Two defensible ways of
  slicing the data give different answers:
  - PhysProp rows that are also leak-free: melting point and water solubility keep a margin; boiling
    point, vapour pressure, logKow, Henry and BCF are not resolved (`data/label_source_attack.csv`).
  - ALL PhysProp test rows: melting point, water solubility AND vapour pressure keep a margin; boiling
    point, logKow and henry do not (`data/dg2_fairness_dedup.csv`).

  No agent settled which slice is right, so both are stated with the slice named and neither is
  promoted. A person should pick.
- **The EPI Suite comparison favours EPI Suite.** EPI Suite's training data overlap our label source, so
  its scores here are optimistic, while ours are leak-free. This asymmetry is stated wherever the
  comparison appears.
- **Undefined properties are refused.** Gas-phase and neutral-species properties are undefined for
  permanently charged or non-volatile species. The tool refuses those rather than predicting them.
  `data/undefined_vs_gap_cells.csv` gives the reasoning for each compound-class x endpoint cell.

## Licence

- The code, text and figures in this folder are released under the MIT License (`LICENSE` in this
  folder).
- This folder sits inside a fork of ScienceClaw (https://github.com/lamm-mit/scienceclaw). The rest of
  that repository is upstream's work under the Apache License 2.0 (`LICENSE` at the repository root)
  and is not relicensed by this folder. See `NOTICE`.
- The MIT grant covers our own work only. Tables in `data/` are aggregate results we computed, but the
  measurements behind them keep their source terms (US EPA CompTox, ChEMBL CC BY-SA 3.0, NMRexp CC BY
  4.0, and the other sources named in the paper). Third-party tools named here (EPI Suite, AIMNet2,
  RDKit) are under their own licences.
