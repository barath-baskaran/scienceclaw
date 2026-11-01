#!/usr/bin/env python
"""Q-003 closure: regenerate the corrected definedness cell numbers + a figure from the
SAME file the paper's §4.5 tail now quotes.

Inputs (read, never retyped):
  CRITIC/undefined_vs_gap_cells_q003.csv   corrected cell table (W-TOX's 180 cells + the
                                           sulfonate/sulfate-salt class CRITIC added), with
                                           verdict (pre), q003_verdict (post), changed_by_q003
  S-7/q003_vs_wtox.md, S-1/q003_vs_wtox.md two independent note-vs-rule comparisons

Outputs:
  SCRIBE/q003_final.json                   every number the paper states in the Q-003 passage
  SCRIBE/figures_v5/figS_q003_corrected.png

Run: python q003_final.py
"""
import json, re, pathlib
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

H = pathlib.Path(__file__).resolve().parent
# Resolve inputs from the working tree, or from beside this script when it ships in the
# public repo (where the inputs are copied to paper/CRITIC/ and paper/S-7/).
W = H if (H / "CRITIC/undefined_vs_gap_cells_q003.csv").exists() else pathlib.Path("(internal path removed)")
OUT = H / "figures_v5"; OUT.mkdir(exist_ok=True)
CSV = W / "CRITIC/undefined_vs_gap_cells_q003.csv"
S7 = W / "S-7/q003_vs_wtox.md"
S1 = W / "S-1/q003_vs_wtox.md"

d = pd.read_csv(CSV)
d["changed_by_q003"] = d["changed_by_q003"].astype(str).str.lower().eq("true")
NEWCLS = [c for c in d.compound_class.unique() if c.startswith("sulfonate_sulfate_salt")]
assert len(NEWCLS) == 1, NEWCLS
newcls = NEWCLS[0]

pre = d.verdict.map(lambda v: "defined" if str(v).startswith("defined (before") else v).value_counts().to_dict()
post = d.q003_verdict.value_counts().to_dict()
ch = d[d.changed_by_q003].sort_values("endpoint")

# the six gas-phase / neutral-species endpoints, named by the data rather than hard-coded
six = sorted(ch.endpoint.tolist())

# --- the two independent note-vs-rule comparisons -------------------------------------
s7 = S7.read_text()
m = re.search(r"AGREE\s*=\s*(\d+);\s*DISAGREE\s*=\s*(\d+);\s*NOT COVERED by the note\s*=\s*(\d+);\s*total\s*(\d+)", s7)
agree, disagree, notcov, total = (int(x) for x in m.groups())
# classes behind the DISAGREE list (reported, not hard-coded)
dis_block = s7.split("## DISAGREE")[1].split("## NOT COVERED")[0]
dis_cls = sorted({l.split(" x ")[0].lstrip("- ").strip() for l in dis_block.splitlines() if l.startswith("- ")})
dis_eps = sorted({l.split(" x ")[1].split(":")[0].strip() for l in dis_block.splitlines() if l.startswith("- ")})

N = {
    "source_cells": str(CSV),
    "source_compare_primary": str(S7),
    "source_compare_second": str(S1),
    "n_cells": int(len(d)),
    "n_cells_base": int(len(d) - (d.compound_class == newcls).sum()),
    "new_class_label": newcls,
    "n_cells_new_class": int((d.compound_class == newcls).sum()),
    "verdicts_before": pre,
    "verdicts_after": post,
    "n_changed": int(len(ch)),
    "changed_cells": [
        {"endpoint": r.endpoint, "class": r.compound_class, "from": r.verdict, "to": r.q003_verdict,
         "n_inventory": int(r.n_inventory), "n_labelled": int(r.n_labelled)} for r in ch.itertuples()
    ],
    "changed_endpoints": six,
    "n_skeletons_new_class": int(ch.n_inventory.max()),
    "n_labelled_in_changed_cells": int(ch.n_labelled.sum()),
    "compare": {"agree": agree, "disagree": disagree, "not_covered": notcov, "total": total,
                "disagree_classes": dis_cls, "disagree_endpoints": dis_eps,
                "disagree_resolution": "left as not_assessed (CRITIC/PRINCIPAL): the note's "
                                       "non-volatile clause cannot be applied from a structure drawing"},
}
json.dump(N, open(H / "q003_final.json", "w"), indent=1)

# --------------------------------------------------------------------- figure
OI = {"undefined": "#D55E00", "defined": "#0072B2", "defined_if_site": "#56B4E9",
      "not_assessed": "#999999", "assay_unattainable": "#CC79A7"}
order = ["undefined", "defined", "defined_if_site", "assay_unattainable", "not_assessed"]
fig, ax = plt.subplots(1, 2, figsize=(7.2, 3.1), gridspec_kw={"width_ratios": [1.15, 1]})
plt.rcParams.update({"font.size": 8})

# (a) before vs after verdict counts
x = range(len(order)); wdt = 0.38
ax[0].bar([i - wdt / 2 for i in x], [pre.get(k, 0) for k in order], wdt, color="#BBBBBB",
          edgecolor="black", linewidth=0.4, label="before Q-003 check")
ax[0].bar([i + wdt / 2 for i in x], [post.get(k, 0) for k in order], wdt,
          color=[OI[k] for k in order], edgecolor="black", linewidth=0.4, label="after (shipped)")
for i, k in enumerate(order):
    ax[0].text(i + wdt / 2, post.get(k, 0) + 1.5, str(post.get(k, 0)), ha="center", fontsize=7)
ax[0].set_xticks(list(x)); ax[0].set_xticklabels([k.replace("_", "\n") for k in order], fontsize=7)
ax[0].set_ylabel(f"class x endpoint cells (of {len(d)})"); ax[0].legend(fontsize=6.5, frameon=False)
ax[0].set_title(f"(a) {len(ch)} cells move to 'undefined'", fontsize=8, loc="left")
ax[0].spines[["top", "right"]].set_visible(False)

# (b) the cells that moved, with their labelled-row counts
lab = [f"{r['endpoint']}" for r in N["changed_cells"]]
val = [r["n_labelled"] for r in N["changed_cells"]]
ax[1].barh(range(len(lab)), val, color=OI["undefined"], edgecolor="black", linewidth=0.4)
for i, v in enumerate(val):
    ax[1].text(v + 2, i, str(v), va="center", fontsize=7)
ax[1].set_yticks(range(len(lab))); ax[1].set_yticklabels(lab, fontsize=7); ax[1].invert_yaxis()
ax[1].set_xlabel("labelled rows now flagged physically undefined")
ax[1].set_title(f"(b) sulfonate/sulfate salts, {int(ch.n_inventory.max())} skeletons",
                fontsize=8, loc="left")
ax[1].spines[["top", "right"]].set_visible(False)
ax[1].set_xlim(0, max(val) * 1.25 + 2)
fig.tight_layout()
fig.savefig(OUT / "figS_q003_corrected.png", dpi=200)
print(json.dumps({k: N[k] for k in ("n_cells", "n_changed", "verdicts_after", "compare")}, indent=1))
print("wrote q003_final.json and figures_v5/figS_q003_corrected.png")
