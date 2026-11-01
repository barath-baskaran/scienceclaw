The predictor ships as a single offline HTML file (`dashboard/index.html`, 0.61 MB). It loads no remote resources, and its build script fails if any remote URL is embedded. A launcher (`dashboard/start_dashboard.sh`) serves the same page on 127.0.0.1 only. In that mode a structure nobody has seen is computed on the user's machine: RDKit ETKDGv3 + MMFF94 start, an AIMNet2 relaxation on CPU (33–55 s for the demo structures), the frozen W-MODEL v5 structure + physics model, the W-TOX hazard models, and a live, identity-checked EPI Suite query. Physics computed at inference is labelled "approximate (conformer-dependent)" for molecules with four or more rotatable bonds. The reason is OPS-2's CPU-vs-GPU parity check, where descriptors of flexible molecules drifted by more than 10% of the training SD.

The tool has three input modes, each a first-class tab:
- **structure** (SMILES);
- **structure + MS/MS**;
- **spectrum only**. This mode runs W-SPECTRA's spectrum_only_v31 model. All required metadata must be supplied, and none is ever filled in by default. Every estimate shows the spectrum-only test error next to the error from precursor mass + adduct alone and the error with the known structure on the same compounds. Example for ESI-positive logKow: 76%, 89% and 44% of naive. This shows what the fragments add.

Every property row shows:
- the estimate, plus a conversion to everyday units with its formula;
- the 90% conformal range;
- the empirical coverage on test chemicals as new to the model as the query, printed next to the nominal level. Bands with fewer than 30 test chemicals are marked "too few to check".
- a novelty tag, carried by shape and word rather than colour: ● familiar / ▲ somewhat new / ✖ new to the model. It is worded as "less similar training data: expect larger errors", not as a validity gate, because similarity is a weak, graded signal. For spectra, similarity did not track error, so no novelty call is made.
- the EPI Suite comparator. For pKa the row says "no EPI comparator" instead.

Expanding a row shows the block shares (structure / quantum chemistry / spectrum) and the top SHAP contributions in plain words. It also shows the model's test error as a percentage of the naive guess: leak-free first (logKow 52%, n=454), then for the query's novelty band, then for the full test set, labelled as including close relatives of training chemicals.

Where W-SPACE's derived rules call a property physically undefined, the row says "⊘ Not physically defined for this compound". It gives a one-line plain reason and **no number and no interval**, even where EPI Suite would return one. An example is the vapour pressure or logKow of a quaternary ammonium salt. Salts are predicted for their neutral parent, and the page says so. Hazard rows state their label source verbatim and report classifier calls with PR-AUC against the base rate, never accuracy. They are marked "low-confidence" when the chemical is unfamiliar.

**Checks.** Automated checks run in a real Chromium engine (`dashboard/check_v3.py`). All 201 property rows across 9 structure examples and 4 spectrum examples carry their required fields or a reasoned refusal. There are no JavaScript errors and no horizontal overflow at 1280 or 390 px, and all visible text meets WCAG AA contrast (minimum 4.83:1). A colour-vision simulation (protan/deutan/tritan) found one confusable pair: "somewhat new" vs "new" under deuteranopia, ΔE 4.2. "New" was changed to a filled tag, raising ΔE to at least 63.

**Usability.** Two agents who did not build the dashboard reviewed it. W-TP did two cold reads as a bench chemist; W-MODEL checked correctness against its own model files. They raised 18 issues, all fixed, including a misleading "leak-free" claim, a hazard call that should have read "inconclusive", and a similarity shown on a different scale from the coverage bin. An automated screen recording of a new structure computed live, the refusals for a quaternary ammonium salt, spectrum-only mode and the test-results view was made but is not included in this repository; `dashboard/DEMO_SCRIPT.md` describes how to record it again.
