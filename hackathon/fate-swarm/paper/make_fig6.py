#!/usr/bin/env python
"""Figure 6 (v5): hazard endpoints on MEASURED labels, per familiarity bin.

Built from exactly the files §4.6 of the whitepaper quotes:
  W-TOX/r3/results_hazard.json          (W-TOX, measured ChEMBL / CompTox labels)
  CRITIC/audit_wtox_chembl_control.csv  (CRITIC, familiarity-only control)
No number in this script is typed by hand.
Run: python make_fig6.py
"""
import json, csv, pathlib
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

H = pathlib.Path(__file__).resolve().parent
OUT = H / "figures_v5"; OUT.mkdir(exist_ok=True)
# the text of 4.6 quotes scribe_numbers.json['tox_r3'], which make_figures.py derives
# from W-TOX/r3/results_hazard.json plus the per-row preds_*.parquet (leak-free subsets).
# The figure reads the same object, so figure and text cannot disagree.
NUM = pathlib.Path(H / "scribe_numbers.json")
CTL = pathlib.Path("CRITIC/audit_wtox_chembl_control.csv")

T = json.load(open(NUM))["tox_r3"]
CT = {r["endpoint"]: r for r in csv.DictReader(open(CTL))} if CTL.exists() else {}

# Okabe-Ito, colour-blind safe
OI = ["#0072B2", "#E69F00", "#009E73", "#CC79A7", "#56B4E9", "#D55E00", "#000000"]
BINS = ["<0.3", "0.3-0.5", "0.5-0.7", ">=0.7"]
CLS = [e for e in T if T[e].get("kind") == "classification"]
REG = [e for e in T if T[e].get("kind") == "regression"]
NICE = {"er_active": "ER-alpha active", "ar_active": "AR active",
        "er_potency": "ER-alpha potency", "ar_potency": "AR potency",
        "rat_oral_ld50": "rat oral LD50"}

plt.rcParams.update({"font.size": 8, "axes.spines.top": False, "axes.spines.right": False})
fig, ax = plt.subplots(1, 3, figsize=(12.6, 4.0), gridspec_kw={"width_ratios": [1.15, 1.15, 1.25]})

# ---- panels a, b: receptor activity, PR-AUC against each bin's own base rate ----
for j, e in enumerate(CLS):
    a = ax[j]
    cells = [("all\ntest", T[e]["full"]), ("leak-\nfree", T[e]["leak_free"])] + \
            [(b, (T[e].get("by_bin") or {}).get(b, {})) for b in BINS]
    x = np.arange(len(cells))
    pr = [c.get("pr_auc") for _, c in cells]
    br = [c.get("base_rate") for _, c in cells]
    a.bar(x, [p if p is not None else 0 for p in pr], 0.62,
          color=[OI[0], OI[0]] + [OI[1]] * len(BINS), edgecolor="k", lw=.4,
          hatch=["", "//"] + [""] * len(BINS))
    for xi, (p, b) in enumerate(zip(pr, br)):
        if b is None: continue
        a.plot([xi - .36, xi + .36], [b, b], color="k", ls="--", lw=1.4, zorder=5)
        if p is not None:
            a.annotate("", xy=(xi, p), xytext=(xi, b),
                       arrowprops=dict(arrowstyle="-", lw=0))
            a.text(xi, max(p, b) + .025, f"+{p - b:.2f}", ha="center", fontsize=6.4)
    c = CT.get(e)
    if c:
        v = float(c["pr_auc_nnsim_only"])
        a.plot([-.5, 1.5], [v, v], color=OI[5], lw=2.0, zorder=6)
        a.text(1.6, v, f"familiarity-only\ncontrol {v:.2f}", color=OI[5], fontsize=6.4, va="center")
    a.set_xticks(x, [lab for lab, _ in cells], fontsize=6.8)
    a.set_ylim(0, 1.08); a.set_ylabel("PR-AUC  (no-skill value = base rate)")
    a.set_title(f"{'ab'[j]}  {NICE.get(e, e)}: PR-AUC vs base rate", loc="left", fontsize=9)
    ns = "  ".join(f"n={c.get('n')}" for _, c in cells[:2])
    a.text(0.0, -0.21, f"measured ChEMBL labels; dashed = that cell's base rate;  {ns}",
           transform=a.transAxes, fontsize=6.2, color="0.3")
ax[0].plot([], [], "k--", lw=1.4, label="base rate (no skill)")
ax[0].bar([], [], color=OI[0], label="pooled subsets")
ax[0].bar([], [], color=OI[1], label="by familiarity bin (nn_sim to train)")
ax[0].legend(fontsize=6.3, frameon=False, loc="upper left")

# ---- panel c: regression hazards, % of the naive training-mean guess ----
a = ax[2]
cells = [("leak-free", "leak_free"), ("all test", "full")] + [(b, b) for b in BINS]
x = np.arange(len(REG)); w = 0.14
for k, (lab, key) in enumerate(cells):
    vals, covs = [], []
    for e in REG:
        m = T[e].get(key) if key in ("leak_free", "full") else (T[e].get("by_bin") or {}).get(key, {})
        vals.append(m.get("pct_naive"))
        covs.append(m.get("coverage"))
    col = OI[2] if key == "leak_free" else (OI[6] if key == "full" else OI[1])
    alpha = 1.0 if key in ("leak_free", "full") else min(1.0, 0.35 + 0.14 * (k - 2))
    bars = a.bar(x + (k - (len(cells) - 1) / 2) * w, [v if v is not None else 0 for v in vals], w,
                 color=col, alpha=alpha, edgecolor="k", lw=.3,
                 label=lab if k < 2 else (f"bin {lab}" if k == 2 else f"bin {lab}"))
    for xi, (v, c) in enumerate(zip(vals, covs)):
        if v is None or c is None: continue
        a.text(x[xi] + (k - (len(cells) - 1) / 2) * w, v + 1.5, f"{c:.2f}",
               ha="center", fontsize=5.2, rotation=90, color="0.25")
a.axhline(100, color="0.4", ls="--", lw=1.0)
a.text(len(REG) - 0.45, 101.5, "no skill", fontsize=6.4, color="0.4", ha="right")
nom = T[REG[0]].get("nominal")
a.set_xticks(x, [f"{NICE.get(e, e)}\n({T[e].get('units','')})\nn lf={T[e]['leak_free']['n']}" for e in REG], fontsize=6.6)
a.set_ylabel("RMSE, % of the naive training-mean guess")
a.set_ylim(0, 125)
a.set_title(f"c  Potency and lethality: error and empirical coverage\n    (small numbers = empirical coverage; nominal {nom:.2f})",
            loc="left", fontsize=9)
a.legend(fontsize=6.0, frameon=False, ncol=2, loc="upper left")

fig.tight_layout()
fig.savefig(OUT / "fig6_toxicity.png", dpi=200, bbox_inches="tight")
print("wrote", OUT / "fig6_toxicity.png")
