# BB's Q-003 expert note versus W-TOX's undefined-vs-gap table (S-1, Sonnet)

I produced the lists only and did not decide who is right.

Sources:
- Note: `(internal path removed)`
- W-TOX table: `data/undefined_vs_gap_cells.csv` (180 cells = 15 endpoints x 12 classes). Verdict counts: defined 93, not_assessed 45, undefined 18, defined_if_site 18, assay_unattainable 6.
- Rule text: `W-TOX/README.md  [not redistributed; VM-internal]`, lines 80-100.

The note names only two classes: quaternary ammonium (permanent cation) and sulfonate/sulfate salts (permanent anion). It names six undefined properties and two genuine gaps. Everything else in the table is outside the note.

## 1. AGREE (12 + 2 cells; the six properties are Henry, vapour pressure, boiling point, kOH_gas, logKoa and logKow)

**Permanent cation (quaternary ammonium), six endpoints, W-TOX verdict `undefined`: 6 cells.**
- `henry` x permanent_cation. Note: needs volatility. W-TOX: undefined, "property of a gas-phase form; an ion has none".
- `vapor_pressure` x permanent_cation. Both undefined.
- `boiling_point` x permanent_cation. Both undefined.
- `koh_gas` x permanent_cation. Both undefined.
- `logkoa` x permanent_cation. Both undefined.
- `logkow` x permanent_cation. Both undefined. W-TOX adds: measurable instead is logD or an ion-pair Kow. The note also says ion pair.

**Permanent anion (sulfonate/sulfate "same reasoning"), same six endpoints, W-TOX `undefined`: 6 cells.**
- `henry`, `vapor_pressure`, `boiling_point`, `koh_gas`, `logkoa`, `logkow` x permanent_anion. Both undefined.
- The note says sulfonate and sulfate salts fall under the same reasoning. W-TOX's class `permanent_anion` is defined as a charge-based class. I did not check whether it contains the sulfonates (the class has 283 inventory structures).

**Genuine gaps named by the note: 2 cells.**
- `koc` x permanent_cation. Note: measurable, genuine gap, zero labels across 288 skeletons. W-TOX: verdict `defined` (not undefined), n_labelled = 1. Agrees on the category: not undefined, and nearly empty.
- `pka_acidic` x pfas. Note: measurable, genuine gap, 4 labels across 470 skeletons. W-TOX: `defined_if_site`, n_labelled = 16 (not undefined). Agrees on the category.

## 2. DISAGREE or PARTIAL (no outright contradiction in the verdict; these are the mismatches to resolve)

1. **`koc` x permanent_cation: label counts differ.**
   - Note: 0 labels across 288 skeletons. W-TOX: 1 labelled row, out of 8,099 inventory structures.
   - The class sizes differ too: 288 skeletons (note) versus 8,099 structures (W-TOX permanent_cation).
   - Unit probably differs: skeletons versus inventory rows. The "genuine gap" status is the same.
2. **`pka_acidic` x pfas: label counts differ.** Note: 4 labels across 470 skeletons. W-TOX: 16 labelled rows, out of 23,429 structures. The unit (skeleton versus row) and the class definition differ. The category agrees, but the number in the whitepaper should come from one source.
3. **W-TOX's verdict vocabulary has no explicit "genuine gap" label.**
   - The note asks for a two-way split: physically undefined versus genuine data gap, with reasoning per cell.
   - W-TOX's verdict column has `defined`, `defined_if_site`, `not_assessed`, `undefined`, `assay_unattainable`. A genuine gap is only implied by `defined` plus a small `n_labelled` (e.g. koc x permanent_cation = 1).
   - So the table does not by itself say which `defined` cells are gaps. The dashboard-side file `W-SPACE/refuse_cells_for_dashboard.csv  [not redistributed; VM-internal]` has A/B/C categories; I did not compare it cell by cell.
4. **Possible downstream inconsistency (not note versus W-TOX).** In my cold dashboard run (`W-TOOL/usability_review_S1.md  [not redistributed; VM-internal]`), perfluoropentanoic acid had logkoa, koh_gas, henry, vapor_pressure, boiling_point and logkow refused as "defined but non-equivalent (strong acid)". W-TOX marks `pfas` x those six endpoints as `defined` (n_labelled 8 to 499). The note does not cover PFAS gas-phase properties. Whoever owns the table should check that W-TOX's table, W-SPACE's rules and the dashboard agree.

## 3. NOT COVERED BY THE NOTE (W-TOX's own reasoning)

- **Permanent zwitterion x the six gas-phase / neutral endpoints (6 cells): `undefined`.** The note names neither zwitterions nor ions in general. W-TOX applies the same logic. Labelled rows in those cells: henry 1, vapour pressure 11, boiling point 4, kOH 0, logKoa 0, logKow 21.
- **`defined_if_site` (18 cells): the pKa endpoints.** pka_acidic and pka_basic x 9 classes. The note says nothing about pKa except the PFAS gap. The rule: a pKa needs an ionisable site of that kind. The 18 cells cover hydrolytically_labile, neutral_organic, permanent_anion, permanent_cation, permanent_zwitterion, pfas, small_volatile, surfactant_like and very_hydrophobic. W-TOX's own table: permanent_cation pKa acidic = 10 labelled, basic = 2.
- **`assay_unattainable` (6 cells): a state W-TOX invented.** The cells are er_potency and ar_potency x hydrolytically_labile, small_volatile, very_hydrophobic. The reasons are hydrolysis, evaporation and clogP > 7.
- **`not_assessed` (45 cells): inorganic, organometal and unparsed x 15 endpoints.** The rule refuses to decide because ionic and covalent drawings disagree. The note does not discuss metals. Dashboard-side, W-SPACE labels them "not assessed (metal)".
- **`defined` cells (93).** The note says nothing about:
  - gas-phase or neutral endpoints for neutral_organic, small_volatile, pfas, surfactant_like, very_hydrophobic and hydrolytically_labile (W-TOX: defined)
  - water solubility, melting point, bcf, rat LD50 and ER/AR potency for ions (W-TOX: defined)
- **Specific cases worth a second look by the owner** (they are listed here without a view on which is right):
  - `water_solubility`, `melting_point` x permanent_cation: `defined`, with 116 and 280 labelled rows. Both are physically meaningful for a salt, but the note's logic about "the species" could cut either way.
  - `rat_oral_ld50` x permanent_cation: `defined`, 244 labelled rows. The dashboard card flags a "species mismatch".
  - `bcf` x permanent_cation: `defined`, 12 labelled rows. The W-SPACE amendment treats Koc and BCF for ions as a genuine gap with a matrix/pH caveat.

## Counts
- Agree: 14 cells in one sense: 12 undefined cells for the cation and anion classes, plus 2 gap cells with a category match but different label counts.
- Disagree: 0 verdict contradictions. 3 mismatches in label counts or vocabulary, plus 1 cross-file inconsistency (PFAS refusals on the dashboard versus W-TOX `defined`).
- Not covered by the note: 180 - 14 = 166 cells. W-TOX's own reasoning, of which 6 zwitterion cells (undefined), 18 `defined_if_site`, 6 `assay_unattainable`, 45 `not_assessed` and the remainder `defined`.
- Check: the cation (6) + anion (6) + koc cation (1) + pka_acidic pfas (1) = 14 cells compared. The 180 - 14 = 166 figure follows from that.

---
# Addendum for SCRIBE (job 1): the W-SPACE implementation

Sources:
- `data/undefined_vs_gap_cells.csv  [shipped aggregate; working file not redistributed; VM-internal]`: 840 rows = 2 scopes (visible, all_inventory_structures) x 35 classes x 12 fate endpoints. It is per compound with categories A (physically undefined), B (non-equivalent) and C (defined); `cell_status` is one of covered, mixed, C_genuine_gap, A_undefined, B_nonequivalent.
- `analysis/domain_rules.py`.

W-SPACE's table counts compounds per class and endpoint, not a single verdict per cell. W-TOX's has 12 charge/class groups x 15 endpoints, one verdict per cell. W-TOX covers 3 hazard endpoints that W-SPACE does not. The two classifications are therefore not cell-for-cell comparable, and I only matched the cells named by the note.

## (a) W-SPACE AGREES with the note
- **Quaternary ammonium / permanent cation x logkow, boiling_point, vapor_pressure, henry, logkoa, koh_gas.**
  - Visible scope: A = 253 of 256 (about 99%) for logkow and boiling_point, and the same for the other four. 3 of 256 are C.
  - `cell_status` is A_undefined for logkoa, koh_gas and henry (the status for logkow and boiling_point is `covered`, because 48 and 15 labelled rows sit there).
  - The three C compounds are probably quaternary ammonium-like structures the rule decided are not permanent cations. I did not check them.
- **Species permanent_cation x the same six.** A = 409 of 409 each. Status A_undefined for logkoa and koh_gas only; the other four are `covered` because labelled rows exist (logkow 95, boiling point 22, vapour pressure 45, henry 1).
- **Quaternary ammonium x koc.** `C_genuine_gap`: 256 of 256 are C, 0 labelled (visible). With the hidden-inclusive scope: 288 inventory structures, which matches the note's "288 skeletons". This is a clean match to the note.
- **PFAS x pka_acidic.** The visible scope has 4 labelled rows of 417 inventory structures. The note says 4 labels across 470 skeletons. The label count matches. The inventory size differs (417 visible versus the note's 470; the hidden-inclusive scope row I printed shows 126 defined, and I did not reconcile the 470).
- **Permanent anion x the gas-phase endpoints.** boiling_point, henry, logkoa and koh_gas are A_undefined (9 of 9). logkow and vapor_pressure are A = 9 of 9 but `covered` because of labelled rows (2 and 3). This follows the note's "same reasoning".

## (b) W-SPACE DISAGREES with the note, or deliberately departs from it
1. **Sulfonic/sulfate acid or salt x logkow, boiling_point, vapor_pressure, henry, logkoa, koh_gas.**
   - Note: sulfonate and sulfate salts fall under the same reasoning as quaternary ammonium, i.e. physically undefined.
   - W-SPACE: only 25 of 632 are A, and these are zwitterions. 605 of 632 are classed B (non-equivalent: "unpopulated neutral, strong acid or base"). cell_status is `B_nonequivalent` for logkoa and koh_gas.
   - W-SPACE says so in `analysis/domain_rules.py` (around L346): "Extension of BB note Q003, which groups sulfonate/sulfate salts with permanent ions; our derivation keeps them separate because a neutral form exists in principle."
   - Both implementations still refuse to predict; the dashboard wording differs (A = "not physically defined", B = "non-equivalent / not measurable by standard protocol").
   - W-TOX does not have a sulfonate class. Its `permanent_anion` (283 structures) is `undefined` for the six endpoints, which is close to the note.
   - So W-TOX is closer to the note than W-SPACE here. W-SPACE changes the note's category for the sulfonates.
2. **PFAS x gas-phase / neutral endpoints.** W-SPACE: B is 50 to 130 of 417 (e.g. logkow 65, boiling point 88, koh_gas 130) and the rest C. W-TOX: `defined` for the whole class (class-level). The note says nothing about PFAS here. Not a disagreement with the note.

## (c) NOT COVERED by the note (W-SPACE's own reasoning)
- Cells in the visible scope by status: A_undefined, B_nonequivalent, C_genuine_gap and mixed together are 52 of 420; the rest, 756 across both scopes (368 per scope), are `covered`. Note: the `cell_status` counts I printed were over both scopes.
- Species permanent_zwitterion x logkoa, koh_gas: A_undefined (75 of 75). Zwitterions are not in the note. The rule is the same as for cations.
- Species permanent_anion x water_solubility and koc: `C_genuine_gap`. Species permanent_zwitterion x koc: `C_genuine_gap`.
- Species metal_containing_not_assessed (all endpoints): not assessed. Same position as W-TOX's `not_assessed`.
- B-category states (non-equivalent: strong acid or base, surfactant, decomposes, inner salt, no ionisable site) have no counterpart in the note. W-TOX has `defined_if_site` and `assay_unattainable` for comparable ideas.
- Note: hazard endpoints (LD50, ER, AR) are covered by W-TOX only.

## Agreement between the two implementations
- Agree on the undefined status: permanent cation and anion x the six gas-phase / neutral endpoints (the permanent_cation and permanent_anion classes). Agree on the koc gap for quaternary ammonium and permanent ions. Agree on zwitterions: both call logkoa, koh_gas and the other four undefined.
- Differ on: sulfonates (A in the note and in W-TOX's anion class; B in W-SPACE); how the verdict is held (one per cell versus per-compound counts); `defined_if_site` (W-TOX) versus B "no_site_in_aqueous_window" (W-SPACE); W-SPACE's `covered` label hides undefined cells that happen to hold labels (e.g. quaternary x logkow: 253 of 256 undefined, 48 labelled rows, status `covered`).
- That last point matters for the whitepaper: `cell_status` in W-SPACE is not a clean undefined/gap indicator. Use n_A_undefined / n_C_defined.
