# Limitations register: where current tools, data and agents fail at this analysis (READER-2, run 3)

Primary deliverable for the PIs. Each entry gives **what failed**, **the exact input → output** (or the count), **the consequence**, and **the source**: an agent's file or note, or a literature reference cited as DOI + page in our own words. Literature text is never quoted.
Status: OPEN means it still applies to the shipped tool, FIXED means it was handled in this run, FIELD means it is a property of the field and not of our code.

## A. Label data (CompTox exp_props → labels_v2)

| # | Limitation | Exact evidence | Consequence | Status | Source |
|---|---|---|---|---|---|
| A1 | Repeat measurements are mostly copies passed between aggregators, not replicates | logKow: 7,116 of 10,342 compounds have n_measurements ≥ 2. Of those, 4,518 (63.5%) have spread = 0. Raw exp_props with copies collapsed gives 64.6% copies, leaving 2,577 compounds with distinct replicates. Water solubility raw rows: 58% copies | n_measurements overstates evidence and must not be used as a confidence weight | OPEN (documented) | READER-2/noise_panel.csv; READER-1/label_noise_floor.csv |
| A2 | No replicate noise floor exists for Koc, kOH, pKa basic, pKa acidic or logKOA | Compounds with ≥ 2 distinct values: Koc 0, kOH 0, pKa basic 0, pKa acidic 7, logKOA 1 | Nobody can say whether a model is near the measurement limit on these endpoints | FIELD | READER-2/noise_panel.csv |
| A3 | Labels exist for quantities that are physically undefined | Category-A rows (W-SPACE rule): logKow 151, VP 76, BP 33, Henry 2. Example: benzyltrimethylammonium logKow -1.61. 72–76% of these come from eChemPortal (REACH dossiers), where a calculated value is accepted when the test cannot be run (doi:10.1021/acs.chemrev.5b00215 p.33) | A model trained on them learns numbers for non-existent quantities | FIXED in W-MODEL v5 (category-A rows dropped before fitting) | READER-2/undefined_labelled_sources.csv; W-SPACE/species_v3.parquet |
| A4 | Carbon acidities are filed as pKa | pka_basic: acetophenone 18.34, propiophenone 17.56, isobutyraldehyde 15.67 (all OPERA2.8). 167 of 2,293 pKa rows have no ionisable site by SMARTS | pKa targets mix non-equivalent quantities | FIXED for pka_basic > 14 (dropped in v5); the remaining category-B rows are flagged | CRITIC/audit_impossible_labels.json; W-SPACE note 20:29 |
| A5 | Linear Pow stored as log | eChemPortal DTXSID0027511 has propValue 62031 with original text '62031 (log Pow)'. About 300 such rows | Silent corruption of up to about 5 log units | FIXED (range filter in labels_v2; READER-1 found label min/max exactly -3.0/10.0, i.e. filtered, not clipped: only 4 and 2 rows sit at the bounds) | READER-1/label_noise_floor.py (n_raw_rows_dropped_range_or_T: logkow 361) |
| A6 | Contradictory duplicates within one InChIKey | logKow 236 keys with median within-key range 0.73 log10. VP 169 keys with median range 2.58 log10 | Raises the noise floor | OPEN | W-MODEL limitation (run 2) |
| A7 | Koc pools non-equivalent quantities | Kd, Freundlich KF and Koc are all reported as "Koc". Matrix and pH are not standardised, and foc variation alone spans about a factor of 25 in Kd (doi:10.1039/C7EM00034K p.8; doi:10.3389/fenvs.2024.1379283 p.2) | Koc error cannot be split into model error and label error | FIELD | literature |
| A8 | "No label" in the swarm DB is partly an artefact | Property rows for held-out compounds were removed from the swarm copy | Coverage counts are lower bounds | OPEN (documented) | W-SPACE README |

## B. The EPI Suite comparator

| # | Limitation | Exact evidence | Consequence | Status | Source |
|---|---|---|---|---|---|
| B1 | EPI's apparent skill is concentrated on PhysProp-sourced rows | RMSE % of naive, PhysProp rows vs other rows. EPI: logKow 34 vs 93, BP 29 vs 104, VP 39 vs 107, WS 53 vs 103. Our L1 control on the same rows: 34 vs 56, 30 vs 70, 34 vs 59, 40 vs 56. Difference-in-differences -31 to -44 pp, with cluster CIs excluding 0 for logKow, BP, VP, WS and BCF. In the leak-free, not-doubtful, non-PhysProp cell, EPI is at 106–109% of naive for MP, BP and VP | EPI's whole-test numbers flatter it. Report EPI on non-PhysProp rows as the cleaner comparator | OPEN (reported) | READER-2/epi_overlap_strat.py; READER-1/epi_joint_comparison.md |
| B2 | No out-of-sample EPI test is possible for Koc, kOH or pKa | 100% of test rows carry the OPERA2.8 (PhysProp) tag | EPI's strong kOH score (AOPWIN) cannot be told apart from in-sample fit | FIELD/OPEN | READER-2/physprop_flag_test.parquet |
| B3 | The API is estimate-only | experimentalValues is empty in all 4,999 cached responses. Queried by SMILES with cas=None | No lookup leakage, but EPI's coefficients are still fitted on overlapping data | documented | CRITIC note 20:35 |
| B4 | EPI reports no applicability domain | A user cannot tell an extrapolation from an interpolation (doi:10.1016/j.namjnl.2025.100054 p.12) | Our domain flag is a real addition | FIELD | literature |
| B5 | Published "external" benchmarks overlap training sets | 13–38% of a cosmetics test set were already in the tools' training sets (doi:10.1016/j.namjnl.2025.100054 p.8–9). BCF RMSE of one tool varies by about 1 log unit across benchmarks for the same reason (doi:10.1080/1062936X.2019.1626278 p.3). OPERA used random 75/25 splits (doi:10.1186/s13321-018-0263-1 p.5) | Literature accuracy figures are interpolation numbers. Our leak-free numbers are not comparable with them | FIELD | literature |

## C. Software and compute

| # | Limitation | Exact input → output | Consequence | Status | Source |
|---|---|---|---|---|---|
| C1 | nvalchemi AIMNet2Wrapper silently drops the Coulomb term without Ewald | HCN at the physics_v1 geometry gives E = -2543.354 eV with max\|F\| = 1.83 eV/Å. The native calculator gives -2544.0806 eV with max\|F\| = 7e-4 eV/Å | Physics that looks plausible but is wrong, with no warning | FIXED (native calculator) | OPS-2 note 20:32 |
| C2 | Closed-shell AIMNet2 is out of domain for radicals | E(H atom) = -10.781 eV vs about -13.6 eV. X–H BDEs come out about 100 kcal/mol too high, and IPs 1–2 eV too high | No BDE, IP or Fukui descriptor from this model. kOH mechanism features need AIMNet2-NSE, which is not obtainable offline | OPEN | W-PHYSICS note 20:39 |
| C3 | GPU driver vs pinned torch | hyperstack driver 570.195 (CUDA 12.8) with torch 2.14.1 cu130 gives "NVIDIA driver … too old" | Some GPU hosts are unusable | workaround | OPS-1 note 20:37 |
| C4 | The apt wrapper logs success on failure | apt.log says "install OK pkgs=weasyprint", but /usr/bin/weasyprint is absent because of a dpkg lock held by a hung chromium install | Check the binary, not the log | OPEN | SCRIBE note 20:26 |
| C5 | Expert note unreadable for the first 8 minutes | BB_EXPERT_NOTE_Q003.md was mode 640, group team. The swarm uid is in no shared group | Undefined-vs-gap rules were derived from first principles before the note could be read. They agree with it (sulfonate/quaternary reasoning) | FIXED 20:21 | PRINCIPAL notes |
| C6 | The model does not know when pKa is not applicable | Input C[N+](C)(C)CCCCCCCCCCCCCC.[Br-] gave pka_acidic 12.63 under frozen_v2 | Confident numbers for undefined quantities | FIXED in the tool via the domain_rules category gate | W-TOOL note 20:06 |

## D. Our own model and methods (what still fails)

| # | Limitation | Evidence | Source |
|---|---|---|---|
| D1 | Predictions are thermodynamically inconsistent across endpoints | Measured labels obey log H = log(VP/760) − log(WS·1000) to a median 0.13 log10. Our predictions miss it by a median 0.64 log10, and 35% are off by more than 1 log unit | READER-1/thermo_consistency_preds_summary.csv |
| D2 | Leak-free test n is too small to resolve some endpoints | logKOA 3, Koc 27, kOH 30, pKa acidic 38, BCF 53 | W-MODEL v5_main/results.json |
| D3 | Conformal coverage is not guaranteed off-distribution | Validity needs exchangeability, which a cluster split breaks by design (doi:10.1021/ci5001168 p.5). Per-bin coverage must be shown with its n | READER-1 audit |
| D4 | More of the same data helps familiar chemistry far more than novel chemistry | See data_priorities.md, experiment A | READER-2/vod_summary_A.csv |

## E. Field-level limits (literature), relevant to "novel chemistry"

1. **Coverage statistics exclude the hardest chemicals.** A large inventory study dropped about 24k of 112k records (permanently charged, UVCB, unparseable) before measuring QSPR domain coverage (doi:10.1021/acs.est.3c05643 p.4). Another excluded UVCBs and multi-constituent substances, about 30% of REACH registrations (doi:10.1016/j.comtox.2025.100398 p.2).
2. **Roughly one third of registered substances have no single structure.** Of about 235k CAS-identified entries across 22 inventories, over 75k are mixtures, polymers or UVCBs. A further 50k+ are confidential and up to 70k are ambiguously described (doi:10.1021/acs.est.9b06379 p.1, p.4–5). A SMILES-in tool, ours included, cannot address them.
3. **Being inside the domain is not accuracy.** Leverage-based and deny-list domains disagree on the same model, and Kow-only Koc domains accept about 20k chemicals that Abraham-descriptor domains reject (doi:10.1021/acs.est.3c05643 p.6, p.10). Restricting to the domain sometimes lowered balanced accuracy, for example for two BCF models (doi:10.1016/j.namjnl.2025.100054 p.9, p.12).
4. **QSPRs ignore fast-degrading functional groups.** Hydrolysable groups and peroxides are not represented, so expert review remains necessary (doi:10.1021/es903383a p.1). Measured logKow for hydrolysable silanes in our test set (e.g. CC[Si](ON=C(C)C)(ON=C(C)C)ON=C(C)C, labelled 0.20 while EPI estimates 8.85) probably describes the hydrolysis products.
5. **Ready biodegradability models do not travel.** On REACH substances mostly outside their training sets, balanced accuracy is 0.60–0.77, and consensus did not help (doi:10.1016/j.comtox.2025.100398 p.1).
6. **Coverage is weakest for KOA, atmospheric reactivity, F/P-containing chemicals and ionizables** (doi:10.1021/acs.est.3c05643 p.1). Our labelled fractions agree: logKOA ≤ 0.05 in every class, and 0.000 for organophosphorus, siloxanes and organometals (READER-2/lit_vs_data_coverage.csv).
