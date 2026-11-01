# W-MODEL — fate-property models and the frozen predictor (Run 3, v5)

All numbers trace to files below; every script reruns with `python <script>`.
Endpoints (12, labels_v2 units): logkow (log10), water_solubility (log10 mol/L), vapor_pressure (log10 mmHg),
henry (log10 atm·m3/mol), boiling_point / melting_point (°C), koc / bcf (log10 L/kg), logkoa (log10),
koh_gas (log10 cm3/molecule/s), pka_acidic / pka_basic (pKa units).

## THE DELIVERABLE: `frozen_v5/` [not redistributed; VM-internal] (frozen 2026-10-31 21:32 EDT; MANIFEST.json = sha256 of every file)
```python
import sys; sys.path.insert(0, 'W-MODEL/frozen_v5'); from fatev5 import predict
predict('CCOC(=O)c1ccccc1')                 # physics from the GPU table (27k labelled structures)
predict(smi, compute_physics=True)          # unseen structure: AIMNet2 CPU relaxation (~10-60 s)
predict(smi, physics=<compute_physics dict>)
predict(smi, allow_struct_only=True)        # explicit opt-in; flagged NO_PHYSICS (the only route for ions)
```
CLI: `python frozen_v5/predict.py  [not redistributed; VM-internal]` "SMILES" [--compute-physics|--allow-struct-only].
W-TOOL seed interface: model.json `impl = fate_model:FateModelV5`.

**Fails loudly** (test_frozen_v5.py → test_frozen_v5.log, all PASS): unparseable/empty SMILES → `InvalidStructureError`;
no physics and no opt-in → `MissingPhysicsError` naming the 31 columns and the command to compute them; a physics dict
lacking an always-present column → error naming them (element-absent columns such as q_N_min_e may be None, exactly as
in training); physics_ok=False → error with the reason; charged species → error explaining physics is not defined for them.

Per endpoint it returns: `value` (None when the property is physically UNDEFINED for the species — W-SPACE
domain_rules v3, frozen copy `domain_rules_v5.py  [not redistributed; VM-internal]`), `interval` (90 % normalised Mondrian split-conformal),
`interval_plain_mondrian`, `empirical_coverage_test_this_bin` (+ plain), `n_test_this_bin`, `nn_sim_train` + bin,
`nn_sim_endpoint_train`, `domain_flag` (OUT_OF_DOMAIN <0.3, EXTRAPOLATING <0.5, IN_DOMAIN; OUT if an element was never
seen in that endpoint's training set), `flags`, `definedness_category` (B = caveat, e.g. pKa with no ionisable site),
`measured_in_training_set`, `attribution_block_shares` + `attribution_top` (TreeSHAP over the 3-seed bag; Morgan bits
translated into the fragments present in the molecule; physics descriptors described), `epi_comparator`
(W-TOOL's structure-matched EPI cache; live fetch with `epi_live=True`, rate-gated, identity-checked), `naive_train_mean`.

Variants shipped: **SP** = structure + AIMNet2 physics (default). **S** = structure only, trained on ALL defined rows
including ions (`frozen_v5_sall`), used only on explicit opt-in.

## Data handling (train_v5.py)
1. labels_v2, split as given (never re-split). Water solubility: miscibility gate rows removed.
2. Rows physically UNDEFINED per W-SPACE `definedness()` dropped (e.g. BP/logKow of quaternary ammonium), and pka_basic > 14
   (OPERA C–H acidities; CRITIC). Counts in results.json.
3. **One row per (endpoint, InChIKey)**, median label (labels_v2 is per DTXSID; 5 % of rows were duplicates with conflicting
   values; CRITIC). Pre-dedup run kept as `v5_main_nodedup/` [not redistributed; VM-internal] (sensitivity).
4. Leak-free = W-SPACE `quarantine_v3.parquet  [not redistributed; VM-internal]` `leak_free` (max Tanimoto to v2.1 train < 0.40 for every drawing), joined
   on (skeleton, endpoint). Sensitivities `lf_v2`, `lf_ep`. By construction no leak-free row has nn_sim ≥ 0.40.
5. Ablation rows: every variant in a run uses the same compounds (rows lacking any block are dropped from all; counts per
   nn bin in results.json `dropped_missing_blocks`). physics_v1 has no charged species, so the S/SP headline excludes ions;
   `v5_sall/` [not redistributed; VM-internal] gives S on all defined rows.
6. Model: 3-seed LightGBM bag (lr 0.05, 63 leaves, ff 0.3, bagging 0.8), early stopping on a cluster-grouped 15 % inner
   hold-out of TRAIN, refit on train. Calib is used only for conformal.
7. Intervals (90 %): global; Mondrian per nn_sim bin; **normalised Mondrian** (|r|/σ(x), σ = LightGBM on log|OOF residual|
   from 5-fold cluster-grouped CV on train) — pre-registered as shipped before any v5 test number was seen.
8. Error = RMSE and RMSE as % of the naive guess (mean of the run's training labels); cluster bootstrap (labels_v2 cluster,
   1000×) for every CI; paired for contrasts.

## Results (final, dedup) — files
| file | content |
|---|---|
| `v5_main/results.json  [not redistributed; VM-internal]`, `test_predictions.parquet  [not redistributed; VM-internal]`, `calib_predictions.parquet  [not redistributed; VM-internal]` | S vs SP, 12 endpoints, all metrics/subsets/bins |
| `v5_main/headline_leakfree.csv  [not redistributed; VM-internal]` | leak-free first, then lf_v2, full: n, RMSE, % naive + CI, SP−S CI, coverage |
| `v5_main/bins.csv  [not redistributed; VM-internal]` | per nn_sim bin (<0.3, 0.3-0.5, 0.5-0.7, ≥0.7): n, % naive + CI, coverage & width of 3 interval types |
| `v5_main/vs_epi.csv  [not redistributed; VM-internal]` | SP vs EPI Suite on IDENTICAL rows (EPI estimated values only, identity-matched) |
| `v5_main/class_coverage.csv  [not redistributed; VM-internal]`, `class_coverage_summary.csv  [not redistributed; VM-internal]` | coverage per W-SPACE compound class (n≥15), binomial + BH |
| `v5_main/fig1..fig4*.png` [not redistributed; VM-internal] | leak-free vs EPI; error by bin; coverage (global vs Mondrian vs normalised + class failures); parity |
| `v5_sall/` [not redistributed; VM-internal] | S on all defined rows (incl. ions), same tables |
| `v5_spec_{pos,neg,ei}/`, `v5_spectra_summary.csv  [not redistributed; VM-internal]`, `fig5_spectra_ablation.png  [not redistributed; VM-internal]` | S/SP/SPX/SX/X/XM on compounds with a W-SPECTRA v3.1 block |

Key findings (numbers from the files above; see also the run notes):
- Leak-free SP error 45–58 % of naive for MP, logKow, WS, BP, VP, Henry, Koc, kOH; BCF 88 %; pKa-basic 74 %; pKa-acidic 97 % (no skill).
- SP beats EPI Suite on identical leak-free rows for MP, logKow, WS, BP, VP (CIs exclude 0); EPI AOPWIN beats us on kOH.
- Physics adds 1–7 points of % naive; CI excludes 0 only for MP, BP, pKa-a, pKa-b, and that set changed with model version and label cleaning.
- Normalised Mondrian intervals: 0/178 class×endpoint cells under-covered (vs 14 plain Mondrian, 11 global) and narrower on most bins.
- Spectra add nothing measurable to structure(+physics); spectrum-only has real skill (fragments beat precursor mass + ion type).

## Older material
frozen_v2/ (run 2 frozen), frozen_v3, frozen_v4 + results_v4.json (pre-run-3 rebuild), `v5_main_prefilter/` [not redistributed; VM-internal] (before the
undefined-row filter; discarded), `*_nodedup/` [not redistributed; VM-internal] (before dedup; sensitivity only).

## Added after the freeze (analysis on the frozen model; no model change)
| file | content |
|---|---|
| `v5_main/learner_control_ridge.csv  [not redistributed; VM-internal]` (`learner_control_v5.py  [not redistributed; VM-internal]`) | same rows/split, ridge instead of LightGBM: physics helps a weak learner more consistently, but LightGBM-S beats ridge-SP everywhere |
| `v5_main/henry_consistency.json  [not redistributed; VM-internal]` (`henry_consistency_v5.py  [not redistributed; VM-internal]`) | Henry from predicted VP/WS; calib-chosen blend 0.75/0.25 lowers leak-free Henry 52.1 → 49.2 % naive; not shipped, reported per compound as `thermo_consistency` |
| `v5_main/sigma_terciles.csv  [not redistributed; VM-internal]` (`sigma_check_v5.py  [not redistributed; VM-internal]`) | difficulty model ranks real error; shipped interval holds ~0.90 per difficulty tercile, plain Mondrian 0.99 easy / 0.78 hard |
| `inventory_predictions_v5.parquet  [not redistributed; VM-internal]`, `_summary.json  [not redistributed; VM-internal]` (`predict_inventory_v5.py  [not redistributed; VM-internal]`) | frozen SP over the EPA-inventory AIMNet2 table (neutral physics_ok rows; rerun as shards land). Intervals much wider than on test at equal nn_sim (BP 398 vs 73 °C median) |
| `test_frozen_v5.py  [not redistributed; VM-internal]` / `.log` [not redistributed; VM-internal] | acceptance tests of the fail-loudly behaviour (all PASS) |
| `v5_stack/` + `decision.csv  [not redistributed; VM-internal]` (`build_aux_v5.py  [not redistributed; VM-internal]`, `train_v5.py  [not redistributed; VM-internal]` --tag stack --variants SP,SPA, `eval_stack_v5.py  [not redistributed; VM-internal]`) | pre-registered multi-endpoint stacking; calib rule fires only for kOH, logKoa; not shipped (v5.1 candidate) |
| `v5_dropB/` (`train_v5.py  [not redistributed; VM-internal]` --tag dropB --drop-B) | sensitivity without W-SPACE category-B label rows; conclusions unchanged |

Predictor change after freeze (code only, boosters unchanged, MANIFEST refreshed): refuses W-SPACE category-B cells with
display='refuse' (e.g. VP/logKow of sulfonic acids and salts) per BB expert note Q-003; also reports `thermo_consistency`.
