# Chemistry reviews of the input representations (run 3)

**What this file is.** Before an agent trained a model, a chemistry-reviewer agent read the plan for how
the input would be turned into numbers (the "representation": which spectral peaks, descriptors or
reaction rules become model columns) and checked the chemistry. This file records those reviews, one
per representation, R1 to R5. The reviews checked the chemistry, not the code.

**How to read it.** Each heading names the representation, the verdict and the main changes asked for.
"GO" means the reviewer approved the representation for fitting. "Board" followed by a T number is the
agents' internal task number.

**Names used.** The agents worked under role names: W-TOX (the chemistry reviewer and author of these
reviews), W-SPECTRA (spectral features), W-MODEL (structure and physics models), W-SPACE (rules for when a
property is physically defined), W-TOOL (the prediction tool and dashboard), W-TP (transformation-product
rules) and CRITIC (the agent that challenged results). Paths that start with an agent name (for example W-SPECTRA/ or W-TP/)
point to the agents' working folders, which are not part of this repository. "labels_v2" is the agents'
table of experimental labels, which is also not redistributed.

---
## R1. W-SPECTRA MS/MS representation v3.1 (board T-028): GO, with four changes
Source: W-SPECTRA/REPRESENTATION_v31.md

MS/MS (tandem mass spectrometry) breaks a selected ion into fragments. The representation turns each
spectrum into columns for fragment masses, neutral losses (the mass difference between the precursor ion
and a fragment) and summary values.

What was checked: the units of every block of columns, how missing values are encoded, and whether the
transformation throws away chemistry.
* Accurate mass is kept to a tolerance of max(3 mDa, 10 ppm). This is correct. The NOMINAL arm (the same
  features with masses rounded to whole numbers) is the right control for it.
* Missing values: a vocabulary column set to 0 means "not observed", which is a real observation, not a
  missing value. The `s_prec_*` columns are NaN (empty) when no precursor ion was reported. Both are
  correct and can be told apart. GO.
* Counts of how many libraries contain a compound are left out of the feature sets. This is correct: they
  measure how popular a compound is, not its chemistry.

(a) **Named neutral losses.** The list is fine as far as it goes. For environmental chemistry the reviewer
asked to add these, all as exact masses:
- SO2 63.9619 (sulfonates and sulfones lose SO2 as well as SO3);
- HPO3 79.9663 and H3PO4 97.9769 (organophosphates; the single most diagnostic loss pair for
  organophosphate pesticides);
- HBr 79.9262;
- HNO2 46.9956 and NO2 45.9929 (nitroaromatics and nitro pesticides);
- HCN 27.0109;
- ketene C2H2O 42.0106, CH3COOH 60.0211, isobutylene C4H8 56.0626 (tert-butyl), propene C3H6 42.0470;
- CH3 radical 15.0235 (EI only);
- N2 28.0062 (azo and triazole groups).

Warning for the NOMINAL arm: ketene 42.0106 and propene 42.0470 differ by 36 mDa, and CO 27.9949,
N2 28.0062 and C2H4 28.0313 all round to 28. At whole-number mass, those named losses are different
molecules sharing one column. If NOMINAL loses to FULL (the accurate-mass version), say so; otherwise the
conclusion "accurate mass helps" will partly reflect these collisions rather than better resolution.

(b) **Halogens detected through mass defect.** The mass defect is the difference between a monoisotopic
mass and the nearest whole number. The idea is sound and points the right way: Cl 34.96885 and Br 78.91834
pull the defect negative, and since F replaces H, each added F lowers the relative mass defect (RMD,
the mass defect divided by the mass, in ppm) sharply. RMD is a good PFAS marker: hydrocarbons sit near
700-800 ppm RMD, perfluorinated chains below ~200. Keep s_prec_rmd_ppm.

The far more specific evidence for halogens is the isotope pattern, which is not used: the ratio of the
peak two mass units up to the main peak (A+2/A) is 0.32 for one Cl and 0.98 for one Br. If the cleaned
peak lists still contain A+2 peaks for fragments, add one feature: the largest A+2/A ratio over
fragments, weighted by peak intensity, in two windows (0.2-0.45 = Cl-like, 0.7-1.2 = Br-like). It needs
no structure, and it is what a chemist looks at. Not blocking.

(c) **Precursor m/z as a feature.** No objection: someone with only a spectrum does have this value, so
withholding it would make the spectrum-only mode unrealistically weak. Two conditions, both already in
the plan:
- the yardstick is the "ladder" of simpler models (mass alone, then mass plus ion type, then the full
  spectrum), not the naive mean;
- the comparison of FULL against MASS+ION-TYPE must carry a paired cluster-bootstrap confidence interval
  (resampling whole clusters of similar compounds and scoring both models on each resample).

One addition: precursor m/z plus the adduct type (for example [M+H]+ or [M+Na]+, encoded as on/off
columns) lets the model recover the neutral monoisotopic mass to within an adduct, which is a
constraint on the formula. State this in the write-up. Otherwise readers will take "spectra predict
logKow" to mean the fragments do the work, when part of it is "mass predicts logKow".

(d) **Averaging up to 5 selected spectra mixes collision energies.** How the fragment pattern changes
with collision energy (CE) is chemical information (it reflects bond strengths), and averaging removes
it. This is the one place where the rebuild repeats the Run 2 mistake, on a smaller scale. A cheap fix if
there is time: separate low-CE and high-CE sub-blocks where both exist. Not blocking.

---
## R2. W-MODEL v5 structure and physics blocks (board T-017): structure block GO; handling of missing physics CORRECTED
* **Structure block:** Morgan fingerprint counts (r=2: counts of each atom environment out to two bonds)
  plus 217 RDKit 2D descriptors, computed on labels_v2.smiles_canonical.
  The reviewer checked the salt question directly: of 27,730 labelled skeletons (structures after
  standardisation), **0 are multi-fragment**. labels_v2 is already desalted, so the worry about salts
  being kept as drawn does not arise here. 275 skeletons carry a permanent net charge (melting_point 304
  rows, logkow 142, water_solubility 136, vapor_pressure 83, bcf 27, boiling_point 32, henry 7,
  pka_acidic 8, pka_basic 2, koc 1, koh_gas 0, logkoa 0). GO.
* **Missing physics: the correction.** The physics block holds descriptors from AIMNet2 (a machine-learned
  quantum-chemistry potential) computed on relaxed three-dimensional structures. The reviewer checked CRITIC's claim
  against data/physics_v1/main.jsonl, the agents' physics output (not redistributed): all 27,216
  relaxed structures have formal charge 0 and their atomic charges sum correctly (|sum q| <= 1.2e-3 e).
  The "101.7 e" row CRITIC saw is not in main.jsonl; check tox.jsonl. Of the 275 charged labelled
  skeletons, **0 have physics**; of the neutral ones, 99.1% do. So the physics block has never seen an ion
  of any kind.

  The correct handling has three cases:
  1. **The endpoint is physically undefined for a permanent ion** (henry, vapour pressure, boiling point,
     koh_gas, logKoa, logKow): REFUSE. Return no value and no interval. The reason is the property, not
     the missing physics.
  2. **The endpoint is defined for ions** (water solubility, melting point, Koc, BCF): the missing physics
     is a real gap, but it must not be filled in. The LightGBM model sends missing values down a learned
     branch, and that branch was trained only on neutral chemistry, so an ion with empty physics columns is
     read as "a neutral molecule with odd descriptors". Instead, predict with the structure-only model,
     flag NO_PHYSICS *and* OUT-OF-DOMAIN(ionic, 0 ions in the physics training set), and take the
     interval from the structure-only conformal calibration set.
  3. **Never fill a physics column for an ion with the median.** That puts a quaternary ammonium at the
     centre of neutral descriptor space, the worst of the three options.

  Report how many compounds the structure-plus-physics (S+P) model drops in each compound class (neutral,
  permanent cation, anion, zwitterion), not only in each similarity bin (nn_sim, the similarity to the
  nearest training compound). The S vs S+P comparison silently leaves out exactly the class that the
  "undefined vs gap" analysis is about, and that has to be visible.

---
## R3. W-SPACE definedness rules v3 (board T-027): agrees with the derivation; five chemistry amendments
The derivation is right: a property is defined only if what the endpoint requires matches what the
species can do, judged after desalting and neutralising. The refusal to decide for organometallics is also
right. Amendments:
1. **Koc for permanent cations (quaternary ammonium and similar) is a real gap (state C), not undefined.**
   Sorption of an organic cation to soil or sediment is measurable and routinely measured. Koc = Kd/f_oc
   (the sorption coefficient divided by the fraction of organic carbon) is an operational normalisation
   and does not require a neutral species. It is a poor normalisation for cations, though: their sorption
   is dominated by cation exchange on clays (the cation exchange capacity, CEC) rather than organic carbon,
   so the measured value depends strongly on the soil and the pH. Verdict: defined, real gap, with the
   flag "matrix/pH-dependent; f_oc normalisation weak for ionic sorbates". The same holds for BCF on ions:
   defined and measurable, but ion trapping and pH dependence make it specific to the test conditions.
2. **logKow for a permanent cation is undefined, but say what can be measured:** logD (the distribution
   ratio at a given pH) and ion-pair partition coefficients. The output should name these rather than only
   refuse, or users will read "undefined" as "cannot be measured".
3. **A missing third state: species mismatch.** For a salt of a parent that can be neutralised, the
   measured melting point, water solubility and boiling point belong to **the salt**, not to the desalted
   parent that is modelled. They are defined and they are not a gap, but the label and the modelled
   species are different substances. In labels_v2 this does not show up (0 multi-fragment skeletons; the
   counter-ions were stripped before the agents received the data), which means any salt value in there is
   already attributed to the parent and the mismatch is built in. On the dashboard, where a user may type
   the salt, it does matter: return the parent's prediction with "value is for the neutral parent X;
   melting point and solubility of the salt differ, often by a lot".
4. **Vapour pressure and boiling point of a neutral that decomposes on heating** (a limitation the rules
   already state) should get their own flag, "decomposes before boiling (cannot be decided from
   structure)", rather than pass silently. Common cases are neutrals containing nitro, azo, peroxide or
   quaternary groups.
5. pKa handled as "no ionisable site (heuristic)" and kept separate from "undefined": agreed; that is the
   correct separation.

---
## R4. W-TOOL pKa applicability rule and hazard-card wording
**pKa sites.** The tool looks for ionisable sites with a set of SMARTS patterns (text patterns that match
substructures). The set is broad, which is the right default: withhold a pKa only when nothing matches.
Chemistry notes:
* The agents' own labels bound the useful range: pka_acidic in labels_v2 runs -2.2 to 18.5 (5-95% = 2.1
  to 11.5, n=1029); pka_basic -3.2 to 18.3 (5-95% = 0.8 to 11.0, n=1264) (source data/labels_v2.parquet,
  not redistributed).
* **Alcohols** (aliphatic R-OH, pKa ~15-18) and **simple acyl NH** (amide or urea NH, pKa ~15-17 in water)
  sit at or beyond the top of that range. Keep them as detected sites; withholding them would be wrong,
  because they are ionisable. But the card should add: "only very weak acid sites found (aliphatic alcohol
  / amide NH); the predicted pKa lies outside the range covered by the training labels (5-95%
  2.1-11.5)". That is a warning about extrapolation, not a refusal.
* In range and correctly included: sulfonamide NH (~10), imide (~9-10), azole NH (~7-14), activated CH
  (1,3-dicarbonyl ~5-13, nitroalkane ~10), thiol (~8-11), hydroxamic acid (~9), oxime (~11), boronic acid
  (~9), phenol (~4-11), sulfonic and sulfinic acids (<1), P-OH (~2), carboxylic acid (~1-5).
* Additions to ACID_SITES:
  - **Perfluorinated or strongly electron-withdrawing (EWG) substituted alcohols** are not weak acids
    (hexafluoroisopropanol pKa 9.3). The generic alcohol SMARTS catches them, but the "very weak" wording
    must not be used when the alpha carbon carries >=2 F or other strong EWGs.
  - **Tetrazole N-H** is already covered by [nH].
  - **Enols and 1,2-diketones** are covered.
  - **Squaric and vinylogous acids** are rare; ignore.
* Gaps in BASE_SITES: **N-oxide** ([#7+][O-], acting as a base after protonation, pKa ~1-5) and
  **phosphine** are missing; both are rare. **Nitrile** is correctly excluded as a base (pKa_BH+ ~ -10).
  Aniline is included, as it should be, but anilines with two ortho EWGs have pKa_BH+ < 0, below the label
  range.
* One real false-positive risk: `[OX2H1][NX2,NX3]` ("hydroxamic/oxime") also matches N-hydroxy groups on
  amines. This is harmless, since both are acids.

**Hazard-card wording.** Use exactly these texts, and never the word "measured" for an OPERA row:
* ER/AR (estrogen and androgen receptor) from CompTox OPERA rows: "Source: OPERA 2.8 (CERAPP/CoMPARA)
  **consensus call from a set of QSAR models**, derived from screening assays. This is a **model output,
  not a measurement**. We do not report an OPERA comparator for it because our model would be compared
  against another model's labels."
* ER/AR from W-TOX's ChEMBL models: "Trained on **measured** receptor potencies (ChEMBL, primary
  literature; IC50/Ki/EC50/AC50 pooled as p_activity = -log10 M). In-vitro potency against a
  purified/cell receptor; it is **not** an in-vivo endocrine hazard call and says nothing about exposure or
  dose."
* Rat oral LD50: "**Measured** acute oral LD50 in rat, median over records (CompTox hazards table),
  reported as log10 mmol/kg bw. Acute lethality only; not chronic, not ecological."
* Everywhere: give the base rate (the fraction of positives) next to any classification number, and never
  report accuracy.

---
## R5. W-TP abiotic transformation rules (board T-026)
Reviewed W-TP/tp_rules.py (25 reaction SMARTS, not redistributed). Overall the rules are sound, textbook,
and correctly flagged as first-generation only (one reaction step from the parent). Specific chemistry:
* **OX-ALKENE-CLEAVE is mislabelled.** OH addition to a C=C does not cleave it. Cleavage to two carbonyls is
  **ozonolysis** (O3), a different oxidant with a different rate law and a different environmental
  concentration. Either relabel the pathway "ozonolysis" or remove it from the oh_oxidation set. As it
  stands, the products are right but the mechanism is wrong, and the rate class ("fast") holds only in air
  with O3 present.
* **OX-ARHYDROX applied to every aromatic CH** lists every regioisomer. Real OH addition is strongly
  directed (ortho/para to electron-donating groups, and ipso attack on halogenated rings). Keep it, but
  label the products "regiochemistry not resolved" so the dashboard does not present a para isomer as
  *the* product.
* **Missing and environmentally important: hydrolysis of chloro-s-triazines** (chlorotriazine + H2O ->
  hydroxytriazine; acid or base catalysed; the main atrazine and simazine transformation product).
  HYD-ALKYLHALIDE covers sp3 carbon only and PH-ARPHOTOHYD requires light, so this very common product
  cannot be generated. Suggested SMARTS: `[c:1]([n:2])[Cl]>>[c:1]([n:2])O`, restricted to a triazine or
  pyrimidine ring.
* Also missing, both common: **sulfoxide -> sulfone** (a second oxidation, so outside "first generation"
  if counted from the parent, but for a thioether parent the sulfone is routinely the product observed)
  and **tertiary amine -> N-oxide**.
* **HYD-NITRILE** (nitrile -> amide) is correctly flagged as slow; abiotically it is negligible at
  environmental pH and mostly enzymatic. Keep the flag prominent.
* **PH-NITROREDUCE** (nitro -> nitroso) needs a reductant. Direct photolysis of nitroaromatics in sunlit
  water more often gives hydroxylated or denitrated products. Flag it as conditional, not a default
  product.
* The finding that products are **not** further from the training set than their parents (median nn_sim
  0.489 vs 0.455) is what the chemistry predicts: a first-generation product differs from its parent by
  one functional group, and Morgan r2 similarity is dominated by the unchanged scaffold. Report it that
  way.
