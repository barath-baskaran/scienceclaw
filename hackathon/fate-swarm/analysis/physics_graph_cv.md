# Does adding physics descriptors help? A graph cross-validation estimate (P-009)

This note asks whether adding quantum-chemistry-derived "physics" descriptors to the structure
descriptors makes the model more accurate, and whether any gain is larger for compounds that are far
from the training data. It is a test of the physics effect only. **It is not an estimate of the
tool's accuracy**: the cross-validation models here are also trained on the compounds that the
official split sets aside for calibration and testing.

The identifier in the title is the name the agents gave this pre-stated hypothesis test.

## Terms used

- **Graph cross-validation (graph CV)**: the compounds are divided into five folds cut on a similarity
  graph, so that no compound in a test fold has a close neighbour in its training folds. Each fold is
  held out in turn.
- **S, SP, SPperm**: the three model variants compared.
  - **S** = structure descriptors only.
  - **SP** = S + AIMNet2 physics v1. AIMNet2 is a machine-learned interatomic potential that
    approximates density functional theory (DFT); the physics descriptors (charges, dipole, shape,
    surface area, energy residuals) are computed from its relaxed geometry.
  - **SPperm** = S + the physics rows shuffled between compounds. This is a capacity control: it has
    the same number of extra columns as SP but no real information in them. If SP beats S only
    because it has more columns to fit, SPperm would do as well.
- **Error**: % of naive RMSE, the root-mean-square error as a percentage of a naive guess that predicts
  the mean of the fold's training labels. Lower is better.
- **Bins**: the bin column groups compounds by their Tanimoto similarity to the nearest training
  compound (on the project's Morgan fingerprints); the lower-similarity bin is the less familiar group.
  "all" pools both bins.

## Method

- Source: physics_graphcv.csv and physics_graphcv_perfold.csv, produced by eval_physics_graphcv.py.
  These are the agents' working files and are not part of this repository.
- Confidence intervals: paired cluster bootstrap over labels_v2.cluster (1000 resamples), 95% CI. The
  unit of resampling is the chemical-similarity cluster. "Paired" means S, SP and SPperm are compared
  on the same resampled compounds each time.
- The physics transforms (element reference energies, robust z-scores) are computed over all
  compounds at once. This uses the input descriptors (X) of the test compounds, never their labels (y),
  so no label information leaks.
- Fixed hyper-parameters: no tuning and no early stopping.
- One row per (endpoint, skeleton), with the mean label. This is a deviation from CRITIC condition 5
  (CRITIC is the agent that set the test conditions and checked results), which asks for the median
  over InChIKeys.
- The last column, "S on all rows", is S scored on ALL rows, including compounds without physics
  descriptors, taken from the eval_splits_v3 graph_all run. Comparing it with the S column shows what
  restricting to compounds with physics descriptors removes.

## Results

"clusters" is the number of chemical-similarity clusters. "SP-S" and "SP-SPperm" are differences in
percentage points of naive error, with their confidence intervals; negative means SP has the lower error. "folds SP<S"
counts the folds in which SP beat S.

| endpoint | bin | n | clusters | S | SP | SPperm | SP-S | SP-SPperm | folds SP<S (of 5) | S on all rows (n) |
|---|---|---|---|---|---|---|---|---|---|---|
| bcf | all | 1205 | 462 | 77.8 | 75.4 | 76.5 | -2.46 [-4.23, -1.04] | -1.17 [-2.71, +0.31] | 3 | 78.0 (1237) |
| bcf | <0.3 | 253 | 154 | 83.5 | 81.6 | 84.0 | -1.93 [-4.48, +1.82] | -2.48 [-5.06, +0.39] |  |  |
| bcf | 0.3-0.4 | 952 | 359 | 76.1 | 73.4 | 74.2 | -2.64 [-4.80, -0.59] | -0.74 [-2.52, +1.03] |  |  |
| boiling_point | all | 7696 | 1650 | 51.9 | 51.5 | 52.8 | -0.33 [-1.04, +0.42] | -1.32 [-2.02, -0.59] | 3 | 53.1 (7758) |
| boiling_point | <0.3 | 1689 | 669 | 50.1 | 50.2 | 52.4 | +0.03 [-1.29, +1.44] | -2.27 [-3.26, -1.13] |  |  |
| boiling_point | 0.3-0.4 | 6007 | 1330 | 52.5 | 52.0 | 53.0 | -0.45 [-1.13, +0.27] | -0.97 [-1.82, -0.13] |  |  |
| henry | all | 2491 | 745 | 54.7 | 54.4 | 55.6 | -0.36 [-1.51, +0.75] | -1.28 [-2.43, -0.18] | 4 | 54.2 (2502) |
| henry | <0.3 | 494 | 247 | 60.0 | 59.6 | 61.3 | -0.35 [-2.54, +2.26] | -1.64 [-3.82, +0.68] |  |  |
| henry | 0.3-0.4 | 1997 | 605 | 53.0 | 52.7 | 53.8 | -0.36 [-1.46, +0.71] | -1.16 [-2.38, +0.11] |  |  |
| koc | all | 630 | 252 | 53.4 | 55.6 | 55.0 | +2.19 [-0.83, +5.18] | +0.59 [-1.71, +2.84] | 3 | 54.4 (632) |
| koc | <0.3 | 103 | 67 | 57.2 | 56.3 | 56.6 | -0.89 [-4.91, +4.03] | -0.29 [-3.39, +2.70] |  |  |
| koc | 0.3-0.4 | 527 | 214 | 52.5 | 55.4 | 54.6 | +2.90 [-0.26, +6.28] | +0.79 [-1.96, +3.60] |  |  |
| koh_gas | all | 607 | 279 | 57.6 | 54.9 | 59.3 | -2.73 [-4.53, -0.14] | -4.39 [-6.19, -1.72] | 4 | 57.8 (609) |
| koh_gas | <0.3 | 139 | 86 | 57.5 | 54.8 | 60.1 | -2.71 [-5.07, +1.75] | -5.24 [-7.51, -0.26] |  |  |
| koh_gas | 0.3-0.4 | 468 | 227 | 57.6 | 54.9 | 58.6 | -2.74 [-5.09, +0.35] | -3.70 [-5.79, -1.13] |  |  |
| logkoa | all | 252 | 90 | 30.7 | 31.0 | 31.7 | +0.25 [-1.91, +2.04] | -0.67 [-2.23, +0.51] | 3 | 30.7 (252) |
| logkoa | <0.3 | 57 | 31 | 22.7 | 24.1 | 25.3 | +1.42 [-2.24, +3.73] | -1.13 [-3.88, +0.92] |  |  |
| logkoa | 0.3-0.4 | 195 | 69 | 34.4 | 34.3 | 34.7 | -0.19 [-2.56, +2.02] | -0.49 [-2.12, +0.88] |  |  |
| logkow | all | 9880 | 2339 | 45.8 | 44.8 | 45.7 | -1.05 [-1.67, -0.41] | -0.93 [-1.49, -0.40] | 4 | 45.2 (9931) |
| logkow | <0.3 | 2240 | 951 | 48.9 | 47.2 | 48.4 | -1.72 [-2.88, -0.52] | -1.19 [-2.23, -0.10] |  |  |
| logkow | 0.3-0.4 | 7640 | 1866 | 44.7 | 43.9 | 44.7 | -0.80 [-1.44, -0.12] | -0.84 [-1.45, -0.23] |  |  |
| melting_point | all | 19068 | 3850 | 50.3 | 49.3 | 50.5 | -0.96 [-1.35, -0.60] | -1.15 [-1.47, -0.82] | 4 | 51.0 (19473) |
| melting_point | <0.3 | 4012 | 1567 | 50.8 | 49.5 | 51.2 | -1.32 [-2.13, -0.57] | -1.66 [-2.37, -1.02] |  |  |
| melting_point | 0.3-0.4 | 15056 | 3082 | 50.1 | 49.3 | 50.3 | -0.84 [-1.23, -0.47] | -0.97 [-1.33, -0.60] |  |  |
| pka_acidic | all | 1007 | 385 | 70.9 | 69.6 | 71.9 | -1.32 [-3.45, +0.99] | -2.38 [-4.50, -0.11] | 3 | 70.8 (1028) |
| pka_acidic | <0.3 | 117 | 87 | 81.1 | 78.9 | 82.2 | -2.20 [-8.39, +3.61] | -3.31 [-9.57, +2.32] |  |  |
| pka_acidic | 0.3-0.4 | 890 | 333 | 68.9 | 67.8 | 70.0 | -1.14 [-3.33, +1.07] | -2.20 [-4.41, -0.08] |  |  |
| pka_basic | all | 1256 | 489 | 64.7 | 62.7 | 64.7 | -2.06 [-3.94, -0.06] | -2.00 [-3.72, -0.11] | 4 | 66.1 (1264) |
| pka_basic | <0.3 | 190 | 115 | 59.9 | 56.5 | 57.3 | -3.40 [-7.28, +0.36] | -0.81 [-4.92, +3.37] |  |  |
| pka_basic | 0.3-0.4 | 1066 | 437 | 65.5 | 63.6 | 65.8 | -1.87 [-3.94, +0.31] | -2.17 [-4.02, -0.25] |  |  |
| vapor_pressure | all | 6287 | 1645 | 45.7 | 45.7 | 46.0 | -0.00 [-0.78, +0.72] | -0.34 [-0.78, +0.14] | 2 | 46.3 (6361) |
| vapor_pressure | <0.3 | 1409 | 640 | 46.3 | 45.3 | 45.6 | -0.92 [-2.22, +0.37] | -0.28 [-1.21, +0.63] |  |  |
| vapor_pressure | 0.3-0.4 | 4878 | 1312 | 45.5 | 45.8 | 46.2 | +0.35 [-0.42, +1.07] | -0.37 [-0.87, +0.20] |  |  |
| water_solubility | all | 8110 | 2219 | 48.7 | 47.6 | 49.2 | -1.15 [-1.70, -0.52] | -1.67 [-2.21, -1.13] | 4 | 51.5 (8280) |
| water_solubility | <0.3 | 1974 | 932 | 53.5 | 52.2 | 54.6 | -1.24 [-2.20, -0.22] | -2.32 [-3.42, -1.26] |  |  |
| water_solubility | 0.3-0.4 | 6136 | 1716 | 47.0 | 45.9 | 47.3 | -1.11 [-1.68, -0.44] | -1.42 [-1.99, -0.87] |  |  |

## Verdict against the pre-stated falsification test

- SP beats S with a CI excluding 0 on 6/12 endpoints: ['bcf', 'koh_gas', 'logkow', 'melting_point',
  'pka_basic', 'water_solubility']. The largest gain is -2.7 points.
- SP beats its permuted copy (the capacity control) with a CI excluding 0 on 8/12: ['boiling_point',
  'henry', 'koh_gas', 'logkow', 'melting_point', 'pka_acidic', 'pka_basic', 'water_solubility'].
- Physics helps by CRITIC condition 4 (SP beats S AND SP beats SPperm, both CIs excluding 0):
  ['koh_gas', 'logkow', 'melting_point', 'pka_basic', 'water_solubility']. Where SP beats SPperm but
  not S, the shuffled physics columns are making the model worse (they act as noise features), so
  that is not evidence of a physics gain.
- Endpoints where SP beats S by >= 10% of naive in the <0.3 bin with a CI excluding 0: none.
- Conclusion: the claim SURVIVES. Physics gives a small (about 1-3 points of % naive) improvement that
  is real (it beats the permuted control), and it does not help disproportionately far from training.
  The <0.3 gains are of similar size to the 0.3-0.4 gains, with overlapping CIs; the interaction was
  not tested formally.
