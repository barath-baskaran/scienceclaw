# Prior art: predicting properties from mass spectra without an identified structure

READER-1, run 3. The source is the team's private 166-paper library only; I could not search the open literature. Everything below is paraphrased, so cite as DOI + page. Nothing here is quoted.

## What has been done (in the library)
| Work | Input | Endpoint | Route | Evaluation | DOI, page |
|---|---|---|---|---|---|
| Hu et al. 2022, J Hazard Mater | EI-MS | T. pyriformis IGC50, liver toxicity | spectral features -> ML directly | train/test split, applicability-domain filter | 10.1016/j.jhazmat.2022.128558 p.1 |
| Peets et al. 2022 (MS2Tox), ES&T | ESI HRMS MS2 | fish/daphnia/algae LC50/EC50 | property model trained on structure fingerprints restricted to MS2-predictable bits; at inference, fingerprints predicted by SIRIUS/CSI:FingerID | test RMSE ~0.8-1.1 log-mM; MassBank validation on chemicals not in training | 10.1021/acs.est.2c02536 pp.3-4 (15510-15512) |
| Boelrijk et al. 2023, J Cheminform | ESI HRMS MS2 (cumulative neutral losses + precursor m/z) | RP-LC retention index | CNL -> CatBoost directly | the large set used *model-predicted* RI labels | 10.1186/s13321-023-00699-8 pp.4-5 |
| Hulleman et al. 2026, Anal Chem | ESI(+) MS2 CNLs | ready biodegradability (binary) | semi-supervised: a structure model pseudo-labels about 20.9k spectra, because only 107 compounds had both a label and a spectrum | random 80:20 split over *spectra* (the authors note this keeps train/test similar, p.5); external n=54, BA 78% | 10.1021/acs.analchem.6c02844 pp.4-7 (29231-29234) |
| Szabo et al. 2026 (fishFingers), ACS ES&T Tox | ESI MS2 -> SIRIUS fingerprints | fish log10 BCF | same two-stage route as MS2Tox | MS2 validation RMSE 1.02 vs structure-based TEST 0.89; validation subset has a narrower label SD (1.17 vs ~1.45) | 10.1021/acsesttox.6c00068 pp.A, D |

Hulleman 2026 claims to be the first direct biodegradability prediction for unknown HRMS features (p.7, 29234).

## What a defensible novelty claim looks like
Within this library, no work:
1. predicts the **physicochemical partitioning / fate set** (vapour pressure, Henry, Koc, logKow, KOA, water solubility, pKa, kOH) from MS/MS without a structure. The closest are BCF (fishFingers), ready biodegradability (Hulleman) and RP-LC retention (Boelrijk), each a single endpoint;
2. evaluates spectrum-only prediction on a **structure-cluster-disjoint split with performance by distance to training** (Hulleman split spectra at random; MS2Tox and fishFingers held out chemicals but did not stratify by similarity);
3. reports **calibrated (conformal) intervals with empirical coverage** for spectrum-only predictions.

Suggested wording for SCRIBE, hedged to the search actually done: "To our knowledge, and within the literature we could review, prior spectrum-to-property models address single endpoints (toxicity, BCF, ready biodegradability, retention) and use random or chemical-level splits. We report spectrum-only predictions for N fate endpoints under a cluster-disjoint split, with conformal intervals and coverage by familiarity bin."
Do **not** claim "first to predict fate from MS/MS". BCF and ready biodegradability are fate/persistence endpoints and have been done (fishFingers, Hulleman).

## Lessons from the prior work that bear on our design
- **Two-stage / pseudo-label routes beat direct training when label∩spectra is small.** MS2Tox p.3, Hulleman p.5. Our spectrum arm trains on about 5.3k train compounds with spectra, while the structure models use all labels. A "spectrum -> predicted substructure bits -> structure-trained property model" arm, or pseudo-labelling AMOS spectra of unlabelled compounds with the structure model, is the comparison a reviewer will ask for.
- **The spectra subset is biased** (fishFingers p.D; our measurement in READER-1/spectra_subset_bias.csv). With an HR ESI spectrum, test Henry mean is -7.4 vs -4.1 log10 atm m3/mol without one. Spectrum-only error as a % of naive must use the naive mean of the same subset.
- **Formula/annotation error is the dominant failure.** MS2Tox p.4: permethrin was about 1300x off with the wrong formula and about 6x off with the right one. Amide/carbonyl bits were the least reliably predicted.
- **Structure-based models still win where both are possible.** fishFingers p.D: TEST 0.89 vs MS2 route 1.02 RMSE. This matches our Run-2 finding that spectrum-only trails structure.
