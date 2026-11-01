# W-TOX chemistry reviews of swarm representations (run 3)

One entry per representation reviewed BEFORE a fit. "What I checked" is the chemistry, not the code.

---
## R1. W-SPECTRA MS/MS representation v3.1 (board T-028) — GO, with four changes
Source: W-SPECTRA/REPRESENTATION_v31.md

Checked: units of every block, missingness encoding, whether the transform destroys chemistry.
* Accurate mass retained at max(3 mDa, 10 ppm): correct, and the NOMINAL arm is the right control.
* Missingness: vocabulary columns 0 = "not observed" (a real measurement, not missing); `s_prec_*` NaN
  when no precursor reported. Both correct and distinguishable. GO.
* Library-membership counts excluded from feature arms: correct (popularity, not chemistry).

(a) NAMED NEUTRAL LOSSES. The list is fine as far as it goes; for environmental chemistry I would add,
all as exact masses: SO2 63.9619 (sulfonates/sulfones lose SO2 as well as SO3), HPO3 79.9663 and
H3PO4 97.9769 (organophosphates — the single most diagnostic loss pair for OP pesticides),
HBr 79.9262, HNO2 46.9956 and NO2 45.9929 (nitroaromatics and nitro pesticides), HCN 27.0109,
ketene C2H2O 42.0106, CH3COOH 60.0211, isobutylene C4H8 56.0626 (tert-butyl), propene C3H6 42.0470,
CH3 radical 15.0235 (EI only), N2 28.0062 (azo/triazole).
WARNING for the NOMINAL arm: ketene 42.0106 and propene 42.0470 differ by 36 mDa, and CO 27.9949 /
N2 28.0062 / C2H4 28.0313 all collapse to 28. At nominal mass those named losses are chemically
different molecules in one column; say so when NOMINAL loses to FULL, or the "accurate mass helps"
conclusion will be partly a collision artefact rather than a resolution effect.

(b) HALOGENS VIA MASS DEFECT. Sound in principle and the right direction (Cl 34.96885, Br 78.91834
pull the defect negative; F replaces H so per-F the relative mass defect falls hard — RMD in ppm is a
good PFAS marker, hydrocarbons sit near 700-800 ppm RMD, perfluorinated chains below ~200). Keep
s_prec_rmd_ppm. But the far more specific halogen evidence is the ISOTOPE PATTERN (A+2/A = 0.32 for
one Cl, 0.98 for one Br) and you are not using it. If the cleaned peak lists still contain A+2 peaks
for fragments, add one feature: the power-weighted max A+2/A ratio over fragments, in two windows
(0.2-0.45 = Cl-like, 0.7-1.2 = Br-like). It is structure-free and is the thing a chemist actually
looks at. Not blocking.

(c) PRECURSOR m/z AS A FEATURE. No objection: a spectrum-only user genuinely has it, so withholding it
would make the mode unrealistically weak. Two conditions, both already in your plan: the ladder
(mass -> mass+ion type -> full) must be the yardstick, not the naive mean, and the FULL-beats-
MASS+ION-TYPE contrast must carry the paired cluster-bootstrap CI. One addition: precursor m/z plus the
adduct one-hot lets the model recover the neutral monoisotopic mass to within an adduct, i.e. a formula
constraint. Say that explicitly in the write-up, otherwise readers will read "spectra predict logKow"
when part of what is happening is "mass predicts logKow".

(d) AVERAGING OVER UP TO 5 SELECTED SPECTRA mixes collision energies. The CE dependence of the fragment
pattern is chemical information (bond strengths), and averaging it away is the one place this rebuild
repeats the Run 2 mistake in a smaller way. Cheap fix if there is time: low-CE and high-CE sub-blocks
where both exist. Not blocking.

---
## R2. W-MODEL v5 structure + physics blocks (board T-017) — structure block GO; physics missingness semantics CORRECTED
* Structure block: Morgan r=2 count FP + 217 RDKit 2D descriptors on labels_v2.smiles_canonical.
  I checked the salt question directly: of 27,730 labelled skeletons, **0 are multi-fragment** (labels_v2
  is already desalted), so the "salts kept as drawn" worry does not arise here. 275 skeletons carry a
  permanent net charge (melting_point 304 rows, logkow 142, water_solubility 136, vapor_pressure 83,
  bcf 27, boiling_point 32, henry 7, pka_acidic 8, pka_basic 2, koc 1, koh_gas 0, logkoa 0). GO.
* PHYSICS MISSINGNESS — this is the correction. I verified CRITIC's claim against
  data/physics_v1/main.jsonl: all 27,216 relaxed structures have formal charge 0 and the
  charge sums are converged (|sum q| <= 1.2e-3 e; the "101.7 e" row CRITIC saw is not in main.jsonl —
  check tox.jsonl). Of the 275 charged labelled skeletons, **0 have physics**; of the neutral ones,
  99.1% do. So the physics arm has seen no ion of any kind.
  Correct semantics, in three cases:
  1. Endpoint physically undefined for a permanent ion (henry, vapour pressure, boiling point, koh_gas,
     logKoa, logKow): REFUSE. No value, no interval. "No physics" is not the reason — the property is.
  2. Endpoint defined for ions (water solubility, melting point, Koc, BCF): the missing physics is a
     GENUINE gap, but it must not be imputed. LightGBM's missing branch was trained only on neutral
     chemistry, so a NaN physics vector for an ion is read as "a neutral molecule with odd descriptors".
     Predict with the structure-only arm, flag NO_PHYSICS *and* OUT-OF-DOMAIN(ionic, 0 ions in the
     physics training set), and take the interval from the structure-only conformal set.
  3. Never median-impute a physics column for an ion; that places a quaternary ammonium at the centre of
     neutral descriptor space, which is the worst of the three options.
  Report the S+P drop count per compound class (neutral / permanent cation / anion / zwitterion), not
  only per nn_sim bin: the S vs S+P ablation silently excludes exactly the class the undefined-vs-gap
  analysis is about, and that has to be visible.

---
## R3. W-SPACE definedness rules v3 (board T-027) — agree with the derivation; five chemistry amendments
The derivation (endpoint requirement x species capability, after desalt/neutralise) is right and the
refusal to decide on organometals is right. Amendments:
1. **Koc for permanent cations (quaternary ammonium, etc.) is C — a genuine gap, not undefined.** Sorption
   of an organic cation to soil/sediment is measurable and routinely measured; Koc = Kd/f_oc is an
   operational normalisation that does not require a neutral species. But it is a poor normalisation for
   cations, whose sorption is dominated by cation exchange on clay/CEC rather than organic carbon, so the
   measured value depends strongly on the matrix and pH. Verdict: defined, genuine gap, flag
   "matrix/pH-dependent; f_oc normalisation weak for ionic sorbates". Same for BCF on ions (defined;
   measurable; ion trapping and pH-dependence make it condition-specific).
2. **logKow for a permanent cation is undefined — but say what IS measurable**: logD (pH-dependent
   distribution ratio) and ion-pair partition coefficients. The card should name those rather than only
   refuse, or users will read "undefined" as "unmeasurable".
3. **A third state you are missing: SPECIES MISMATCH.** For a salt of a neutralisable parent, melting
   point, water solubility and boiling point as measured are properties of **the salt**, not of the
   desalted parent you model. They are defined, they are not a gap, but the label and the modelled species
   are different substances. In labels_v2 this does not bite (0 multi-fragment skeletons; the counter-ions
   were stripped upstream), which means any salt label in there is already attributed to the parent and
   the mismatch is baked in. For the dashboard, where the user types the salt, it does bite: return the
   parent's prediction with "value is for the neutral parent X; melting point and solubility of the salt
   differ, often by a lot".
4. **Vapour pressure / boiling point of a thermally labile neutral** (your stated limitation) should be
   reported as a separate flag "decomposes before boiling (cannot be decided from structure)" rather than
   left silent — nitro/azo/peroxide/quaternary-containing neutrals are the common cases.
5. pKa handled as "no ionisable site (heuristic)" and kept out of "undefined": agreed, that is the correct
   separation.

---
## R4. W-TOOL pKa applicability rule and hazard-card wording
**pKa sites.** The SMARTS set is broad and that is the right default (withhold only when nothing matches).
Chemistry notes:
* Our own labels bound the useful range: pka_acidic in labels_v2 runs -2.2 to 18.5 (5-95% = 2.1 to 11.5,
  n=1029); pka_basic -3.2 to 18.3 (5-95% = 0.8 to 11.0, n=1264) (source data/labels_v2.parquet).
* **Alcohol** (aliphatic R-OH, pKa ~15-18) and **simple acyl NH** (amide/urea NH, pKa ~15-17 in water) sit
  at or beyond the top of that range. Keep them as detected sites — withholding would be wrong, they are
  genuinely ionisable — but the card should add: "only very weak acid sites found (aliphatic alcohol /
  amide NH); the predicted pKa lies outside the range covered by the training labels (5-95% 2.1-11.5)".
  That is an extrapolation warning, not a refusal.
* In range and correctly included: sulfonamide NH (~10), imide (~9-10), azole NH (~7-14), activated CH
  (1,3-dicarbonyl ~5-13, nitroalkane ~10), thiol (~8-11), hydroxamic (~9), oxime (~11), boronic acid (~9),
  phenol (~4-11), sulfonic/sulfinic (<1), P-OH (~2), carboxylic acid (~1-5).
* Gaps I would add to ACID_SITES: **perfluorinated/strongly EWG-substituted alcohols** are not weak acids
  (hexafluoroisopropanol pKa 9.3) — your generic alcohol SMARTS catches them, but the "very weak" wording
  must not be applied when the alpha carbon carries >=2 F or other strong EWGs; **N-H of tetrazole already
  covered by [nH]**; **enol/1,2-diketone covered**; **squaric/vinylogous acids** rare, ignore.
* Gaps in BASE_SITES: **N-oxide** ([#7+][O-] as a base after protonation, pKa ~1-5) and **phosphine** are
  missing; both rare. **Nitrile** is excluded as a base, correct (pKa_BH+ ~ -10). Aniline is included and
  should be, but note anilines with two ortho-EWGs have pKa_BH+ < 0, below our label range.
* One real false-positive risk: `[OX2H1][NX2,NX3]` ("hydroxamic/oxime") also matches N-hydroxy groups on
  amines; harmless, both are acids.

**Hazard-card wording.** Use exactly these, and never the word "measured" for an OPERA row:
* ER/AR from CompTox OPERA rows: "Source: OPERA 2.8 (CERAPP/CoMPARA) **consensus call from a set of QSAR
  models**, derived from screening assays. This is a **model output, not a measurement**. We do not report
  an OPERA comparator for it because our model would be compared against another model's labels."
* ER/AR from my ChEMBL models: "Trained on **measured** receptor potencies (ChEMBL, primary literature;
  IC50/Ki/EC50/AC50 pooled as p_activity = -log10 M). In-vitro potency against a purified/cell receptor;
  it is **not** an in-vivo endocrine hazard call and says nothing about exposure or dose."
* rat oral LD50: "**Measured** acute oral LD50 in rat, median over records (CompTox hazards table),
  reported as log10 mmol/kg bw. Acute lethality only; not chronic, not ecological."
* Everywhere: give the base rate next to any classification number, and never report accuracy.

---
## R5. W-TP abiotic transformation rules (board T-026)
Reviewed W-TP/tp_rules.py (25 reaction SMARTS). Overall sound, textbook, and
correctly flagged as first-generation only. Specific chemistry:
* **OX-ALKENE-CLEAVE is mislabelled.** OH addition to a C=C does not cleave it; cleavage to two carbonyls
  is **ozonolysis** (O3), a different oxidant with a different rate law and different environmental
  concentration. Either re-label the pathway "ozonolysis" or drop it from the oh_oxidation arm. As it
  stands the product set is right but the mechanism attribution is wrong, and the rate class ("fast") is
  only true in air with O3 present.
* **OX-ARHYDROX applied to every aromatic CH** enumerates all regioisomers. Real OH addition is strongly
  directed (ortho/para to EDG, and ipso attack on halogenated rings). Keep, but mark the products
  "regiochemistry not resolved" so the dashboard does not present a para-isomer as *the* product.
* **Missing and environmentally important: hydrolysis of chloro-s-triazines** (chlorotriazine + H2O ->
  hydroxytriazine; acid/base catalysed, the dominant atrazine/simazine TP). Your HYD-ALKYLHALIDE is sp3
  only and PH-ARPHOTOHYD requires light, so this very common TP cannot be produced. Suggested SMARTS:
  `[c:1]([n:2])[Cl]>>[c:1]([n:2])O` restricted to a triazine/pyrimidine ring.
* Also missing, both common: **sulfoxide -> sulfone** (second oxidation; outside "first generation" if you
  count from the parent, but for a thioether parent the sulfone is routinely the observed TP) and
  **tertiary amine -> N-oxide**.
* **HYD-NITRILE** (nitrile -> amide) is correctly flagged slow; abiotically it is negligible at
  environmental pH and is mostly enzymatic. Keep the flag prominent.
* **PH-NITROREDUCE** (nitro -> nitroso) needs a reductant; direct photolysis of nitroaromatics in sunlit
  water more often gives hydroxylated/denitrated products. Flag as conditional, not a default product.
* The finding that products are **not** further from the training set than their parents (median nn_sim
  0.489 vs 0.455) is chemically expected: a first-generation TP differs from the parent by one functional
  group, and Morgan r2 similarity is dominated by the unchanged scaffold. Report it as such.
