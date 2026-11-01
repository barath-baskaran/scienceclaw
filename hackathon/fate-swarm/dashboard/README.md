# The dashboard (run 3)

The dashboard is a single web page that shows the models' predictions for a compound, with the
uncertainty and the comparison to EPI Suite laid out row by row. This file explains how to open it,
what each row means, which files build it, and its known limitations.

Names such as W-TOOL (the agent that built the dashboard), W-MODEL, W-SPECTRA, W-TOX, W-SPACE, W-PHYSICS,
W-TP, CRITIC, SCRIBE and the READER and OPS agents are the agents that did each part of the work. File names marked
`[not redistributed; VM-internal]` stayed on the machine the agents worked on and are not in this repository.

## Open it

**Open:** `dashboard/index.html`. It is one file that works offline: no CDN and no network access when it
renders. It shows the precomputed examples, the spectrum-only examples, the test results, and any results
file you open with it.

**Predict anything new:** run `bash start_dashboard.sh  [not redistributed; VM-internal]`, then open http://127.0.0.1:8765.
This needs the trained models, which are not in this repository (see the main `README.md`). The server
listens only on your own machine (localhost). Physics descriptors are computed on CPU in about 1 min, and
EPI Suite is queried live with an identity check.

**Command line:** `dashboard/tool/wtool_backend.py` --smiles "CCO" [--no-physics] [--epi-live] --out p.json, then load
the output with "Open results file…" in the page. `--spectrum spec.json  [not redistributed; VM-internal]` gives spectrum-only mode, and
`--file x.csv  [not redistributed; VM-internal]` gives batch mode.

## Status at the freeze

"Freeze" is the point after which the models were no longer changed.

- Models: W-MODEL frozen_v5 (fate properties), W-SPECTRA spectrum_only_v31 (spectrum-only), W-TOX r3/model_frozen_v3
  (hazard; trained on measured labels).
- Checks: check_v3.py passes on 201/201 rows with 0 JS errors and meets WCAG AA (the web accessibility standard for
  text contrast).
- Usability: two independent reviews (W-TP ×2, W-MODEL); every issue found was fixed.
- Demo: DEMO_SCRIPT.md (for a person to re-record). The automated screen recording was removed from this repository
  on 2026-11-01, because its final seconds showed an internal status console, and it is not redistributed.
- Repository copy: repo_dashboard/ (→ SCRIBE repo/dashboard/; SCRIBE is the agent that assembled this repository).

## What each property row shows

- **The value** in model units, plus a conversion to everyday units with its formula (mg/L, Pa, half-life in air, ...).
- **Likely range:** the split-conformal interval and a range bar. A split-conformal interval is a range sized from the
  model's actual errors on compounds it was not trained on. The bar uses shapes: box = range, ◆ = estimate,
  ○ = EPI Suite, × = measured.
- **Range held in testing:** the empirical coverage, meaning how often the range actually contained the measured value
  for test chemicals in the same novelty band, with n. It is always printed next to the nominal level (the coverage the
  range was designed for), because the two can differ.
- **New to the model?** ● familiar / ▲ somewhat new / ✖ new. This comes from nn_sim_train: the Tanimoto similarity
  (Morgan r2 fingerprints, a bit-string of the small substructures in a molecule) between the compound and its nearest
  training compound. Spectrum mode uses spectral cosine similarity instead.
- **EPI Suite:** an estimate whose structure has been checked against the input. For pKa the row says
  "no EPI comparator", never a blank.
- **Details (click the row):**
  - block shares (how much of the prediction came from structure / quantum chemistry / spectrum) and the top SHAP
    features in plain words (SHAP splits a prediction into contributions from each input feature);
  - the model's test error as % of the naive guess (the error of always predicting the training mean), overall and in
    this novelty band;
  - caveats.
- **Refusals:** where the W-SPACE rule `domain_rules.category()` returns `refuse`, the row shows "⊘ Not physically defined
  for this compound" (or "Defined only for a neutral form that does not exist at environmental pH") with the reason, and
  no number. `caveat` cells show the number plus a ▲ headline and the reason.
- **Salts:** W-SPACE `species()` strips counter-ions and neutralises the structure. The models, physics and EPI Suite run
  on the parent compound, and the page says so. Whether a property is defined is judged on the structure as entered.
- **Consistency check:** the Henry constant implied by the predicted vapour pressure and water solubility is compared
  with the directly predicted Henry constant (READER-1). A warning appears if they differ by more than 1 log unit.
- **Hazard rows:** ER/AR (estrogen and androgen receptor activity) calls read "inconclusive" when the range crosses 0.5,
  and the base rate (the fraction of actives in the data) is given. LD50 is shown as a GHS band (the hazard categories
  of the Globally Harmonized System). Wording follows W-TOX review R4.

## Files

| file | what it does |
|---|---|
| `dashboard/build_v3.py` | Builds `index.html`. It runs the frozen models on the examples at build time and embeds the results as `data_v3.json  [not redistributed; VM-internal]`. `--quick` skips physics. |
| `dashboard/v3_head.html`, `dashboard/v3/*.js` | The page itself: HTML/CSS, core helpers, rendering, UI, start-up. Plain ES5-style JavaScript with no libraries. |
| `dashboard/build_good.py` → `good_v3.json`, `tool/card_stats.json` | The "How good is it?" panel: test RMSE as % of naive (the training mean), leak-free first (W-SPACE quarantine_v3), by nn_sim bin, against EPI Suite on the same rows. Also the n, coverage and skill shown on each card. |
| `dashboard/check_v3.py` → `dashboard/docs/screenshots/check_report.json` | Checks in a real Chromium browser: every row has its required fields or a refusal with a reason; no JS errors; no overflow at 1280/390 px; WCAG AA contrast; clear messages when offline or when input is missing. |
| `tool/wtool_backend.py` | Runs the frozen models, physics (W-PHYSICS `compute_physics`, timeout 240 s), EPI Suite and the W-SPACE rules. It contains no model logic itself. |
| `tool/wtool_postproc.py` | The W-SPACE category rules, plus W-TOX's warning for weak-acid pKa. |
| `tool/models_registry.json` | The frozen models used, in priority order. |
| `tool/depict.py` | Draws structures as SVG. RDKit's own drawer needs libXrender, which is missing on the VM. |
| `tool/shoot.py`, `tool/review_pack.sh` | Screenshots and checks in headless Chromium (QtWebEngine), and a text review pack for reviewers. |
| `tool/cvd_check.py` → `dashboard/docs/screenshots/cvd_report.json` | Colour-blindness simulation (Machado 2009): the colour difference (ΔE) between every pair of colours that carry meaning. |
| `tool/record_demo.py` | Records the demo automatically to mp4, following `DEMO_SCRIPT.md`. |
| `epi_extract.py`, `build_epi_canonical.py` → `epi_comparator_v3.parquet  [not redistributed; VM-internal]`, `_metrics.json/.md  [not redistributed; VM-internal]` | **The reference EPI Suite comparator for run 3.** It reproduces W-LADDER's extraction exactly. |

## Limitations (measured)

- Spectrum-only mode: the intervals under-cover at nominal 90% (empirical 0.85–0.88 for logKow/MP/VP/WS/Henry, from
  CRITIC's audit and W-SPECTRA's manifest), meaning they contain the measured value less often than designed. The page
  prints the empirical value. Spectral similarity does not track error, so no novelty call is made in this mode.
- Hazard classifiers show PR-AUC (area under the precision-recall curve) against the base rate in each novelty band,
  never accuracy.
- Physics computed at prediction time is approximate for flexible molecules (≥4 rotatable bonds). The page labels this,
  following OPS-2's parity check.
- The page opened as a file (file://) cannot compute new structures, because there is no Python in the browser. It says
  so clearly and gives the start command.
- EPI Suite needs internet. Offline, the row says "EPI web service not reachable".
- EPI Suite's test errors are optimistic, because its training data overlap CompTox.

Note: the "How good is it?" table scores every method on the rows that all listed methods share, so its n can be equal
to or smaller than the paper's (e.g. water_solubility leak-free n=377 vs 405). The water_solubility naive mean there uses
the ungated training set (0.38% effect, in the conservative direction).
