# Near-neighbour recall control

Models score better on test compounds that have a close relative in the training set, because they can
partly "recall" that relative's value. This note measures how much of the error difference between
the full test set and the leak-free test set comes from that recall, and how much comes simply from
having less training data. It replaces an earlier control (the graph-trained control and its "share
of gap" ratio, see `split_evaluation.md`) that the critic agent's audit (CRITIC 21:18) found to be
confounded.

## Design

All results use the official test rows and the same structure-only LightGBM (a gradient-boosted
decision-tree model on structure descriptors). Three training sets are compared:

- **FULL**: the official training set.
- **PRUNE**: the official training set minus every compound within Tanimoto 0.40 of any test compound
  (that is, every close structural relative of a test compound is removed).
- **RAND**: the same number of training compounds removed at random (3 seeds, i.e. three different
  random draws).

From these:

- **recall effect** = PRUNE - RAND. Both have the same training size, so the difference isolates the
  loss of close relatives.
- **size effect** = RAND - FULL: the effect of the smaller training set on its own.
- **Negative control**: the recall effect on the leak-free rows, which is expected to be 0 because
  those compounds had no close relative in training to begin with.

Errors are in % of naive points: root-mean-square error as a percentage of a naive guess that always
predicts the training mean (lower is better), and differences are in percentage points of that scale.
Intervals are paired cluster-bootstrap 95% CIs: compounds are resampled by chemical-similarity
cluster, and the models being compared are scored on the same resample each time.

The source files, eval_recall_control.py and recall_control.csv, are the agents' working files and are
not part of this repository.

## Results

Rows: "all_test" is every official test compound, "leakfree_test" the ones with no close training
relative, "leaking_test" the ones with one. "train removed" is the share of the training set removed in
PRUNE (and therefore in RAND).

| endpoint | rows | n | train removed | FULL | PRUNE | RAND | recall effect | size effect |
|---|---|---|---|---|---|---|---|---|
| bcf | all_test | 206 | 18% | 74.5 | 77.2 | 77.8 | -0.58 [-5.64, +4.66] | +3.32 [-2.24, +9.58] |
| bcf | leakfree_test | 52 | 18% | 90.4 | 96.5 | 99.0 | -2.51 [-9.75, +7.55] | +8.65 [-5.49, +19.28] |
| bcf | leaking_test | 154 | 18% | 67.3 | 68.3 | 67.8 | +0.48 [-5.78, +5.77] | +0.48 [-2.87, +4.03] |
| boiling_point | all_test | 1293 | 43% | 54.0 | 54.5 | 54.1 | +0.35 [-1.32, +1.99] | +0.14 [-1.42, +1.64] |
| boiling_point | leakfree_test | 362 | 43% | 56.3 | 55.4 | 56.0 | -0.62 [-3.51, +2.00] | -0.30 [-2.69, +2.38] |
| boiling_point | leaking_test | 931 | 43% | 52.7 | 54.0 | 53.1 | +0.89 [-1.17, +2.88] | +0.40 [-1.56, +2.32] |
| henry | all_test | 417 | 29% | 51.3 | 53.7 | 50.6 | +3.07 [+0.56, +6.16] | -0.63 [-2.54, +1.30] |
| henry | leakfree_test | 122 | 29% | 60.1 | 60.8 | 58.8 | +2.05 [-1.29, +7.52] | -1.35 [-4.52, +2.57] |
| henry | leaking_test | 295 | 29% | 44.7 | 48.6 | 44.7 | +3.93 [+0.89, +7.89] | -0.04 [-2.16, +2.10] |
| koc | all_test | 105 | 20% | 55.0 | 57.9 | 57.3 | +0.58 [-5.68, +6.98] | +2.36 [-0.07, +5.12] |
| koc | leakfree_test | 28 | 20% | 53.2 | 51.4 | 56.6 | -5.26 [-12.27, +1.97] | +3.44 [-1.55, +8.84] |
| koc | leaking_test | 77 | 20% | 55.6 | 60.0 | 57.6 | +2.45 [-5.54, +9.96] | +2.00 [-1.43, +5.13] |
| koh_gas | all_test | 101 | 14% | 49.7 | 51.3 | 48.6 | +2.65 [+0.21, +4.78] | -1.11 [-4.83, +2.79] |
| koh_gas | leakfree_test | 30 | 14% | 61.5 | 62.8 | 62.9 | -0.09 [-4.77, +3.76] | +1.42 [-4.89, +10.74] |
| koh_gas | leaking_test | 71 | 14% | 45.7 | 47.3 | 43.5 | +3.81 [+1.08, +6.37] | -2.17 [-6.55, +1.15] |
| logkoa | all_test | 36 | 20% | 15.4 | 25.2 | 17.0 | +8.23 [+1.51, +14.54] | +1.54 [-0.03, +3.10] |
| logkoa | leaking_test | 33 | 20% | 13.3 | 25.1 | 14.4 | +10.67 [+3.34, +16.47] | +1.10 [-0.47, +3.40] |
| logkow | all_test | 1649 | 38% | 42.3 | 46.1 | 44.3 | +1.81 [+0.34, +3.11] | +2.01 [+1.03, +3.07] |
| logkow | leakfree_test | 444 | 38% | 52.2 | 54.5 | 54.6 | -0.19 [-3.32, +2.50] | +2.40 [+0.18, +4.71] |
| logkow | leaking_test | 1205 | 38% | 38.2 | 42.8 | 40.0 | +2.76 [+1.40, +4.05] | +1.86 [+0.99, +2.76] |
| melting_point | all_test | 3245 | 49% | 51.9 | 55.4 | 54.0 | +1.39 [+0.53, +2.21] | +2.11 [+1.53, +2.72] |
| melting_point | leakfree_test | 813 | 49% | 56.2 | 57.6 | 57.9 | -0.30 [-1.83, +1.19] | +1.75 [+0.57, +2.94] |
| melting_point | leaking_test | 2432 | 49% | 50.0 | 54.4 | 52.3 | +2.14 [+1.16, +3.14] | +2.29 [+1.64, +2.94] |
| pka_acidic | all_test | 171 | 24% | 65.5 | 72.6 | 72.8 | -0.20 [-4.97, +4.56] | +7.33 [+3.30, +11.41] |
| pka_acidic | leakfree_test | 39 | 24% | 96.9 | 106.5 | 109.9 | -3.41 [-12.75, +5.18] | +12.98 [+3.48, +23.32] |
| pka_acidic | leaking_test | 132 | 24% | 52.4 | 58.6 | 57.0 | +1.60 [-4.11, +7.98] | +4.64 [+0.46, +8.05] |
| pka_basic | all_test | 211 | 23% | 69.6 | 69.4 | 71.3 | -1.93 [-6.64, +1.55] | +1.73 [-0.92, +4.54] |
| pka_basic | leakfree_test | 54 | 23% | 81.3 | 77.4 | 84.1 | -6.66 [-13.05, -1.46] | +2.76 [-1.18, +8.21] |
| pka_basic | leaking_test | 157 | 23% | 64.9 | 66.3 | 66.2 | +0.12 [-4.82, +4.68] | +1.28 [-1.82, +5.24] |
| vapor_pressure | all_test | 1056 | 33% | 44.8 | 47.0 | 45.6 | +1.35 [-0.21, +2.93] | +0.85 [-0.20, +1.80] |
| vapor_pressure | leakfree_test | 304 | 33% | 48.4 | 48.9 | 48.5 | +0.39 [-1.17, +2.17] | +0.12 [-2.17, +2.17] |
| vapor_pressure | leaking_test | 752 | 33% | 43.2 | 46.2 | 44.4 | +1.76 [-0.30, +3.75] | +1.18 [+0.07, +2.48] |
| water_solubility | all_test | 1374 | 33% | 49.3 | 53.0 | 50.4 | +2.68 [+0.99, +4.24] | +1.04 [+0.23, +1.81] |
| water_solubility | leakfree_test | 392 | 33% | 53.6 | 54.1 | 55.3 | -1.19 [-3.03, +0.74] | +1.72 [+0.40, +3.14] |
| water_solubility | leaking_test | 982 | 33% | 47.6 | 52.6 | 48.3 | +4.32 [+2.45, +6.30] | +0.74 [-0.17, +1.71] |

## Summary

- Recall effect on all test rows: the CI excludes 0 (positive) on 6/12 endpoints (['henry', 'koh_gas',
  'logkoa', 'logkow', 'melting_point', 'water_solubility']); the median is 1.4 points.
- Negative control (leak-free rows): the CI excludes 0 on 1/11 endpoints (['pka_basic']), which is
  consistent with chance at 95%.
