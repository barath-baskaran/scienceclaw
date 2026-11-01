# EPI Suite comparator v3 (canonical, test split of labels_v2)

EPI numbers are optimistic: EPI Suite was trained on PhysProp, which overlaps CompTox; the SMILES-only API returns no experimental values, so overlap cannot be flagged per compound.

Error = RMSE as % of the naive guess (train-split mean); 100% = no skill. Source: epi_comparator_v3_metrics.json

| endpoint | units | n with EPI / n test | EPI RMSE | % of naive | nn_sim <0.3: n, % naive | nn_sim 0.3-0.5: n, % naive | nn_sim 0.5-0.7: n, % naive | nn_sim >=0.7: n, % naive |
|---|---|---|---|---|---|---|---|---|
| bcf | log10_L_per_kg_linear | 210 / 210 | 1.03 | 87% | 17, 90% | 102, 96% | 72, 73% | 19, 81% |
| boiling_point | degC | 1351 / 1355 | 74 | 76% | 82, 123% | 632, 68% | 544, 70% | 93, 97% |
| henry | log10_atm_m3_per_mol | 432 / 434 | 1.86 | 63% | 34, 77% | 214, 66% | 156, 49% | 28, 46% |
| koc | log10_L_per_kg_linear | 105 / 105 | 0.668 | 61% | 6, 72% | 53, 70% | 39, 58% | 7, 28% |
| koh_gas | log10_cm3_per_molecule_s | 97 / 101 | 0.281 | 24% | 14, 30% | 46, 21% | 33, 24% | 4, 20% |
| logkoa | log10 | 36 / 36 | 0.546 | 15% | 3, 7% | 9, 7% | 18, 18% | 6, 20% |
| logkow | log10 | 1751 / 1757 | 1.5 | 70% | 126, 158% | 823, 61% | 665, 57% | 137, 57% |
| melting_point | degC | 3448 / 3458 | 83.2 | 84% | 208, 101% | 1611, 85% | 1402, 75% | 227, 84% |
| pka_acidic | log10 | 0 / 172 | no EPI module | - | - | - | - | - |
| pka_basic | log10 | 0 / 211 | no EPI module | - | - | - | - | - |
| vapor_pressure | log10_mmHg | 1121 / 1127 | 3.21 | 86% | 81, 129% | 555, 78% | 399, 83% | 86, 100% |
| water_solubility | log10_mol_per_L | 1531 / 1536 | 1.98 | 85% | 120, 107% | 768, 84% | 532, 86% | 111, 68% |

Cross-check vs W-LADDER/epi_v2_values.parquet: {"logkow": {"n_compared": 1700, "n_abs_diff_gt_1e6": 0, "max_abs_diff": 0.0}, "water_solubility": {"n_compared": 1462, "n_abs_diff_gt_1e6": 0, "max_abs_diff": 0.0}, "vapor_pressure": {"n_compared": 1092, "n_abs_diff_gt_1e6": 0, "max_abs_diff": 0.0}, "henry": {"n_compared": 425, "n_abs_diff_gt_1e6": 0, "max_abs_diff": 0.0}, "melting_point": {"n_compared": 3322, "n_abs_diff_gt_1e6": 0, "max_abs_diff": 0.0}, "boiling_point": {"n_compared": 1335, "n_abs_diff_gt_1e6": 0, "max_abs_diff": 0.0}, "koc": {"n_compared": 103, "n_abs_diff_gt_1e6": 0, "max_abs_diff": 0.0}, "logkoa": {"n_compared": 33, "n_abs_diff_gt_1e6": 0, "max_abs_diff": 0.0}, "koh_gas": {"n_compared": 91, "n_abs_diff_gt_1e6": 0, "max_abs_diff": 0.0}, "bcf": {"n_compared": 207, "n_abs_diff_gt_1e6": 0, "max_abs_diff": 0.0}}
Fetched this run: 2
