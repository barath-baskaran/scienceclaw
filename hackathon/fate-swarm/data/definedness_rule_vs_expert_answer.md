# Definedness rule vs. the expert's written answer (Q-003): a cell-by-cell comparison

**What this is.** Some fate properties have no physical meaning for some kinds of compound: a permanently
charged ion has no vapour pressure and no octanol-water partition coefficient for its neutral form, for
example. The agents built a rule that labels every compound class x endpoint combination ("cell") as
physically *undefined* (no measurement could exist) or *defined* (a missing value is a real data gap). A
domain expert separately wrote a short answer to the same question (called "the note" below).
This page compares the two cell by cell. It records where they agree and disagree; it does not judge
which is right.

**Why it matters.** An undefined cell should be reported to users as "not applicable", not predicted and
not counted as a data need. A defined cell with no labels is a real gap that a measurement could fill. Mixing the
two up either hides a real data need or asks for a measurement that cannot exist.

**Who did what.** W-TOX is the agent that built the rule and the cell table; a separate agent wrote this
comparison. File names starting with W-TOX/ refer to the agents' working folders, which are not part
of this repository.

## Sources

- **The note:** the expert's written answer (its location on the event machine is not given here).
- **The rule's cell table:** W-TOX/r3/undefined_vs_gap_cells.csv (180 cells = 12 classes x 15 endpoints).
- **Comparison script:** q003.py (a working file, not included).
- A second agent made an independent comparison of the same kind. How the two were resolved, and the
  corrected table, are in the section "Physically undefined is not missing" and the supplementary table
  "the corrected definedness table" of `paper/whitepaper.md`.

## Result

**Counts: AGREE = 14; DISAGREE = 12; NOT COVERED by the note = 154; total 180**

- **AGREE**: the note addresses the cell and gives the same verdict as the rule.
- **DISAGREE**: the note's general principle would give a different verdict from the rule.
- **NOT COVERED**: the note says nothing that applies to the cell.

## How to read the verdicts

| rule verdict | meaning |
|---|---|
| `undefined` | the property has no physical meaning for this kind of species, so no label can exist |
| `defined` | the property is meaningful; if there is no label, that is a real data gap |
| `defined_if_site` | (pKa only) defined where the molecule has an acidic or basic site |
| `not_assessed` | the rule does not decide: for inorganic and metal-containing compounds the ionic and covalent drawings of the same substance give different answers; `unparsed` structures could not be read |
| `assay_unattainable` | (receptor potency only) the compound cannot be assessed by the in-vitro receptor assays at all |

`n_labelled` is the number of compounds in that cell that have an experimental label.

## Assumptions made in the comparison

- The note's six undefined properties (vapour pressure, logKow, Henry, KOA, gas-phase OH rate, boiling
  point) are mapped to the rule's endpoints vapor_pressure, logkow, henry, logkoa, koh_gas, boiling_point.
- The note names the permanent cation class (quaternary ammonium) and says sulfonate/sulfate salts follow
  the same reasoning. The comparing agent mapped that to W-TOX's permanent_anion class, whose SMARTS
  (substructure patterns) include sulfonate, sulfate ester and carboxylate.
- W-TOX's README says it derived the rule without being able to read the note.
- Zwitterions are not named in the note. The general "permanently charged" principle might extend to
  them, but the comparing agent did not decide that, so they sit in NOT COVERED.

## Count differences (not verdict differences)

The note says zero Koc labels across 288 quat skeletons and 4 acidic-pKa labels across 470 PFAS
skeletons. The W-TOX table shows n_labelled=1 (permanent_cation x koc) and 16 (pfas x pka_acidic), using
its own class definitions and compound counts. These counts are not reconciled here.

## About the DISAGREE list

The note does not name inorganic or organometal classes; the disagreement is with its general
"non-volatile" clause. Organometal cells hold labels (e.g. vapor_pressure 216, boiling_point 298).

## AGREE (14)

| cell (class x endpoint) | rule verdict | n_labelled | what the note says |
|---|---|---|---|
| permanent_anion x henry | undefined | 0 | 'Sulfonate and sulfate salts fall under the same reasoning as quaternary ammonium cations' |
| permanent_cation x henry | undefined | 1 | listed undefined for permanent cation (table) |
| permanent_anion x vapor_pressure | undefined | 4 | 'Sulfonate and sulfate salts fall under the same reasoning as quaternary ammonium cations' |
| permanent_cation x vapor_pressure | undefined | 61 | listed undefined for permanent cation (table) |
| permanent_anion x boiling_point | undefined | 0 | 'Sulfonate and sulfate salts fall under the same reasoning as quaternary ammonium cations' |
| permanent_cation x boiling_point | undefined | 29 | listed undefined for permanent cation (table) |
| permanent_anion x koh_gas | undefined | 0 | 'Sulfonate and sulfate salts fall under the same reasoning as quaternary ammonium cations' |
| permanent_cation x koh_gas | undefined | 0 | listed undefined for permanent cation (table) |
| permanent_anion x logkoa | undefined | 0 | 'Sulfonate and sulfate salts fall under the same reasoning as quaternary ammonium cations' |
| permanent_cation x logkoa | undefined | 0 | listed undefined for permanent cation (table) |
| permanent_anion x logkow | undefined | 2 | 'Sulfonate and sulfate salts fall under the same reasoning as quaternary ammonium cations' |
| permanent_cation x logkow | undefined | 128 | listed undefined for permanent cation (table) |
| permanent_cation x koc | defined | 1 | Koc for quats measurable, genuine gap (rule: defined, not undefined) |
| pfas x pka_acidic | defined_if_site | 16 | acidic pKa for PFAS measurable, genuine gap (rule: defined_if_site, i.e. applicable where an acid site exists) |

## DISAGREE (12)

For every cell below, the note's general principle is: 'undefined for a species that is permanently
charged or non-volatile'. The rule instead says: 'ionic and covalent drawings ... give different
answers; the rule refuses to decide' = not_assessed, neither undefined nor gap.

| cell (class x endpoint) | rule verdict | n_labelled |
|---|---|---|
| inorganic x henry | not_assessed | 0 |
| organometal x henry | not_assessed | 25 |
| inorganic x vapor_pressure | not_assessed | 0 |
| organometal x vapor_pressure | not_assessed | 216 |
| inorganic x boiling_point | not_assessed | 0 |
| organometal x boiling_point | not_assessed | 298 |
| inorganic x koh_gas | not_assessed | 0 |
| organometal x koh_gas | not_assessed | 6 |
| inorganic x logkoa | not_assessed | 0 |
| organometal x logkoa | not_assessed | 0 |
| inorganic x logkow | not_assessed | 0 |
| organometal x logkow | not_assessed | 80 |

## NOT COVERED by the note (154)

Each line gives the cell, the rule's verdict and the number of labelled compounds.

- hydrolytically_labile x henry: rule=defined (n_labelled=27)
- neutral_organic x henry: rule=defined (n_labelled=1528)
- permanent_zwitterion x henry: rule=undefined (n_labelled=1)
- pfas x henry: rule=defined (n_labelled=117)
- small_volatile x henry: rule=defined (n_labelled=721)
- surfactant_like x henry: rule=defined (n_labelled=7)
- unparsed x henry: rule=not_assessed (n_labelled=0)
- very_hydrophobic x henry: rule=defined (n_labelled=159)
- hydrolytically_labile x vapor_pressure: rule=defined (n_labelled=212)
- neutral_organic x vapor_pressure: rule=defined (n_labelled=4291)
- permanent_zwitterion x vapor_pressure: rule=undefined (n_labelled=11)
- pfas x vapor_pressure: rule=defined (n_labelled=309)
- small_volatile x vapor_pressure: rule=defined (n_labelled=1335)
- surfactant_like x vapor_pressure: rule=defined (n_labelled=52)
- unparsed x vapor_pressure: rule=not_assessed (n_labelled=0)
- very_hydrophobic x vapor_pressure: rule=defined (n_labelled=344)
- hydrolytically_labile x boiling_point: rule=defined (n_labelled=273)
- neutral_organic x boiling_point: rule=defined (n_labelled=4637)
- permanent_zwitterion x boiling_point: rule=undefined (n_labelled=4)
- pfas x boiling_point: rule=defined (n_labelled=499)
- small_volatile x boiling_point: rule=defined (n_labelled=2232)
- surfactant_like x boiling_point: rule=defined (n_labelled=53)
- unparsed x boiling_point: rule=not_assessed (n_labelled=0)
- very_hydrophobic x boiling_point: rule=defined (n_labelled=132)
- hydrolytically_labile x koh_gas: rule=defined (n_labelled=11)
- neutral_organic x koh_gas: rule=defined (n_labelled=149)
- permanent_zwitterion x koh_gas: rule=undefined (n_labelled=0)
- pfas x koh_gas: rule=defined (n_labelled=49)
- small_volatile x koh_gas: rule=defined (n_labelled=395)
- surfactant_like x koh_gas: rule=defined (n_labelled=0)
- unparsed x koh_gas: rule=not_assessed (n_labelled=0)
- very_hydrophobic x koh_gas: rule=defined (n_labelled=0)
- hydrolytically_labile x logkoa: rule=defined (n_labelled=0)
- neutral_organic x logkoa: rule=defined (n_labelled=124)
- permanent_zwitterion x logkoa: rule=undefined (n_labelled=0)
- pfas x logkoa: rule=defined (n_labelled=8)
- small_volatile x logkoa: rule=defined (n_labelled=98)
- surfactant_like x logkoa: rule=defined (n_labelled=0)
- unparsed x logkoa: rule=not_assessed (n_labelled=0)
- very_hydrophobic x logkoa: rule=defined (n_labelled=22)
- hydrolytically_labile x logkow: rule=defined (n_labelled=96)
- neutral_organic x logkow: rule=defined (n_labelled=8475)
- permanent_zwitterion x logkow: rule=undefined (n_labelled=21)
- pfas x logkow: rule=defined (n_labelled=350)
- small_volatile x logkow: rule=defined (n_labelled=1190)
- surfactant_like x logkow: rule=defined (n_labelled=59)
- unparsed x logkow: rule=not_assessed (n_labelled=0)
- very_hydrophobic x logkow: rule=defined (n_labelled=241)
- hydrolytically_labile x water_solubility: rule=defined (n_labelled=96)
- inorganic x water_solubility: rule=not_assessed (n_labelled=0)
- neutral_organic x water_solubility: rule=defined (n_labelled=7174)
- organometal x water_solubility: rule=not_assessed (n_labelled=100)
- permanent_anion x water_solubility: rule=defined (n_labelled=0)
- permanent_cation x water_solubility: rule=defined (n_labelled=116)
- permanent_zwitterion x water_solubility: rule=defined (n_labelled=21)
- pfas x water_solubility: rule=defined (n_labelled=260)
- small_volatile x water_solubility: rule=defined (n_labelled=1044)
- surfactant_like x water_solubility: rule=defined (n_labelled=90)
- unparsed x water_solubility: rule=not_assessed (n_labelled=0)
- very_hydrophobic x water_solubility: rule=defined (n_labelled=342)
- hydrolytically_labile x melting_point: rule=defined (n_labelled=484)
- inorganic x melting_point: rule=not_assessed (n_labelled=0)
- neutral_organic x melting_point: rule=defined (n_labelled=16262)
- organometal x melting_point: rule=not_assessed (n_labelled=241)
- permanent_anion x melting_point: rule=defined (n_labelled=3)
- permanent_cation x melting_point: rule=defined (n_labelled=280)
- permanent_zwitterion x melting_point: rule=defined (n_labelled=19)
- pfas x melting_point: rule=defined (n_labelled=785)
- small_volatile x melting_point: rule=defined (n_labelled=1938)
- surfactant_like x melting_point: rule=defined (n_labelled=186)
- unparsed x melting_point: rule=not_assessed (n_labelled=0)
- very_hydrophobic x melting_point: rule=defined (n_labelled=680)
- hydrolytically_labile x koc: rule=defined (n_labelled=3)
- inorganic x koc: rule=not_assessed (n_labelled=0)
- neutral_organic x koc: rule=defined (n_labelled=517)
- organometal x koc: rule=not_assessed (n_labelled=2)
- permanent_anion x koc: rule=defined (n_labelled=0)
- permanent_zwitterion x koc: rule=defined (n_labelled=0)
- pfas x koc: rule=defined (n_labelled=31)
- small_volatile x koc: rule=defined (n_labelled=68)
- surfactant_like x koc: rule=defined (n_labelled=0)
- unparsed x koc: rule=not_assessed (n_labelled=0)
- very_hydrophobic x koc: rule=defined (n_labelled=13)
- hydrolytically_labile x bcf: rule=defined (n_labelled=5)
- inorganic x bcf: rule=not_assessed (n_labelled=0)
- neutral_organic x bcf: rule=defined (n_labelled=901)
- organometal x bcf: rule=not_assessed (n_labelled=33)
- permanent_anion x bcf: rule=defined (n_labelled=2)
- permanent_cation x bcf: rule=defined (n_labelled=12)
- permanent_zwitterion x bcf: rule=defined (n_labelled=1)
- pfas x bcf: rule=defined (n_labelled=107)
- small_volatile x bcf: rule=defined (n_labelled=133)
- surfactant_like x bcf: rule=defined (n_labelled=8)
- unparsed x bcf: rule=not_assessed (n_labelled=0)
- very_hydrophobic x bcf: rule=defined (n_labelled=95)
- hydrolytically_labile x pka_acidic: rule=defined_if_site (n_labelled=2)
- inorganic x pka_acidic: rule=not_assessed (n_labelled=0)
- neutral_organic x pka_acidic: rule=defined_if_site (n_labelled=865)
- organometal x pka_acidic: rule=not_assessed (n_labelled=2)
- permanent_anion x pka_acidic: rule=defined_if_site (n_labelled=0)
- permanent_cation x pka_acidic: rule=defined_if_site (n_labelled=10)
- permanent_zwitterion x pka_acidic: rule=defined_if_site (n_labelled=0)
- small_volatile x pka_acidic: rule=defined_if_site (n_labelled=123)
- surfactant_like x pka_acidic: rule=defined_if_site (n_labelled=9)
- unparsed x pka_acidic: rule=not_assessed (n_labelled=0)
- very_hydrophobic x pka_acidic: rule=defined_if_site (n_labelled=2)
- hydrolytically_labile x pka_basic: rule=defined_if_site (n_labelled=4)
- inorganic x pka_basic: rule=not_assessed (n_labelled=0)
- neutral_organic x pka_basic: rule=defined_if_site (n_labelled=888)
- organometal x pka_basic: rule=not_assessed (n_labelled=2)
- permanent_anion x pka_basic: rule=defined_if_site (n_labelled=0)
- permanent_cation x pka_basic: rule=defined_if_site (n_labelled=2)
- permanent_zwitterion x pka_basic: rule=defined_if_site (n_labelled=0)
- pfas x pka_basic: rule=defined_if_site (n_labelled=3)
- small_volatile x pka_basic: rule=defined_if_site (n_labelled=355)
- surfactant_like x pka_basic: rule=defined_if_site (n_labelled=3)
- unparsed x pka_basic: rule=not_assessed (n_labelled=0)
- very_hydrophobic x pka_basic: rule=defined_if_site (n_labelled=7)
- hydrolytically_labile x rat_oral_ld50: rule=defined (n_labelled=250)
- inorganic x rat_oral_ld50: rule=not_assessed (n_labelled=0)
- neutral_organic x rat_oral_ld50: rule=defined (n_labelled=8821)
- organometal x rat_oral_ld50: rule=not_assessed (n_labelled=237)
- permanent_anion x rat_oral_ld50: rule=defined (n_labelled=5)
- permanent_cation x rat_oral_ld50: rule=defined (n_labelled=244)
- permanent_zwitterion x rat_oral_ld50: rule=defined (n_labelled=37)
- pfas x rat_oral_ld50: rule=defined (n_labelled=424)
- small_volatile x rat_oral_ld50: rule=defined (n_labelled=899)
- surfactant_like x rat_oral_ld50: rule=defined (n_labelled=56)
- unparsed x rat_oral_ld50: rule=not_assessed (n_labelled=0)
- very_hydrophobic x rat_oral_ld50: rule=defined (n_labelled=242)
- hydrolytically_labile x er_potency: rule=assay_unattainable (n_labelled=1)
- inorganic x er_potency: rule=not_assessed (n_labelled=0)
- neutral_organic x er_potency: rule=defined (n_labelled=5557)
- organometal x er_potency: rule=not_assessed (n_labelled=9)
- permanent_anion x er_potency: rule=defined (n_labelled=0)
- permanent_cation x er_potency: rule=defined (n_labelled=61)
- permanent_zwitterion x er_potency: rule=defined (n_labelled=14)
- pfas x er_potency: rule=defined (n_labelled=636)
- small_volatile x er_potency: rule=assay_unattainable (n_labelled=6)
- surfactant_like x er_potency: rule=defined (n_labelled=8)
- unparsed x er_potency: rule=not_assessed (n_labelled=0)
- very_hydrophobic x er_potency: rule=assay_unattainable (n_labelled=432)
- hydrolytically_labile x ar_potency: rule=assay_unattainable (n_labelled=2)
- inorganic x ar_potency: rule=not_assessed (n_labelled=0)
- neutral_organic x ar_potency: rule=defined (n_labelled=2594)
- organometal x ar_potency: rule=not_assessed (n_labelled=16)
- permanent_anion x ar_potency: rule=defined (n_labelled=0)
- permanent_cation x ar_potency: rule=defined (n_labelled=26)
- permanent_zwitterion x ar_potency: rule=defined (n_labelled=8)
- pfas x ar_potency: rule=defined (n_labelled=1612)
- small_volatile x ar_potency: rule=assay_unattainable (n_labelled=6)
- surfactant_like x ar_potency: rule=defined (n_labelled=7)
- unparsed x ar_potency: rule=not_assessed (n_labelled=0)
- very_hydrophobic x ar_potency: rule=assay_unattainable (n_labelled=89)
