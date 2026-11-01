# Three-slide deck (draft)

*Plata lab hackathon work on environmental fate and toxicity. Built 2026-11-01 (v8);
the slide-2 table is read from one file, `data/fate_vs_epi_suite.csv  [shipped aggregate; working file not redistributed; VM-internal]` (subset=leak_free, model=SP; `data/fate_vs_epi_suite.csv` is byte-identical on these rows). The n, the `ours` column and the EPI column really are the same rows: `W-MODEL/eval_v5.py  [not redistributed; VM-internal]` inner-joins the frozen model's test predictions to `W-TOOL/epi_comparator_v3.parquet  [not redistributed; VM-internal]` on standardized InChIKey + endpoint and computes both percentages on that one joined set (EPI estimated values only, `epi_has_experimental == False`). The other numbers are read from `W-SPECTRA/spectrum_only_final_table.md  [not redistributed; VM-internal]`, `data/hazard_spectrum_only_ld50.json  [shipped aggregate; working file not redistributed; VM-internal]` and `scribe_addendum_v5.json  [not redistributed; VM-internal]`. Speaker notes are in italics.*

---

## Slide 1 — The problem

**A chemist designing a molecule that does not exist yet needs to know what it will do in the
environment. The tools that answer that question were fitted to the chemistry we already have.**

- EPI Suite and most QSARs are trained on inventories of commercial chemicals. On a genuinely new
  scaffold they are being asked to extrapolate, and nobody tells the user that is what is happening.
- An analyst who detects an unknown by mass spectrometry has the opposite problem: a measured spectrum
  and no structure at all.
- So we built one predictor for three kinds of input — a structure, a structure plus a measured MS/MS
  spectrum, or **a spectrum alone** — and we measured it only where it matters: on test compounds with
  **no training analogue at Tanimoto ≥ 0.40 on Morgan r2/2048 fingerprints** (under other
  fingerprints some of those compounds do have close analogues, so the stricter cut is the
  novel-scaffold one, where melting point and water solubility still beat EPI Suite and survive
  every control we applied; the other endpoints are shown but not claimed there - `data/attack_strict_novel.csv`, `data/vs_epi_by_scaffold.csv`).

*Speaker note: the single design decision that makes this different is the evaluation, not the model.
Everything we report is leak-free first; the flattered number comes second and is labelled.*

---

## Slide 2 — What it does, measured honestly

**Error as a percentage of the naive guess (always predict the training mean). 100% = no skill.
Leak-free test compounds. `n` is the number of leak-free test compounds carrying BOTH a model
prediction and an EPI Suite estimate for that endpoint — the rows both percentage columns are
scored on. It runs 1-3 lower than the endpoint's total leak-free test rows (`n_test_rows` in the
same file: 305, 405, 454, 822, 368), because EPI Suite returns no usable estimate for a few.**

| endpoint | leak-free n | ours | EPI Suite, same rows |
|---|---|---|---|
| vapor_pressure | 302 | 45% | 93% |
| water_solubility | 403 | 50% | 87% |
| logkow | 451 | 51% | 93% |
| melting_point | 820 | 53% | 84% |
| boiling_point | 367 | 53% | 78% |

- Nine leak-free model-vs-EPI comparisons could be made (12 endpoints exist; EPI Suite has no pKa
  module, and logkoa has 3 leak-free rows). Our model is
  better on 6 unadjusted; EPI Suite is better on 1
  (koh_gas) and we do not know why; two are unresolved (BCF and Henry's law). Four wins survive a
  Bonferroni correction over the nine - melting point, water solubility, boiling point, vapour
  pressure - and those are the only ones we claim. [DISPUTED, deliberately left open: how far the EPI 'home-turf' caveat extends. On PhysProp rows intersected with leak-free, melting point and water solubility keep a margin over EPI Suite and boiling point, vapour pressure, logKow, Henry and BCF are not resolved (`data/label_source_attack.csv`); on ALL PhysProp test rows vapour pressure also keeps one (`data/dg2_fairness_dedup.csv`). The two cells disagree; a human should pick. See whitepaper Section 4.1.]
- The frozen model is **structure + AIMNet2 physics, with zero spectral features**: structure
  descriptors (2265 columns) and AIMNet2 physics (31 columns), 2296 columns in total. The spectral
  models are separate runs and did not produce this table.
- **From a spectrum alone**, with no structure, one HR ESI+ spectrum gives, leak-free, % of naive
  with 95% CI: water solubility 75 [67, 82], vapour pressure 70 [56, 87], logKow 79 [70, 88],
  melting point 86 [79, 93] - which is above the 85%-of-naive skill bar pre-registered for this comparison (P-005) and is therefore shown, not claimed. **[DISPUTED, deliberately left open - do not settle on a slide:** whether melting point counts as a spectrum-only success depends on which spectrum-only model is quoted. W-MODEL's pooled spectra-only arm puts it at 81% of naive leak-free, under the bar; W-SPECTRA's deployed single-spectrum model, quoted above, puts it at 86%, over it. The two do not give the same list, so the paper prints values and gives no count, and so does this slide.** Skill is not established for boiling point (83 [68, 106]) or Henry (93 [78, 104]); the pKa endpoints, Koc and BCF have fewer than 20 leak-free ESI+ spectra and are not scored leak-free (W-SPECTRA one-spectrum model, HR ESI+; per-endpoint values in `W-SPECTRA/spectrum_only_final_table.md  [not redistributed; VM-internal]`). Those spectrum-only intervals
  under-cover (0.81-0.87 empirical against a nominal 0.90). A spectrum buys essentially nothing
  for acute lethality
  (96% of naive against 82% from the
  structure, same 345 compounds). The tool reports which case you are in.
- Every prediction carries a conformal interval **with its measured empirical coverage**, not only its
  nominal level.

*Figure to project: main Figure 1 (headline, leak-free, against EPI) and
Figure 3 (input modes).*

---

## Slide 3 — The live demo

**Open `dashboard/index.html`. No network.**

1. **A new structure.** Paste a SMILES the model has never seen. Watch the physics descriptors compute
   at inference, then the prediction, the interval, the domain flag, the EPI comparator and the
   attribution appear together.
2. **A refusal.** Paste a quaternary ammonium salt and ask for a gas-phase property. The tool refuses
   and says why: the property is *physically undefined* for a permanently charged species. That is not
   missing data, and treating it as a data gap would misdirect a measurement budget.
3. **Spectrum only.** Paste an MS/MS peak list with its precursor m/z and adduct, no structure. A
   prediction with a wider, honestly-labelled interval.

*Speaker note: the thing to leave them with is the third claim — that we measured where the tool fails
and built the failure into the interface, rather than reporting the average and hoping.*
