# Model notes: the fate-property models and the frozen predictor (Run 3, v5)

These are the notes of W-MODEL, the agent that trained the fate-property models. They say what the
models predict, how they were trained and checked, how the predictor reacts to bad input, and which
files hold the results.

**What is and is not in this repository.** The trained models are not here, and neither are most of the
files named below. A file name followed by `[not redistributed; VM-internal]` stayed on the machine the
agents worked on. Names such as W-MODEL, W-SPACE, W-TOOL or W-SPECTRA are the agents and their
working folders on that machine (W-SPACE handled chemical-space splits and the definedness rules, W-TOOL
the dashboard, W-SPECTRA the spectra models). CRITIC is the reviewing agent. The code that loads the models is
`tool/fatev5.py`.

All numbers trace to files below; every script reruns with `python <script>`.

## Terms used in these notes

| term | meaning |
|---|---|
| frozen model | The trained model files were fixed at a recorded time and not retrained afterwards. MANIFEST.json lists a checksum (a fingerprint of the file contents) for every file, so any later change can be detected. |
| SP, S | The two model variants. **SP** uses structure descriptors plus AIMNet2 physics descriptors (the default). **S** uses structure descriptors only. |
| AIMNet2 | A neural-network model that approximates quantum-chemical calculations at much lower cost. Here it relaxes each molecule's three-dimensional geometry and computes physics descriptors (charges, energies and similar) from it. |
| nn_sim_train | The highest Tanimoto similarity between the query compound and any training compound, using Morgan fingerprints (a bit-string recording which small substructures a molecule contains). Low values mean the compound is unlike anything the model was trained on. |
| leak-free | A test compound with no close analogue in the training set (similarity below the threshold given under "Data handling"). Results on these compounds show how the model does on new chemistry. |
| calib | The calibration set: compounds kept apart from training and used only to size the prediction intervals. |
| split-conformal interval | A prediction range sized from the model's actual errors on the calibration set, so that a chosen fraction of measured values (the nominal level) should fall inside. **Mondrian** means the sizing is done separately in each similarity bin. **Normalised** means each interval is also scaled by a second model's estimate of how hard that compound is to predict. |
| empirical coverage | The fraction of test compounds whose measured value actually fell inside the interval. It is reported next to the nominal level because the two can differ. |
| % of naive | Model error (RMSE) divided by the error of always guessing the mean of the training labels. Equal to the naive error means no skill; lower is better. |
| cluster bootstrap | Confidence intervals obtained by resampling whole clusters of similar compounds rather than single compounds, so near-duplicates are not counted as independent evidence. |
| pre-registered | The choice was written down before any test result was seen, so it could not be tuned to the test set. |
| TreeSHAP | A method that splits a tree model's prediction into a contribution from each input feature. |
| definedness, category B | W-SPACE rules for whether a property physically exists for a species (for example, a boiling point for a permanent salt does not). Category B cells carry a caveat rather than a refusal. |

## Endpoints and units

There are 12 endpoints, in labels_v2 units:

| endpoint | unit |
|---|---|
| logkow | log10 |
| water_solubility | log10 mol/L |
| vapor_pressure | log10 mmHg |
| henry | log10 atm·m3/mol |
| boiling_point, melting_point | °C |
| koc, bcf | log10 L/kg |
| logkoa | log10 |
| koh_gas | log10 cm3/molecule/s |
| pka_acidic, pka_basic | pKa units |

## The deliverable: `frozen_v5/` [not redistributed; VM-internal]

Frozen 2026-10-31 21:32 EDT; MANIFEST.json = sha256 of every file.

```python
import sys; sys.path.insert(0, 'W-MODEL/frozen_v5'); from fatev5 import predict
predict('CCOC(=O)c1ccccc1')                 # physics from the GPU table (27k labelled structures)
predict(smi, compute_physics=True)          # unseen structure: AIMNet2 CPU relaxation (~10-60 s)
predict(smi, physics=<compute_physics dict>)
predict(smi, allow_struct_only=True)        # explicit opt-in; flagged NO_PHYSICS (the only route for ions)
```

- Command line: `python frozen_v5/predict.py  [not redistributed; VM-internal]` "SMILES" [--compute-physics|--allow-struct-only].
- Interface used by the dashboard agent (W-TOOL): model.json `impl = fate_model:FateModelV5`.

**Variants shipped.** **SP** = structure + AIMNet2 physics (default). **S** = structure only, trained on ALL
defined rows including ions (`frozen_v5_sall`), used only when the caller asks for it explicitly.

### It fails loudly on bad input

The acceptance tests (test_frozen_v5.py → test_frozen_v5.log, all PASS) check that the predictor stops with
a clear error instead of returning a number:

- unparseable or empty SMILES → `InvalidStructureError`;
- no physics and no opt-in → `MissingPhysicsError`, naming the 31 columns and the command to compute them;
- a physics dict missing a column that is always present → an error naming the missing columns (columns
  for absent elements, such as q_N_min_e, may be None, exactly as in training);
- physics_ok=False → an error with the reason;
- a charged species → an error explaining that physics is not defined for it.

### What it returns for each endpoint

| field | meaning |
|---|---|
| `value` | The prediction, or None when the property is physically UNDEFINED for the species (W-SPACE domain_rules v3, frozen copy `domain_rules_v5.py  [not redistributed; VM-internal]`) |
| `interval` | 90 % normalised Mondrian split-conformal interval |
| `interval_plain_mondrian` | The same without the difficulty scaling |
| `empirical_coverage_test_this_bin` (+ plain), `n_test_this_bin` | Coverage measured on test compounds in the same similarity bin, and how many there were |
| `nn_sim_train` + bin, `nn_sim_endpoint_train` | Similarity to the nearest training compound, overall and for this endpoint |
| `domain_flag` | OUT_OF_DOMAIN <0.3, EXTRAPOLATING <0.5, otherwise IN_DOMAIN; also OUT if the compound has an element never seen in that endpoint's training set |
| `flags` | Warnings |
| `definedness_category` | B = caveat, e.g. pKa with no ionisable site |
| `measured_in_training_set` | Whether a measured value was in the training data |
| `attribution_block_shares` + `attribution_top` | TreeSHAP over the 3-seed bag; Morgan bits are translated into the fragments present in the molecule, and physics descriptors are described in words |
| `epi_comparator` | The EPI Suite estimate from W-TOOL's structure-matched cache; live fetch with `epi_live=True` (rate-limited, identity-checked) |
| `naive_train_mean` | The training-label mean that "% of naive" is measured against |

## Data handling (train_v5.py)

1. labels_v2 is used with its split as given (never re-split). Water solubility: rows removed by the miscibility gate.
2. Rows where the property is physically UNDEFINED according to W-SPACE `definedness()` are dropped (e.g. BP/logKow
   of quaternary ammonium), and so are rows with pka_basic > 14 (OPERA C–H acidities; flagged by CRITIC). Counts are in results.json.
3. **One row per (endpoint, InChIKey)**, using the median label. labels_v2 has one row per DTXSID (an EPA DSSTox
   substance identifier), and 5 % of rows were duplicates with conflicting values (flagged by CRITIC). The run before
   de-duplication is kept as `v5_main_nodedup/` [not redistributed; VM-internal] as a sensitivity check.
4. Leak-free = the `leak_free` column of W-SPACE `quarantine_v3.parquet  [not redistributed; VM-internal]` (max Tanimoto to the v2.1
   training set < 0.40 for every drawing of the compound), joined on (skeleton, endpoint). Sensitivity versions: `lf_v2`, `lf_ep`.
   By construction no leak-free row has nn_sim ≥ 0.40.
5. Ablation rows (runs that compare variants with and without a feature block): every variant in a run uses the same
   compounds. Rows lacking any block are dropped from all variants; counts per nn bin are in results.json
   `dropped_missing_blocks`. physics_v1 has no charged species, so the S/SP headline comparison excludes ions;
   `v5_sall/` [not redistributed; VM-internal] gives S on all defined rows.
6. Model: a bag of LightGBM models with 3 seeds (lr 0.05, 63 leaves, ff 0.3, bagging 0.8), early stopping on a
   cluster-grouped 15 % inner hold-out of TRAIN, then refit on train. Calib is used only for the conformal intervals.
7. Intervals (90 %): global; Mondrian per nn_sim bin; and **normalised Mondrian** (|r|/σ(x), where σ is a LightGBM model
   of log|OOF residual| from 5-fold cluster-grouped cross-validation on train). Normalised Mondrian was pre-registered as
   the shipped interval before any v5 test number was seen.
8. Error = RMSE and RMSE as % of the naive guess (mean of the run's training labels). Every CI is a cluster bootstrap
   (labels_v2 clusters, 1000×), paired for contrasts.

## Results (final, de-duplicated): files

| file | content |
|---|---|
| `v5_main/results.json  [not redistributed; VM-internal]`, `test_predictions.parquet  [not redistributed; VM-internal]`, `calib_predictions.parquet  [not redistributed; VM-internal]` | S vs SP, 12 endpoints, all metrics, subsets and bins |
| `v5_main/headline_leakfree.csv  [not redistributed; VM-internal]` | leak-free first, then lf_v2, then full: n, RMSE, % naive + CI, SP−S CI, coverage |
| `v5_main/bins.csv  [not redistributed; VM-internal]` | per nn_sim bin (<0.3, 0.3-0.5, 0.5-0.7, ≥0.7): n, % naive + CI, coverage and width of 3 interval types |
| `v5_main/vs_epi.csv  [not redistributed; VM-internal]` | SP vs EPI Suite on IDENTICAL rows (EPI estimated values only, identity-matched) |
| `v5_main/class_coverage.csv  [not redistributed; VM-internal]`, `class_coverage_summary.csv  [not redistributed; VM-internal]` | coverage per W-SPACE compound class (n≥15), binomial test + BH (Benjamini-Hochberg correction for many tests) |
| `v5_main/fig1..fig4*.png` [not redistributed; VM-internal] | leak-free vs EPI; error by bin; coverage (global vs Mondrian vs normalised, plus class failures); parity plots |
| `v5_sall/` [not redistributed; VM-internal] | S on all defined rows (including ions), same tables |
| `v5_spec_{pos,neg,ei}/`, `v5_spectra_summary.csv  [not redistributed; VM-internal]`, `fig5_spectra_ablation.png  [not redistributed; VM-internal]` | S/SP/SPX/SX/X/XM on compounds with a W-SPECTRA v3.1 block |

### Key findings

Numbers are from the files above; see also the run notes.

- Leak-free SP error is 45–58 % of naive for MP, logKow, WS, BP, VP, Henry, Koc and kOH; BCF 88 %; pKa-basic 74 %;
  pKa-acidic 97 % (no skill).
- SP beats EPI Suite on identical leak-free rows for MP, logKow, WS, BP and VP (CIs exclude 0); EPI AOPWIN beats us on kOH.
- Physics adds 1–7 points of % naive. The CI excludes 0 only for MP, BP, pKa-a and pKa-b, and that set changed with
  model version and label cleaning.
- Normalised Mondrian intervals: 0/178 class×endpoint cells under-covered (vs 14 for plain Mondrian and 11 for global),
  and they are narrower on most bins.
- Spectra add nothing measurable to structure (+physics). Spectrum-only has real skill (fragments beat precursor mass + ion type).

## Older material

frozen_v2/ (run 2 frozen), frozen_v3, frozen_v4 + results_v4.json (pre-run-3 rebuild), `v5_main_prefilter/` [not redistributed; VM-internal] (before the
undefined-row filter; discarded), `*_nodedup/` [not redistributed; VM-internal] (before de-duplication; sensitivity only).

## Added after the freeze (analysis of the frozen model; the model itself did not change)

| file | content |
|---|---|
| `v5_main/learner_control_ridge.csv  [not redistributed; VM-internal]` (`learner_control_v5.py  [not redistributed; VM-internal]`) | Same rows and split, ridge regression instead of LightGBM: physics helps a weak learner more consistently, but LightGBM-S beats ridge-SP everywhere |
| `v5_main/henry_consistency.json  [not redistributed; VM-internal]` (`henry_consistency_v5.py  [not redistributed; VM-internal]`) | Henry constant computed from predicted VP/WS; a blend chosen on calib (0.75/0.25) lowers leak-free Henry error 52.1 → 49.2 % naive. Not shipped; reported per compound as `thermo_consistency` |
| `v5_main/sigma_terciles.csv  [not redistributed; VM-internal]` (`sigma_check_v5.py  [not redistributed; VM-internal]`) | The difficulty model ranks real error correctly; the shipped interval holds ~0.90 in each difficulty tercile, while plain Mondrian gives 0.99 on easy and 0.78 on hard compounds |
| `inventory_predictions_v5.parquet  [not redistributed; VM-internal]`, `_summary.json  [not redistributed; VM-internal]` (`predict_inventory_v5.py  [not redistributed; VM-internal]`) | Frozen SP run over the EPA-inventory AIMNet2 table (neutral physics_ok rows; re-run as shards arrive). Intervals are much wider than on the test set at equal nn_sim (BP 398 vs 73 °C median) |
| `test_frozen_v5.py  [not redistributed; VM-internal]` / `.log` [not redistributed; VM-internal] | Acceptance tests of the fail-loudly behaviour (all PASS) |
| `v5_stack/` + `decision.csv  [not redistributed; VM-internal]` (`build_aux_v5.py  [not redistributed; VM-internal]`, `train_v5.py  [not redistributed; VM-internal]` --tag stack --variants SP,SPA, `eval_stack_v5.py  [not redistributed; VM-internal]`) | Pre-registered multi-endpoint stacking (feeding predictions for one endpoint into another); the decision rule on calib fires only for kOH and logKoa. Not shipped (candidate for v5.1) |
| `v5_dropB/` (`train_v5.py  [not redistributed; VM-internal]` --tag dropB --drop-B) | Sensitivity run without W-SPACE category-B label rows; conclusions unchanged |

**Predictor change after the freeze** (code only; the trained boosters are unchanged and MANIFEST was refreshed): the
predictor now refuses W-SPACE category-B cells marked display='refuse' (e.g. VP/logKow of sulfonic acids and salts),
following BB's expert note Q-003. It also reports `thermo_consistency`.
