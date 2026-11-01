# W-TOOL: the dashboard (run 3)

**Status at freeze.**
- Models: W-MODEL frozen_v5 (fate), W-SPECTRA spectrum_only_v31 (spectrum-only), W-TOX r3/model_frozen_v3 (hazard; measured labels).
- Checks: check_v3.py passes on 201/201 rows with 0 JS errors and WCAG AA.
- Usability: two independent reviews (W-TP ×2, W-MODEL); every issue fixed.
- Demo: DEMO_SCRIPT.md (human re-record). The automated screen recording was removed from this repo
  on 2026-11-01 (its final seconds showed an internal status console) and is not redistributed.
- Repo copy: repo_dashboard/ (→ SCRIBE repo/dashboard/).

**Open:** `dashboard/index.html`. It is one offline file: no CDN and no network at render time. It shows the precomputed examples, the spectrum-only examples, the test results, and any results file you open.
**Predict anything new:** run `bash start_dashboard.sh  [not redistributed; VM-internal]`, then open http://127.0.0.1:8765. The server binds to localhost only. Physics is computed on CPU in about 1 min, and EPI Suite is queried live with an identity check.
**Command line:** `dashboard/tool/wtool_backend.py` --smiles "CCO" [--no-physics] [--epi-live] --out p.json. Then use "Open results file…" in the page. `--spectrum spec.json  [not redistributed; VM-internal]` gives spectrum-only mode, `--file x.csv  [not redistributed; VM-internal]` gives batch mode.

## What each property row shows
- The value in model units, plus an everyday-unit conversion with its formula (mg/L, Pa, half-life in air, ...).
- **Likely range:** the split-conformal interval and a range bar. The bar uses shapes: box = range, ◆ = estimate, ○ = EPI Suite, × = measured.
- **Range held in testing:** the empirical coverage on test chemicals in the same novelty band, with n, always printed next to the nominal level.
- **New to the model?** ● familiar / ▲ somewhat new / ✖ new, from nn_sim_train (Tanimoto, Morgan r2). Spectrum mode uses spectral cosine instead.
- **EPI Suite:** an identity-checked estimate. For pKa the row says "no EPI comparator", never a blank.
- **Details (click the row):**
  - block shares (structure / quantum chemistry / spectrum) and the top SHAP features in plain words;
  - the model's test error as % of the naive guess, overall and in this novelty band;
  - caveats.
- **Refusals:** where W-SPACE `domain_rules.category()` says `refuse`, the row shows "⊘ Not physically defined for this compound" (or "Defined only for a neutral form that does not exist at environmental pH") with the reason, and no number. `caveat` cells show the number plus a ▲ headline and the reason.
- **Salts:** W-SPACE `species()` strips counter-ions and neutralises. The models, physics and EPI run on the parent, and the page says so. Definedness is judged on the structure as entered.
- **Consistency check:** the Henry constant implied by the predicted VP/WS is compared with the predicted Henry constant (READER-1). A warning appears if they differ by more than 1 log unit.
- **Hazard rows:** ER/AR calls read "inconclusive" when the range crosses 0.5, and the base rate is given. LD50 is shown as a GHS band. Wording follows W-TOX review R4.

## Files
| file | what |
|---|---|
| `dashboard/build_v3.py` | Builds `index.html`. It runs the frozen models on the examples now and embeds `data_v3.json  [not redistributed; VM-internal]`. `--quick` skips physics. |
| `dashboard/v3_head.html`, `dashboard/v3/*.js` | The page: HTML/CSS, core helpers, rendering, UI, init. Plain ES5-style JS with no libraries. |
| `dashboard/build_good.py` → `good_v3.json`, `tool/card_stats.json` | "How good is it?": test RMSE as % of naive (the train mean), leak-free first (W-SPACE quarantine_v3), by nn_sim bin, against EPI on the same rows. Also the per-card n/coverage/skill. |
| `dashboard/check_v3.py` → `dashboard/docs/screenshots/check_report.json` | Real-Chromium checks. Every row has its required fields or a reason-bearing refusal. No JS errors, no overflow at 1280/390 px, WCAG AA contrast, loud offline and missing-input messages. |
| `tool/wtool_backend.py` | Orchestrates the frozen models, physics (W-PHYSICS `compute_physics`, timeout 240 s), EPI and W-SPACE. It contains no model logic. |
| `tool/wtool_postproc.py` | W-SPACE category rules, plus W-TOX's weak-acid pKa warning. |
| `tool/models_registry.json` | The frozen models used, in priority order. |
| `tool/depict.py` | SVG structure drawing. RDKit's drawer needs libXrender, which is missing on the VM. |
| `tool/shoot.py`, `tool/review_pack.sh` | Headless Chromium (QtWebEngine) screenshots/evals, and a text review pack for reviewers. |
| `tool/cvd_check.py` → `dashboard/docs/screenshots/cvd_report.json` | Colour-blind simulation (Machado 2009): pairwise ΔE of meaning-carrying colours. |
| `tool/record_demo.py` | Automated demo recording to mp4, following `DEMO_SCRIPT.md`. |
| `epi_extract.py`, `build_epi_canonical.py` → `epi_comparator_v3.parquet  [not redistributed; VM-internal]`, `_metrics.json/.md  [not redistributed; VM-internal]` | **Canonical EPI comparator for run 3.** It reproduces W-LADDER's extraction exactly. |

## Limitations (measured)
- Spectrum-only mode: the intervals under-cover at nominal 90% (empirical 0.85–0.88 for logKow/MP/VP/WS/Henry, from CRITIC's audit and W-SPECTRA's manifest). The page prints the empirical value. Spectral similarity does not track error, so no novelty call is made.
- Hazard classifiers show PR-AUC against the base rate per novelty band, never accuracy.
- Physics at inference is approximate for flexible molecules (≥4 rotatable bonds). The page labels this, following OPS-2's parity check.
- The file:// page cannot compute new structures, because there is no Python in the browser. It says so loudly and gives the start command.
- EPI needs internet. Offline, the row says "EPI web service not reachable".
- EPI test errors are optimistic, because EPI's training data overlap CompTox.

Note: the "How good is it?" table scores every method on the rows all listed methods share, so its n can be at or below the paper's (e.g. water_solubility leak-free n=377 vs 405). The water_solubility naive mean there uses the ungated train set (0.38% effect, conservative direction).
