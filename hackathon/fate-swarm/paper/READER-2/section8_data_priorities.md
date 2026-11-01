> **Status (READER-2, run4):** all eight VoD endpoints are complete (the last finished at 00:33). Points 1, 2, 4 and 5 below are SUPERSEDED by `section8_corrections_v7.md  [not redistributed; VM-internal]` and by whitepaper section 8 as it now stands (148 tests, 77 significant; median recovered 19/36/54%; numbers on the shipped v5 SP model). The "still running" and `vod_out/log_all.txt  [not redistributed; VM-internal]` lines are obsolete: the per-endpoint logs are `vod_out/log_<endpoint>.txt`.

# §8 Data priorities (READER-2, run-4 revision 00:35; every number from the named CSV; previous version kept as section8_data_priorities_run3.md)

**Rule (BB, Q003):** physically undefined cells (W-SPACE category A) are not gaps and are excluded. Source table: `data_priorities_table.csv  [not redistributed; VM-internal]` (data_priorities.py), which joins W-SPACE undefined_vs_gap_cells.csv, W-MODEL v4 struct_only test errors by class, the value-of-data (VoD) results and noise_panel.csv.

**1. More of the same data helps familiar compounds more than novel ones for BCF, Henry, logKow and MP. It does not for BP, VP or WS** (`vod_summary_A.csv`, Fig `fig_vod_learning.png`; all 8 learning-curve arms are complete as of run 4, 00:30). Change in % of naive RMSE per doubling of random training data, nn_sim_train <0.3 vs >=0.7:
- BCF: -2.3 vs -15.5 (n_eval 16 / 19)
- Henry: -5.6 vs -13.3
- logKow: -6.4 vs -13.1
- MP: -2.3 vs -7.7
- BP: -5.1 vs -5.3 (flat)
- WS: -6.2 vs -5.9 (flat)
- VP: -4.3 vs -2.5 (reversed)

Koc has no test rows in either extreme bin. The earlier wording, "random data mostly helps near-neighbours", was based on the first 3 endpoints only. It holds for 4 of 7 endpoints and should not be stated as general. Each arm has two runs, and no CI is computed on the slopes.

**2. A class being unseen costs up to ~95 pp of naive error, and adding measurements back recovers part of it** (`vod_summary_B.csv`, Fig `fig_vod_classes.png`). The design is leave-class-out vs full train: same model, same test compounds, plus a control that removes the same number of random rows instead. The 95% CI is a cluster bootstrap. Of 148 class x endpoint tests (all 8 endpoints; the MP arm is still running and lacks some large classes), 77 have a novelty penalty whose CI excludes 0. With 148 tests at 5%, about 7 would pass by chance, so the count is far above chance. No individual test is multiplicity-corrected, though. Largest:
- WS sulfonic/sulfate acid or salt +94.8 pp [30.0, 147.0], n_test 30
- Koc aromatic hydrocarbon +44.2 [33.0, 56.8]
- logKow sulfonic/sulfate +43.2 [34.5, 50.5]
- Henry nitro +34.5 [6.4, 89.6], n_test 19
- BCF aromatic hydrocarbon +28.0
- BCF halogenated aliphatic +27.7
- VP organosilicon/siloxane +27.7 [11.0, 56.9]

The random-removal control has a median of -0.3 pp (IQR -1.5 to +0.65). Its CI excludes 0 in 13 of 139 controls: 11 negative, 2 positive. So it is the class data that matters, not n. Across the 77 significant cases, adding back 5, 15 or 40 class members recovers a median 19%, 36% or 54% of the penalty. **Correction:** the run-3 draft said 39/60/70%, computed on the first 20 cases only. Two runs per arm, so per-case recovery values are noisy and can fall outside [0, 1].

**3. Genuine gaps are dominated by endpoint, not class.** Labelled fraction of the defined inventory (W-SPACE summary): logKOA 0.75%, kOH 1.8%, Koc 1.8%, pKa acidic 3.0%, BCF 3.6%, pKa basic 3.7%, against logKow 30% and MP 57%. Specific cells:
- quaternary ammonium Koc: 0 of 256 defined skeletons labelled
- PFAS acidic pKa: 4 labels, with 119 genuine gaps plus 180 non-equivalent cases
- siloxane logKOA: 0 of 437

**4. Where the shipped model is worst relative to its own average** (≥15 test compounds; v4 struct_only, % of naive):
- organophosphorus: BP 122 vs 54, Henry 92 vs 49, Koc 65 vs 54, logKow 65 vs 45
- urea/carbamate BP: 129, probably decomposition (W-SPACE category B)
- carboxylic acids VP: 91
- PFAS logKow: 67
This matches the literature on poor coverage of P- and F-containing chemicals (doi:10.1021/acs.est.3c05643 p.1).

**5. Headroom against the noise floor** (`data/noise_panel_v5_recheck.csv`; the shipped v5 model, variant S, with replicate-SD brackets from `noise_panel.csv`). RMSE / replicate SD:
| endpoint | full test | leak-free |
|---|---|---|
| logKow | 1.11-2.14 | 1.33-2.57 |
| BCF | 1.42-1.53 | 1.84-1.98 |
| WS | 1.42-2.67 | 1.55-2.91 |
| VP | 1.85-2.24 | 1.92-2.32 |
| Henry | 1.85-2.20 | 2.43-2.89 |
| BP | 2.05-2.73 | 2.39-3.19 |
| MP | 2.26-3.72 | 2.62-4.32 |

**Correction:** the run-3 draft said BCF was "already near its noise floor". That holds only on the full test, where BCF has the smallest ratio. On the leak-free rows, which are the novel-chemistry case, BCF (1.84-1.98, n=52) overlaps VP and logKow. This agrees with W-TP's retraction (N-057). The WS ratio pairs a gated RMSE with an ungated spread and is indicative only. No floor can be estimated for Koc, kOH, pKa or KOA, because CompTox holds 0-7 compounds with independent replicates.

**Recommended campaign, cheapest-first.** The ranking is READER-2's judgement from points 1–5.
1. pKa for PFAS acids and multi-site ionizables, with replicates. This is a routine titration, and it makes the noise floor estimable.
2. Koc in one defined soil at a stated pH for quaternary ammoniums (cation exchange; 0 of 256 labelled), organophosphorus and PFAS, about 15 per class (point 2: 15 added class members recover a median 36% of the novelty penalty across endpoints; Koc aromatic hydrocarbon 64%, Koc N-heteroaromatic 30%).
3. Slow-stir logKow for logKow >7, where the model's mean bias is −1.79 (n=22; `kow_noise_by_range.csv  [not redistributed; VM-internal]`), plus pH-stated logD/pKa pairs for hydrophilic ionizables. Compilations mix in apparent logD, which biases the labels low (W-TOX review). This fits the +0.57 model bias at logKow <1.
4. kOH and KOA for a small set of unfamiliar scaffolds (siloxanes, organophosphorus).
5. Last, BCF. It is the costly in-vivo test (doi:10.1080/1062936X.2019.1626278 p.3), and novel BCF compounds gained least from random data (-2.3 pp per doubling, n_eval=16). It is ranked last on COST, not on noise floor: leak-free headroom is about 1.9x, the same as VP.

**Non-measurement priority.** Re-curate before you measure:
- 151 logKow, 76 VP and 33 BP labels exist for physically undefined species, 72–76% of them from eChemPortal (`undefined_labelled_sources.csv  [not redistributed; VM-internal]`).
- 64.6% of multi-measurement logKow records are copies passed between aggregators, not independent replicates.

