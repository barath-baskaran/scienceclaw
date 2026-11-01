# Environmental fate and hazard prediction from a structure and/or a measured spectrum

Plata lab hackathon work on environmental fate and toxicity.

Give the tool a structure (SMILES), a structure plus an MS/MS spectrum, or **a spectrum alone**, and it
returns predicted environmental fate properties and selected hazard endpoints. Every prediction carries

- a split-conformal interval, reported with the **empirical** coverage measured on held-out test data
  beside its nominal level - never the nominal level on its own;
- a domain flag that distinguishes "far from anything we trained on" from "physically undefined for this
  species", which are different problems with different answers;
- the EPI Suite estimate as a comparator where EPI has a module for the endpoint;
- the features that drove the prediction.

The full method and the results, including the negative ones, are in `paper/whitepaper.pdf`.
A shorter read is `paper/review_summary.pdf`.

## How accuracy is reported here

Error is **RMSE as a percentage of a naive guess that always predicts the training mean**, so a reader
can tell skill from scale: 100% means no skill, 50% means half the error of knowing nothing.

Headline numbers are measured on **leak-free** test compounds - those with no training analogue at
Tanimoto >= 0.40 on Morgan radius-2, 2048-bit fingerprints - and those numbers come first everywhere in this repository. Numbers on the full test
set are higher-looking and are always labelled as such. "Leak-free" is fingerprint-dependent: 57.4% of
leak-free test rows still share a Bemis-Murcko scaffold with a training compound of the same endpoint, so
the paper also reports a stricter novel-scaffold cut (`paper/whitepaper.md`, Sections 3 and 4.1).

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

Source: `data/fate_headline_leakfree.csv`. Two of those rows are **not** evidence of skill: bcf (88%, 95% CI [68.3, 104.5]) and pka_acidic (97%, [82.1, 115.0]) have intervals that cross 100%, so skill is not established for either. "Leak-free" means no training analogue at Tanimoto >= 0.40 **on Morgan r2/2048 fingerprints**; under other fingerprints some of these compounds do have close analogues, so the stricter test in the paper is the novel-scaffold cut, where melting point and water solubility still beat EPI Suite and survive every control we applied. 100% = no skill; acidic pKa is at 97% and we say plainly that
the model has no skill there on novel chemistry.

From **one measured HR ESI+ MS/MS spectrum and no structure** - a separate spectrum-only model, not
the shipped fate model - the leak-free error is 74.7% of naive for water solubility [67.0, 82.4],
70.3% for vapour pressure [56.4, 87.0], 78.9% for logKow [70.1, 87.6] and 86.1% for melting point
[79.3, 93.1]
(`data/spectrum_only_leak_free.csv`), against 46-60% when the structure is known. The spectrum-only
intervals under-cover on novel chemistry (empirical 0.81-0.96 against a nominal 0.90) and should be
treated as approximate. For acute lethality a spectrum alone carries essentially no skill
(96% of naive against
82% from the structure on the same
345 compounds, `data/hazard_spectrum_only_ld50.json`), and the tool says so
rather than printing a number.

Hazard endpoints are trained on measured labels and are weaker than the fate endpoints; the
receptor-activity tasks have rare positives, so they are scored with precision, recall and PR-AUC
against each familiarity bin's own base rate, never with accuracy (`data/hazard_results.json`).

## Repository layout

| path | contents |
|---|---|
| `dashboard/` | The dashboard page: open `dashboard/index.html` in a browser to browse **precomputed predictions for a fixed set of example compounds**, offline. It cannot predict for a new structure on its own |
| `tool/` | Prediction code (`tool/fatev5.py`) and model notes |
| `paper/` | Whitepaper and review summary, every figure, and the single numbers file they are built from |
| `analysis/` | Method notes for the splits, the physics descriptors, the spectra and the chemistry reviews |
| `data/` | The derived result tables the paper and this README quote |
| `tools/` | The pre-push safety scan used by `CHECKLIST.md` |

## Can I run the tool from this repository?

**Not for new structures.** This repository is the public record of the work: the paper, the result
tables, the figures and the code. The trained models are **not** included, so the prediction code in
`tool/` and the server in `dashboard/tool/` have nothing to run. `tool/MODEL_NOTES.md` says what the
models contain and how they were frozen.

A runnable package (models plus a local server, with launchers for Windows and macOS) exists and has
been tested to reproduce the original predictions exactly. It is **not published yet**: it bundles
training data and cached comparator outputs whose licence terms need review before redistribution.
Until then it is shared on request.

## What this version corrected, and why it is worth reading first

This bundle is the corrected version of the paper. A second review round, run by agents that did not
write the text, removed or qualified several claims the first draft made. The short list, because a
reader should know what was taken out before reading what was left in:

- the frozen model that produces every fate number contains **zero spectral features** — it has exactly
  two feature blocks, structure descriptors (2265 columns) and AIMNet2 physics (31 columns), 2296 in
  total, and the spectral models are separate runs;
- "beats EPI Suite on six endpoints" is now "better on 6 of the 9 comparisons that could be made,
  4 of which survive a Bonferroni correction, with one clear loss (gas-phase OH rate constant) that
  we cannot explain"; the difference is unresolved on 2 (bcf, henry), and nine is the denominator
  because EPI Suite has no pKa module and logkoa has 3 leak-free rows;
- of those four, only melting point and water solubility survive every control we applied,
  including a one-line control that clips EPI Suite's output to the training-label range;
- BCF is not "at the measurement noise floor" — that compared two different statistics; no endpoint
  here is label-noise-limited (leak-free RMSE is 1.3x-7.6x the replicate-scatter floor across three
  estimators, `data/attack_noise_floor_ratio.csv`), and BCF is simply an endpoint where skill is not established;
- the physics block's contribution is demonstrated on scaffolds already seen in training; whether it
  helps extrapolation is neither shown nor refuted at these sample sizes;
- a measured spectrum adds nothing on top of a known structure, and for acute lethality a spectrum
  alone carries essentially no skill;
- the spectrum-only result is reported per endpoint, with the model and ion mode named, because two
  defensible models disagree about which endpoints clear the pre-registered bar.

Each of those is traced to a named result file in the paper, and the aggregated files behind them are
in `data/`.

## Reproduce a number from this repository

Every number in the paper is generated, not typed. To regenerate the paper's numbers, figures and PDF
from the frozen prediction tables:

**What you can reproduce with only this repository.** `paper/scribe_numbers.json` and
`paper/scribe_addendum.json` are the two files every number in the paper is read from, and they are
included. So:

```bash
python -m venv .venv && . .venv/bin/activate
pip install matplotlib markdown xhtml2pdf
cd paper
python make_fig6.py           # -> figures_v5/fig6_toxicity.png, from scribe_numbers.json
python make_fig_q003.py       # -> figures_v5/figS_q003_corrected.png, from CRITIC/undefined_vs_gap_cells_q003.csv
python build_whitepaper.py    # -> whitepaper.md/.pdf and review_summary.md/.pdf
```

`paper/make_fig7.py` is shipped for inspection but not in the list above: it reads the inventory tables at
their original scale, and only their summaries are redistributed here (`data/inventory_*`), so Figure 7
is included pre-built. That regenerates the paper, and therefore every number in it, from the numbers files. If a number in
the text does not match the file it is read from, the build is what is wrong, and you can see where.

**What you cannot reproduce from this repository alone.** `paper/make_figures.py` and `paper/make_addendum.py`
recompute the numbers files from the frozen per-row prediction tables listed in `paper/sources.json`.
Those tables are large and are not redistributed here; `data/` contains the aggregated results they
produce. Reproducing the models themselves additionally needs the model directories, which are
not published yet (see "Can I run the tool from this repository?" above). We would rather say this plainly than imply a
one-command reproduction that does not exist.

`dashboard/index.html` shows precomputed predictions for its example compounds only; predicting for a
new structure needs the model package described above.

## Data and provenance

Labels are experimental values taken from the US EPA CompTox Chemicals Dashboard; receptor potencies are
measured values from ChEMBL (CC BY-SA 3.0); the NMR input mode uses NMRexp (CC BY 4.0,
doi:10.5281/zenodo.17296666). Splits are by chemical-space cluster, and the maximum Tanimoto similarity
to the training set is recorded for every test compound. A further validation set is held out by a human
and appears nowhere in this repository.

Identity is by standardised InChIKey with stereochemistry retained - never by name or CAS number.

## Limitations we would want a reader to know

- Physics descriptors (AIMNet2 relaxations) help a little and not reliably: the set of endpoints where the
  gain has a confidence interval excluding zero changed with every defensible scoring choice. We report
  that instability rather than the best version of it.
- Rebuilding the spectral representation did not beat the previous one. That is a negative result and it
  is in the main text, not an appendix.
- The model does not know transformation chemistry: it predicts a parent-to-product change no better than
  a change between two arbitrary similar compounds.
- A LightGBM on ten standard RDKit descriptors, trained on the same pool, already beats EPI Suite on
  melting point, water solubility, boiling point and vapour pressure on the same leak-free rows
  (`data/attack_cheap_vs_epi.csv`). Much of the margin over EPI Suite is available to any modern learner.
- **Disputed, left open:** how far EPI Suite's "home-turf" caveat extends (rows from PhysProp, the
  database it was fitted on). On PhysProp rows intersected with leak-free, melting point and water
  solubility keep a margin, and boiling point, vapour pressure, logKow, Henry and BCF are not resolved
  (`data/label_source_attack.csv`); on ALL PhysProp test rows melting point, water solubility AND vapour
  pressure keep one and boiling point, logKow and henry do not (`data/dg2_fairness_dedup.csv`). Those are
  two defensible cells with different answers and no agent settled which is the right one, so both are
  stated with the cell named and neither is promoted. A human should pick.
- EPI Suite's training data overlap the label source, so the EPI comparator is optimistic; our numbers are
  leak-free. The asymmetry favours EPI and is stated wherever the comparison appears.
- Gas-phase and neutral-species properties are undefined for permanently charged or non-volatile species.
  The tool refuses those rather than predicting them, and `data/undefined_vs_gap_cells.csv` gives the
  reasoning per compound-class x endpoint cell.

## Licence

The code, text and figures in this folder are released under the MIT License (`LICENSE` in this
folder). This folder sits inside a fork of ScienceClaw (https://github.com/lamm-mit/scienceclaw); the
rest of that repository is upstream's work under the Apache License 2.0 (`LICENSE` at the repository
root) and is not relicensed by this folder. See `NOTICE`.

The MIT grant covers our own work only. Tables in `data/` are aggregate results computed by us, but the
measurements behind them keep their source terms (US EPA CompTox, ChEMBL CC BY-SA 3.0, NMRexp CC BY 4.0,
and the other sources named in the paper), and third-party tools named here (EPI Suite, AIMNet2, RDKit)
are under their own licences.


## What you cannot reproduce from this bundle

The split/label table used for every number in the paper (`labels_v2.parquet  [not redistributed; VM-internal]`, built from the
CompTox `exp_props` table) is **not redistributed here**: it is the file that defines the
train/calib/test partition and the held-out evaluation, and it carries third-party licence terms.
Citations in the paper that point at a working file which is not in this bundle are marked
`[not redistributed; ...]` so that no citation sends a reader to a file that is absent. Where a
shipped aggregate carries the same numbers (for example `data/fate_vs_epi_suite.csv` for the
model-versus-EPI-Suite comparison) the citation points at the aggregate and says so.

Documents in `paper/` are the **v8 (corrected)** versions. The corrections applied after the first
draft are listed in the box at the top of `paper/whitepaper.md`; they are all subtractive
(withdrawn causal claims, a multiplicity denominator, a corrected like-for-like comparison, a
disclosed label gate, and the statement that the frozen model contains no spectral features).
