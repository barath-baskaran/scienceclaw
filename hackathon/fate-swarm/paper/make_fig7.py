#!/usr/bin/env python
"""Figure 7 (v5): what the tool actually faces - the EPA inventory, not the test split.

Built from exactly the files the section quotes:
  W-SPACE/inventory_coverage.csv            (definedness and familiarity of a 40,000 random sample)
  W-MODEL/inventory_predictions_v5_summary.json (shipped model over the inventory physics table)
  W-TOX/r3/inventory_hazard_domain.json     (hazard models, inventory-weighted)
Run: python make_fig7_v5.py
"""
import json, csv, pathlib
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

H = pathlib.Path(__file__).resolve().parent
W = pathlib.Path("(internal path removed)")
OUT = H / "figures_v5"; OUT.mkdir(exist_ok=True)

COV = list(csv.DictReader(open(W / "W-SPACE/inventory_coverage.csv")))
INV = json.load(open(W / "W-MODEL/inventory_predictions_v5_summary.json"))
TOX = json.load(open(W / "W-TOX/r3/inventory_hazard_domain.json"))

OI = ["#0072B2", "#E69F00", "#009E73", "#CC79A7", "#56B4E9", "#D55E00", "#F0E442", "#000000"]
plt.rcParams.update({"font.size": 8, "axes.spines.top": False, "axes.spines.right": False})
fig, ax = plt.subplots(1, 3, figsize=(13.2, 4.3), gridspec_kw={"width_ratios": [1.5, 1.1, 1.0]})

# ---- (a) definedness + familiarity of the inventory, per endpoint -----------------
def fl(r, k):
    try: return float(r[k])
    except Exception: return 0.0

COV = sorted(COV, key=lambda r: -fl(r, "C_far_lt03"))
eps = [r["endpoint"] for r in COV]
y = np.arange(len(eps))
segs = [("C_far_lt03", "defined, far from training (nn_sim < 0.3)", OI[5], ""),
        ("C_mid_03_05", "defined, nn_sim 0.3-0.5", OI[1], ""),
        ("C_near_ge05", "defined, nn_sim >= 0.5", OI[2], ""),
        ("B_nonequivalent", "measurable but not equivalent to our labels (B)", OI[4], "//"),
        ("A_undefined", "physically undefined for the species (A)", OI[0], "xx"),
        ("not_assessed", "not assessed (metal-containing, unparseable)", "0.75", "..")]
left = np.zeros(len(eps))
for key, lab, col, hat in segs:
    v = np.array([fl(r, key) for r in COV])
    ax[0].barh(y, v, left=left, color=col, hatch=hat, edgecolor="k", lw=.3, label=lab)
    left += v
ax[0].set_yticks(y, eps, fontsize=7)
ax[0].set_xlim(0, 1); ax[0].set_xlabel("fraction of a 40,000-structure random sample of the EPA inventory")
ax[0].set_title("a  What the inventory looks like to the tool", loc="left", fontsize=9)
ax[0].legend(fontsize=5.9, frameon=False, loc="lower right", ncol=1)
ax[0].text(0.01, -0.165, "A and B are not data gaps: no experiment on that species would fill them.",
           transform=ax[0].transAxes, fontsize=6.3, color="0.3")

# ---- (b) interval width the inventory actually gets, by familiarity bin ----------
BINS = ["<0.3", "0.3-0.5", "0.5-0.7", ">=0.7"]
eps2 = [e for e in INV["endpoints"] if INV["endpoints"][e].get("median_interval_width_by_bin")]
eps2 = sorted(eps2, key=lambda e: -(INV["endpoints"][e]["median_interval_width_by_bin"].get("<0.3") or 0))[:8]
x = np.arange(len(eps2)); w = 0.2
for k, b in enumerate(BINS):
    v = [INV["endpoints"][e]["median_interval_width_by_bin"].get(b) for e in eps2]
    nrm = [INV["endpoints"][e]["median_interval_width_by_bin"].get(">=0.7") or 1 for e in eps2]
    ax[1].bar(x + (k - 1.5) * w, [a / b2 for a, b2 in zip(v, nrm)], w,
              color=[OI[5], OI[1], OI[2], OI[7]][k], edgecolor="k", lw=.3, label=f"nn_sim {b}")
ax[1].axhline(1.0, color="0.4", ls="--", lw=.9)
ax[1].set_xticks(x, eps2, fontsize=6.4, rotation=35, ha="right")
ax[1].set_ylabel("median 90% interval width,\nrelative to the most familiar bin")
ax[1].set_title("b  The interval the inventory gets", loc="left", fontsize=9)
ax[1].legend(fontsize=6.2, frameon=False, ncol=2)
bf = INV["bin_fraction"]
ax[1].text(0.0, -0.33, "Inventory structures per bin: " + ", ".join(f"{b} {bf.get(b, 0):.0%}" for b in BINS)
           + f"  (n = {INV['n_predicted']:,} predicted)", transform=ax[1].transAxes, fontsize=6.3, color="0.3")

# ---- (c) hazard: test split vs inventory-weighted ---------------------------------
T = {k.split("|")[0]: v for k, v in TOX.items() if k.endswith("|epa_inventory")}
names = list(T)
x = np.arange(len(names))
ax[2].bar(x - .2, [T[k]["test_pct_of_naive_overall"] for k in names], .38, color=OI[2],
          edgecolor="k", lw=.3, label="test split")
ax[2].bar(x + .2, [T[k]["inventory_weighted_pct_of_naive"] for k in names], .38, color=OI[5],
          hatch="//", edgecolor="k", lw=.3, label="inventory-weighted")
for i, k in enumerate(names):
    ax[2].text(i - .2, T[k]["test_pct_of_naive_overall"] + 1.5,
               f"cov\n{T[k]['test_coverage_overall']:.2f}", ha="center", fontsize=5.4)
    ax[2].text(i + .2, T[k]["inventory_weighted_pct_of_naive"] + 1.5,
               f"cov\n{T[k]['inventory_weighted_empirical_coverage']:.2f}", ha="center", fontsize=5.4)
ax[2].axhline(100, color="0.4", ls="--", lw=.9)
ax[2].text(len(names) - .4, 101.5, "no skill", fontsize=6.3, color="0.4", ha="right")
ax[2].set_xticks(x, [n.replace("_", "\n") for n in names], fontsize=6.6)
ax[2].set_ylim(0, 125)
ax[2].set_ylabel("RMSE, % of the naive training-mean guess")
ax[2].set_title("c  Hazard: benchmark against product\n    (small numbers = empirical coverage, nominal 0.90)",
                loc="left", fontsize=9)
ax[2].legend(fontsize=6.4, frameon=False, loc="upper left")

fig.tight_layout()
fig.savefig(OUT / "fig7_inventory.png", dpi=200, bbox_inches="tight")
print("wrote", OUT / "fig7_inventory.png")
