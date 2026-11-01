#!/usr/bin/env python
"""Q-003 closure patch: applied to build_whitepaper.py AFTER patch_to_v5.py.

Defect it answers (D27, from CRITIC's expert-answer correction and the orchestrator's
freeze list): §4.5 told the reader that the cell table was one class out of date and had
not been regenerated. CRITIC has since rebuilt it (`CRITIC/undefined_vs_gap_cells_q003.csv`
via `CRITIC/q003_override.py`), two agents independently compared the derived rule with the
human expert's written answer (`S-7/q003_vs_wtox.md`, `S-1/q003_vs_wtox.md`), and the
dashboard owner found a related SMARTS defect. This patch:

  D27a  replaces the "has not been regenerated" passage with the corrected numbers, all read
        from q003_final.json (built by q003_final.py from the corrected CSV + the comparisons);
  D27b  adds Figure S (figS_q003_corrected.png) drawn from the SAME corrected CSV, so the
        section's numbers carry their own figure;
  D27c  adds Supplementary Table S2: the corrected table in full, every cell with its verdict,
        whether Q-003 moved it, and the reason;
  D27d  records W-TOOL's sulfonyl-SMARTS regression finding (basic pKa of SDS) as a limitation
        in the same section, cited to the override in W-TOOL/tool/wtool_postproc.py.

Rebuild order:  patch_to_v5.py  ->  q003_final.py  ->  patch_q003.py  ->  build_whitepaper.py
Run: python patch_q003.py
"""
import pathlib, sys

H = pathlib.Path(__file__).resolve().parent
P5 = H / "build_whitepaper.py"
src = P5.read_text()
if "q003_final.json" in src:
    print("patch_q003: already applied to build_whitepaper.py (nothing to do)"); sys.exit(0)

lines = src.split("\n")

# ---- D27a/b: replace the Q-003 passage (from the "rule, checked" paragraph to the fig5 call)
i0 = next(i for i, l in enumerate(lines) if l.startswith('W("**The rule, checked against a human expert answer.**'))
i1 = next(i for i, l in enumerate(lines) if l.startswith('W(fig("fig5"'))
assert "not been regenerated" in "\n".join(lines[i0:i1]), "Q-003 passage not found as expected"

NEW = r'''Q3 = json.load(open(H / "q003_final.json"))
_c = Q3["compare"]
_mv = ", ".join(f"{r['endpoint']} ({r['n_labelled']} labelled row" + ("" if r['n_labelled'] == 1 else "s") + ")" for r in Q3["changed_cells"])
_va = Q3["verdicts_after"]; _vb = Q3["verdicts_before"]
W("**The rule, checked against a human expert answer.** The definedness rule above was derived from the endpoint definitions by two agents independently, without sight of the domain expert's written answer to our question on exactly this point. That answer was then compared with both implementations, cell by cell, by two further agents working separately (`S-7/q003_vs_wtox.md` and `S-1/q003_vs_wtox.md`), and resolved by the critic agent. "
  f"The expert answer speaks to {_c['agree'] + _c['disagree']} of the {_c['total']} cells in that implementation; the other {_c['not_covered']} are outside it. "
  f"On {_c['agree']} cells the derived rule and the expert answer agree, with no contradicted verdict and only differences of vocabulary and of how a count is defined - including both of the cells the expert named as genuine gaps rather than undefined (Koc for quaternary ammonium compounds, acidic pKa for PFAS), where a rule that called them undefined would have been wrong in the direction that hides a real data need. That is the useful half: a rule derived from definitions reproduced an expert's reasoning on the cells the expert addressed.\n")
W("**One class changed, and we did not catch it ourselves.** Sulfonate and sulfate salts fall under the same reasoning as quaternary ammonium compounds - permanently charged in any environmentally relevant condition - but the standardisation step neutralised them before the rule was applied, so one implementation classed them as ordinary neutral organics. "
  f"That is now corrected rather than merely flagged: the cell table was rebuilt with `CRITIC/q003_override.py` into `{Q3['source_cells']}`, and the corrected table is what this paper reports. It holds {Q3['n_cells']} class x endpoint cells - the original {Q3['n_cells_base']} plus {Q3['n_cells_new_class']} for the sulfonate/sulfate-salt class ({Q3['n_skeletons_new_class']} skeletons). "
  f"{Q3['n_changed']} cells move from defined to physically undefined, and they are exactly the gas-phase and neutral-species endpoints: {_mv}. {Q3['n_labelled_in_changed_cells']} labelled rows therefore carry numbers for a quantity that does not exist for the species as drawn, and must not be counted either as training signal or as evidence that the gap is filled. "
  f"Across the corrected table the verdicts are: undefined {_va.get('undefined',0)} (was {_vb.get('undefined',0)}), defined {_va.get('defined',0)}, defined-where-an-ionisable-site-exists {_va.get('defined_if_site',0)}, assay-unattainable {_va.get('assay_unattainable',0)}, not assessed {_va.get('not_assessed',0)} (Figure S" + str(len(SUPP) + 1) + "). "
  "The shipped predictor was changed to match: it refuses these cells outright (`display='refuse'`) instead of returning a wide interval, so the correction reaches the user and not only the paper.\n")
W("**One count discrepancy in that comparison is now explained, and it is another class-definition bug.** The two cross-check agents could not reconcile the number of acidic-pKa labels for PFAS: the expert answer says 4, the cell table says 16. The cause is the PFAS pattern used to build the cell table, which matches any trifluoromethyl carbon and so flags 1,203 labelled structures where the stricter definition used everywhere else in this paper - two adjacent fluorinated sp3 carbons - flags 397, a strict subset (`PRINCIPAL/pfas_class_scope_S5.md`). The verdicts in the corrected table do not change, but its PFAS counts are an upper bound by roughly a factor of three. Every PFAS count quoted in the main text, including the coverage and data-priority analyses, uses the stricter definition.\n")
W(sfig("figS_q003", "The expert cross-check changed the bookkeeping for one compound class, and we report the corrected table rather than the one we first built. (a) Verdict counts over all " + str(Q3["n_cells"]) + " class x endpoint cells before and after the Q-003 correction; only the 'undefined' column moves. (b) The " + str(Q3["n_changed"]) + " cells that moved, with the number of labelled rows in each that are therefore physically undefined values rather than data. Conclude that the undefined-versus-gap split is a judgement that can be audited and corrected, and that correcting it removes " + str(Q3["n_labelled_in_changed_cells"]) + " rows from what looked like evidence."))
W(f"**Two deviations from the expert answer are deliberate and stay.** {_c['disagree']} cells - the {' and '.join(_c['disagree_classes'])} classes across the same six endpoints - are reported as 'not assessed' rather than undefined, because the note's non-volatile clause cannot be applied from a structure drawing (resolution recorded by the critic and principal agents); those cells also hold real measurements (organometallic boiling points and vapour pressures among them), which an 'undefined' verdict would discard. "
  "Neutral non-volatile solids likewise stay defined, because a vapour pressure exists for them even when it is far too small to measure - that is a measurement problem, not a definitional one. Both deviations are recorded as disagreements, not resolved in our favour by silence. "
  f"Supplementary Table S2 gives every cell of the corrected table with its reasoning; the three-way A/B/C table earlier in this section, and Table S1, are W-SPACE's independent implementation on a different class scheme and a different denominator (inventory skeletons, not labelled rows), and were not rebuilt - that owner's work was closed. The two implementations do not conflict on behaviour: W-SPACE places the same strong-acid parents in category B, 'defined only for an unpopulated neutral microspecies', which the dashboard also refuses. The bookkeeping differs; the number the user is shown does not.\n")
W("**A defect found by the correction, in our own code.** Chasing the same class through the dashboard, the tool owner found that the basic-site pattern used to decide whether a basic pKa applies, `[P,As,Se,S;X3,X4]=O`, also matches the S=O of a sulfonate or sulfate group. Sodium dodecyl sulfate was consequently given a basic pKa of 6.6, a value with no chemical meaning. The dashboard now withholds it and carries a strong-acid caveat on the acidic pKa of sulfonates, where the model returns about 7 and the true value is below 0 (override and its reasoning in `W-TOOL/tool/wtool_postproc.py`). We report it because it is the same failure as the one above seen from the other end: a SMARTS written for one purpose quietly deciding a definedness question it was never reviewed for.\n")
'''
lines[i0:i1] = NEW.strip("\n").split("\n")
src = "\n".join(lines)

# ---- D27b: register the figure
ANCH = 'SUPP = {}'
FIGREG = '''FIGS["figS_q003"] = {"file": "figures_v5/figS_q003_corrected.png",
                     "source": "CRITIC/undefined_vs_gap_cells_q003.csv + S-7/q003_vs_wtox.md (drawn by SCRIBE/q003_final.py)",
                     "by": "q003_final.py"}
SUPP = {}'''
assert src.count(ANCH) == 1
src = src.replace(ANCH, FIGREG, 1)

# ---- D27c: Supplementary Table S2, straight from the corrected CSV
ANCH2 = 'W("## Supplementary tables: per-bin error\\n")'
TBL = r'''W("## Supplementary Table S2: the corrected definedness table (Q-003)\n")
W(f"Every class x endpoint cell of `{Q3['source_cells']}`, after the expert cross-check. "
  "`moved` marks the cells the correction changed. Counts are over the denominator that file uses for the class; "
  "the sulfonate/sulfate-salt rows use a labelled-set denominator and are not comparable with Table S1's inventory counts. "
  "Rows of class `pfas` inherit the over-broad PFAS pattern described in Section 4.5 and overcount by roughly a factor of three (`PRINCIPAL/pfas_class_scope_S5.md`); the verdicts stand, the counts are an upper bound.\n")
W("| class | endpoint | verdict | moved | inventory n | labelled n | reasoning |\n|---|---|---|---|---|---|---|")
import csv as _csv
for _r in _csv.DictReader(open(Q3["source_cells"])):
    _mo = "yes" if str(_r.get("changed_by_q003", "")).lower() == "true" else ""
    _rs = (_r.get("q003_reason") or _r.get("reasoning") or "").replace("|", "/")
    W(f"| {_r['compound_class']} | {_r['endpoint']} | {_r['q003_verdict']} | {_mo} | {_r['n_inventory']} | {_r['n_labelled']} | {_rs} |")
W("")
W("## Supplementary tables: per-bin error\n")'''
assert src.count(ANCH2) == 1
src = src.replace(ANCH2, TBL, 1)

ANCH3 = '''_neg.append("**Acidic pKa has no skill on novel chemistry**'''
NEG = """_neg.append(f"**Our own definedness bookkeeping was wrong for one compound class, and an expert cross-check caught it.** A standardisation step neutralised sulfonate and sulfate salts before the rule that decides whether a property exists was applied, so {Q3['n_changed']} gas-phase and neutral-species cells covering {Q3['n_skeletons_new_class']} skeletons were called defined when they are physically undefined; {Q3['n_labelled_in_changed_cells']} labelled rows are affected. The table was rebuilt, the shipped predictor now refuses those cells, and a related SMARTS defect that gave sodium dodecyl sulfate a basic pKa of 6.6 was found and fixed in the dashboard (`CRITIC/undefined_vs_gap_cells_q003.csv`, `W-TOOL/tool/wtool_postproc.py`).")\n"""
assert src.count(ANCH3) == 1
src = src.replace(ANCH3, NEG + ANCH3, 1)

P5.write_text(src)
print("patch_q003: applied D27a-d to build_whitepaper.py")
