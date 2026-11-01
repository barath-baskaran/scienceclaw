"""SCRIBE Run-3 numbers + figures builder (v4).

Reads ONLY the files listed in sources.json, computes every number the whitepaper states with ONE scorer,
writes scribe_numbers.json, and draws every figure from the same in-memory tables.

Scorer
  % of naive = 100 * RMSE(model) / RMSE(predict the training-split mean of that endpoint), on the SAME rows; 100 = no skill.
  Leak-free  = per-row `leak_free` column if the file has one, else test skeleton NOT in W-SPACE quarantine_skeletons.txt.
  Familiarity bins = nn_sim_train (max Morgan-r2 Tanimoto to the training set, labels_v2): <0.3, 0.3-0.5, 0.5-0.7, >=0.7.
  Cells with n < 20 are reported as unresolvable (None).
  Empirical coverage = fraction of test labels inside [lo, hi]; 95% Wilson interval on that fraction.
  Paired differences = cluster bootstrap (labels_v2 cluster), 1000 resamples, same rows, only the feature set differs.
Rerun:  python make_figures.py
"""
import json, os, pathlib, traceback, datetime
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

H = pathlib.Path(__file__).resolve().parent
OUT = H / "figures_v4"; OUT.mkdir(exist_ok=True)
SRC = json.load(open(H / "sources.json"))
def RP(p): return p if (p is None or os.path.isabs(p)) else str((H / p).resolve())
def P(k): return RP(SRC[k]["path"])
OI = ["#0072B2", "#E69F00", "#009E73", "#CC79A7", "#56B4E9", "#D55E00", "#F0E442", "#000000"]  # Okabe-Ito
MK = ["o", "s", "^", "D", "v", "P", "X", "*"]
BINS = [(0, .3, "<0.3"), (.3, .5, "0.3-0.5"), (.5, .7, "0.5-0.7"), (.7, 1.01, ">=0.7")]
BL = [b[2] for b in BINS]
MIN_N = 20
plt.rcParams.update({"font.size": 8.5, "axes.spines.top": False, "axes.spines.right": False,
                     "savefig.dpi": 200, "font.family": "DejaVu Sans"})
RNG = np.random.default_rng(0)
UCELLS = []

N = {"built": datetime.datetime.now().isoformat(timespec="minutes"), "sources": SRC, "errors": {},
     "definitions": {
         "pct_naive": "100*RMSE(model)/RMSE(training-split mean), same rows; 100 = no skill",
         "leak_free": "per-row leak_free flag from the result file, else test skeleton not in W-SPACE quarantine_skeletons.txt (nn-sim to any train skeleton >= 0.40)",
         "bins": "nn_sim_train from labels_v2 = max Morgan r2 2048-bit Tanimoto to the training split",
         "min_n": MIN_N, "bootstrap": "cluster bootstrap over labels_v2 clusters, 1000 resamples, seed 0"}}

lab = pd.read_parquet(P("labels"))
TRAIN_MEAN = lab[lab.split == "train"].groupby("endpoint").value.mean().to_dict()
UNITS = lab.groupby("endpoint").units.first().to_dict()
test_lab = lab[lab.split == "test"]
NN = test_lab.groupby(["endpoint", "skeleton"]).nn_sim_train.max()
CL = lab.groupby("skeleton").cluster.first()
QUAR = set(pathlib.Path(P("quarantine")).read_text().split()) if pathlib.Path(P("quarantine")).exists() else set()
N["units"] = UNITS


# ---------------- scorer ----------------
def rmse(a, b): return float(np.sqrt(np.mean((np.asarray(a, float) - np.asarray(b, float)) ** 2)))
def wilson(k, n, z=1.96):
    if n == 0: return (None, None)
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d; h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (float(c - h), float(c + h))
def prep(df, ep="endpoint", y="y", nn=None):
    """Attach naive, leak-free flag, nn bin, cluster."""
    d = df.copy()
    if y != "y": d = d.rename(columns={y: "y"})
    if nn and nn in d and nn != "nn": d["nn"] = d[nn]
    elif "nn_sim_train" in d: d["nn"] = d["nn_sim_train"]
    else: d["nn"] = [NN.get((e, s), np.nan) for e, s in zip(d[ep], d.skeleton)]
    if "nn_sim_train" not in d:  # prefer labels' nn_sim_train where the file has its own similarity column
        lab_nn = [NN.get((e, s), np.nan) for e, s in zip(d[ep], d.skeleton)]
        d["nn"] = pd.Series(lab_nn, index=d.index).fillna(d["nn"])
    d["lf"] = d["leak_free"].astype(bool) if "leak_free" in d else ~d.skeleton.isin(QUAR)
    d["bin"] = pd.cut(d.nn, [b[0] for b in BINS] + [1.01], labels=BL, right=False)
    d["naive"] = d["train_mean"] if "train_mean" in d else d[ep].map(TRAIN_MEAN)
    if "cluster" not in d: d["cluster"] = d.skeleton.map(CL)
    return d
def score(d, col, lo=None, hi=None):
    d = d[d[col].notna() & d.y.notna()]
    n = len(d)
    r = {"n": n, "rmse": rmse(d[col], d.y) if n else None, "rmse_naive": rmse(d.naive, d.y) if n else None,
         "pct_naive": (100 * rmse(d[col], d.y) / rmse(d.naive, d.y)) if n >= MIN_N else None}
    if lo and hi and lo in d and n:
        k = int(((d.y >= d[lo]) & (d.y <= d[hi])).sum())
        r.update(coverage=k / n if n >= MIN_N else None, coverage_ci=wilson(k, n) if n >= MIN_N else (None, None),
                 median_width=float((d[hi] - d[lo]).median()))
    return r
def score_all(d, col, lo=None, hi=None):
    return {"full": score(d, col, lo, hi), "leak_free": score(d[d.lf], col, lo, hi),
            "by_bin": {b: score(d[d.bin == b], col, lo, hi) for b in BL}}
def paired_boot(d, a, b, B=1000):
    """CI of pct_naive(b) - pct_naive(a) on identical rows, resampling clusters."""
    d = d[d[a].notna() & d[b].notna()]
    if len(d) < MIN_N: return None
    g = d.groupby("cluster"); keys = list(g.groups); idx = [g.indices[k] for k in keys]
    ya, yb, y, nv = d[a].values, d[b].values, d.y.values, d.naive.values
    def stat(ii):
        den = np.sqrt(np.mean((nv[ii] - y[ii]) ** 2))
        return 100 * (np.sqrt(np.mean((yb[ii] - y[ii]) ** 2)) - np.sqrt(np.mean((ya[ii] - y[ii]) ** 2))) / den
    full = stat(np.arange(len(d)))
    bs = []
    for _ in range(B):
        pick = RNG.integers(0, len(keys), len(keys)); ii = np.concatenate([idx[j] for j in pick])
        bs.append(stat(ii))
    lo, hi = np.percentile(bs, [2.5, 97.5])
    return {"n": len(d), "n_clusters": len(keys), "diff_pp": float(full), "ci_lo": float(lo), "ci_hi": float(hi),
            "excludes_0": bool(lo > 0 or hi < 0)}
def nz(x): return np.nan if x is None else x
def section(name):
    def deco(fn):
        try: fn()
        except Exception as ex:
            N["errors"][name] = f"{type(ex).__name__}: {ex}"; traceback.print_exc()
        return fn
    return deco
def save(fig, name):
    fig.savefig(OUT / name, bbox_inches="tight"); plt.close(fig)


# ---------------- 1. fate headline (shipped model) ----------------
FATE = {}
@section("fate")
def _():
    cfg = SRC["fate"]; d = prep(pd.read_parquet(RP(cfg["path"])).rename(columns={"value": "y"}))
    FATE["df"] = d
    out = {}
    for ep in sorted(d.endpoint.unique()):
        de = d[d.endpoint == ep]; out[ep] = {"units": UNITS.get(ep)}
        for v in cfg["variants"]:
            out[ep][v] = score_all(de, v, v + "_lo", v + "_hi")
            out[ep][v]["interval_methods"] = {m: score_all(de, v, v + a, v + b) for m, (a, b) in cfg.get("interval_methods", {}).items() if v + a in de}
        out[ep]["paired_vs_ref"] = {s: paired_boot(sub, cfg["reference"], cfg["shipped"])
                                    for s, sub in [("full", de), ("leak_free", de[de.lf])]} if cfg["reference"] != cfg["shipped"] else {}
    N["fate"] = out
    try:
        rj = json.load(open(RP(cfg["results_json"])))
        if "nominal_level" in rj: N["fate_nominal"] = {ep: rj["nominal_level"] for ep in out}; N["fate_interval"] = rj.get("shipped_interval")
        else: N["fate_nominal"] = {ep: v["variants"][cfg["shipped"]]["full"].get("conformal_nominal") for ep, v in rj["endpoints"].items()}
    except Exception as ex: N["fate_nominal"] = {}; N["errors"]["fate_nominal"] = str(ex)


# ---------------- 2. EPI comparator on identity-matched identical rows ----------------
@section("epi")
def _():
    cfg = SRC["fate"]; d = FATE["df"]
    e = pd.read_parquet(P("epi"))
    N["epi_status_counts"] = e.epi_status.value_counts().to_dict()
    e = e[(e.epi_status == "ok") & e.epi_value.notna()][["endpoint", "inchikey_std", "measured", "epi_value"]].rename(columns={"epi_value": "converted_value"})
    # match on endpoint + InChIKey + measured value so duplicate label rows of one InChIKey are not cross-joined
    d2 = d.assign(_m=d.y.round(6)); e = e.assign(_m=e.measured.round(6)).drop(columns="measured").drop_duplicates(["endpoint", "inchikey_std", "_m"])
    m = d2.merge(e, on=["endpoint", "inchikey_std", "_m"], how="inner")
    N["epi_join"] = {"model_rows": len(d), "matched_rows": len(m)}
    out = {}
    for ep in sorted(m.endpoint.unique()):
        de = m[m.endpoint == ep]
        out[ep] = {"n_test_rows": int((d.endpoint == ep).sum()), "model": score_all(de, cfg["shipped"]), "epi": score_all(de, "converted_value"),
                   "model_ref": score_all(de, cfg["reference"]),
                   "paired_epi_minus_model": {s: paired_boot(sub, cfg["shipped"], "converted_value") for s, sub in [("full", de), ("leak_free", de[de.lf])]}}
    N["epi"] = out


# ---------------- 2b. joint EPI comparison with label-quality and overlap controls (READER-1 + READER-2) ----------------
EJ = []
@section("epi_joint")
def _():
    j = pd.read_csv(P("epi_joint"))
    if "model_variant" in j: j = j[j.model_variant == SRC["epi_joint"].get("model_variant", "frozen_v4_struct_only")]
    def rng_(x):
        try: a, b = str(x).split(".."); return float(a), float(b)
        except Exception: return (None, None)
    for c in ["d_rmse_ci95", "d_medae_ci95", "did_ci95"]:
        j[c + "_lo"] = [rng_(x)[0] for x in j[c]]; j[c + "_hi"] = [rng_(x)[1] for x in j[c]]
    EJ.append(j)
    out = {}
    for r in j.to_dict("records"):
        out.setdefault(r["subset"], {}).setdefault(r["endpoint"], {})[r["cut"]] = {k: (None if (isinstance(v, float) and v != v) else v) for k, v in r.items() if k not in ("subset", "endpoint", "cut")}
    N["epi_joint"] = out


# ---------------- 2c. evaluation views (W-SPACE) and EPI exclusion-rule sensitivity (CRITIC) ----------------
ES, ER = [], []
@section("eval_splits")
def _():
    d = pd.read_csv(P("eval_splits")); ES.append(d)
    N["eval_splits"] = {f"{r.endpoint}|{r.view}|{r.bin}": {"n": int(r.n), "pct_naive": float(r.pct_naive) if r.n >= MIN_N else None,
                        "lo": float(r.pct_naive_lo) if r.n >= MIN_N else None, "hi": float(r.pct_naive_hi) if r.n >= MIN_N else None} for r in d.itertuples()}
@section("epi_rules")
def _():
    d = pd.read_csv(P("epi_rules")); v = pd.read_csv(SRC["epi_rules"]["verdicts"]); ER.extend([d, v])
    N["epi_rules"] = d.where(d.notna(), None).to_dict("records"); N["epi_rule_verdicts"] = v.to_dict("records")
    N["second_source_logkow"] = json.load(open(P("second_source")))


# ---------------- 3. feature-block ablation by familiarity ----------------
def run_ablation(key):
    cfg = SRC[key]; raw = pd.read_parquet(RP(cfg["path"]))
    if cfg.get("format") == "long":
        idx = ["endpoint", "skeleton", "y"] + (["fam"] if "fam" in raw else [])
        w = raw.pivot_table(index=idx, columns="variant", values=["yhat", "lo", "hi"], aggfunc="first")
        w.columns = [f"{v}" if s == "yhat" else f"{v}_{s}" for s, v in w.columns]; w = w.reset_index()
    else: w = raw.rename(columns={"value": "y"})
    d = prep(w, nn="fam" if "fam" in w else None)
    out = {}
    for ep in sorted(d.endpoint.unique()):
        de = d[d.endpoint == ep].dropna(subset=cfg["variants"])  # identical rows for every variant
        out[ep] = {"n": len(de), "variants": {v: score_all(de, v, v + "_lo", v + "_hi") for v in cfg["variants"]},
                   "paired_vs_ref": {v: {s: paired_boot(sub, cfg["reference"], v) for s, sub in [("full", de), ("leak_free", de[de.lf])]}
                                     for v in cfg["variants"] if v != cfg["reference"]}}
    N[key] = out
@section("ablation")
def _(): run_ablation("ablation")
@section("ablation_run2")
def _(): run_ablation("ablation_run2")


# ---------------- 4. spectrum-only ladder ----------------
@section("spectra_only")
def _():
    cfg = SRC["spectra_only"]; raw = pd.read_parquet(RP(cfg["path"]))
    N["spectra_only_naive"] = "training-subset mean of the same compounds (per-row `naive` column from the result file)" if "naive" in raw else "labels_v2 training-split mean (whole endpoint), NOT the spectrum subset mean"
    out = {}
    for blk in cfg.get("blocks", {"all": "all"}):
        rb = raw[raw.block == blk] if "block" in raw else raw
        d = prep(rb, y=cfg.get("y", "y"), nn=cfg.get("nn"))
        if "naive" in rb: d["naive"] = rb["naive"].values
        lv = cfg["ei_levels"] if blk == "ei" and "ei_levels" in cfg else cfg["levels"]
        out[blk] = {}
        for ep in sorted(d.endpoint.unique()):
            de = d[d.endpoint == ep].dropna(subset=[c for c, *_ in lv if c in d])
            if len(de) == 0: continue
            out[blk][ep] = {"n": len(de), "levels": {c: score_all(de, c, lo, hi) for c, _, lo, hi in lv if c in de},
                            "contrasts": {f"{a}->{b}": {s_: paired_boot(sub, a, b) for s_, sub in [("full", de), ("leak_free", de[de.lf])]}
                                          for a, b in cfg.get("contrasts", []) if a in de and b in de}}
    N["spectra_only"] = out
    N["spectra_only_labels"] = {c: l for c, l, *_ in cfg["levels"] + cfg.get("ei_levels", [])}
    try: N["spectra_mass_regularised"] = json.load(open(RP(cfg["mass_regularised"])))
    except Exception as ex: N["errors"]["mass_regularised"] = str(ex)


# ---------------- 4b. label replicate-noise floor (READER-1) ----------------
@section("noise_floor")
def _():
    c = SRC["noise_floor"]; nf = pd.read_csv(RP(c["path"]))
    nf = nf[nf.n_compounds_distinct_replicates >= c["min_compounds"]]
    N["noise_floor"] = {r.endpoint: {"pct_naive": float(getattr(r, c["column"])), "n_compounds": int(r.n_compounds_distinct_replicates),
                                     "frac_multi_copies_only": float(r.frac_multi_that_are_copies_only)} for r in nf.itertuples()}


# ---------------- 4c. transformation products (W-TP) and physics conformer pre-test (W-PHYSICS) ----------------
@section("tp")
def _():
    c = json.load(open(P("tp"))); ev = json.load(open(RP(SRC["tp"]["eval"])))
    N["tp_control"] = c; N["tp_pooled_coverage"] = ev.get("pooled_headline_coverage_both_test")
    try: N["tp_delta_conformal"] = json.load(open(RP(SRC["tp"]["delta_conformal"])))
    except Exception as ex: N["errors"]["tp_delta_conformal"] = str(ex)
@section("physics_pretest")
def _():
    N["physics_pretest"] = {k: {kk: v.get(kk) for kk in ["n", "median_n_conf", "median_E_v1_minus_ensmin_eV", "frac_v1_above_min_by_gt_0.1eV"]} for k, v in json.load(open(P("physics_pretest"))).items() if isinstance(v, dict)}


@section("paired_ci_crit")
def _():
    for k in ["paired_ci", "paired_ci_v5"]:
        c = pd.read_csv(P(k)); N[k] = c.where(c.notna(), None).to_dict("records")


# ---------------- 5. toxicity ----------------
@section("tox_r3")
def _():
    from sklearn.metrics import average_precision_score, roc_auc_score
    c = SRC["tox_r3"]; R = json.load(open(P("tox_r3")))["endpoints"]; out = {}
    for ep, path in c["preds"].items():
        d = pd.read_parquet(RP(path)); meta = R.get(ep, {}); d["lf"] = d.nn_sim_train < 0.40
        def cls(x, thr):
            n, pos = len(x), int(x.y_true.sum())
            if n == 0: return {"n": 0}
            yp = (x.y_pred >= thr).astype(int); tp = int(((yp == 1) & (x.y_true == 1)).sum()); fp = int(((yp == 1) & (x.y_true == 0)).sum())
            fn = pos - tp; tn = n - pos - fp
            r = {"n": n, "n_positive": pos, "base_rate": pos / n}
            if pos >= 5 and pos < n:
                r.update(pr_auc=float(average_precision_score(x.y_true, x.y_pred)), roc_auc=float(roc_auc_score(x.y_true, x.y_pred)),
                         balanced_accuracy=0.5 * (tp / pos + tn / (n - pos)), precision=tp / (tp + fp) if tp + fp else None, recall=tp / pos)
            if "set_covers" in x: k = int(x.set_covers.sum()); r.update(set_coverage=k / n, set_coverage_ci=wilson(k, n))
            return r
        if meta.get("kind") == "classification":
            thr = meta.get("threshold", .5)
            out[ep] = {"kind": "classification", "threshold": thr, "nominal": float(d.nominal_level.iloc[0]), "full": cls(d, thr), "leak_free": cls(d[d.lf], thr),
                       "by_bin": {b: cls(d[d.bin == b], thr) for b in BL if "bin" in d}}
        else:
            d = d.rename(columns={"y_true": "y"}); d["naive"] = meta.get("naive_mu"); d["bin"] = pd.cut(d.nn_sim_train, [b[0] for b in BINS] + [1.01], labels=BL, right=False)
            out[ep] = {"kind": "regression", "units": str(d.units.iloc[0]) if "units" in d else "", "nominal": float(d.nominal_level.iloc[0]),
                       "full": score(d, "y_pred", "lo", "hi"), "leak_free": score(d[d.lf], "y_pred", "lo", "hi"), "by_bin": {b: score(d[d.bin == b], "y_pred", "lo", "hi") for b in BL}}
    N["tox_r3"] = out

@section("tox")
def _():
    N["tox_cls"] = json.load(open(P("tox_cls")))
    N["tox_ld50"] = [r for r in json.load(open(P("tox_results")))["results"] if "LD50" in r["endpoint"]]


# ---------------- 6. undefined vs gap + domain rules ----------------
@section("undefined")
def _():
    N["domain_rules"] = json.load(open(P("domain_rules")))
    p = pathlib.Path(P("undefined_vs_gap"))
    N["undefined_vs_gap"] = json.load(open(p)) if p.exists() else None
    c = pd.read_csv(P("undefined_cells")); c = c[c.scope == SRC["undefined_cells"]["scope"]]
    UCELLS.append(c)
    N["undefined_cells_status_counts"] = c[c.cls != "ALL"].cell_status.value_counts().to_dict()
    N["undefined_zero_label_cells"] = c[(c.n_labelled == 0) & (c.cls != "ALL")][["cls", "endpoint", "n_inventory", "n_A_undefined", "n_B_nonequivalent", "n_genuine_gap", "cell_status", "reason"]].to_dict("records")


SPACE_DF = []
# ---------------- 7. chemical space of the labelled set ----------------
@section("space")
def _():
    from rdkit import Chem
    from rdkit import RDLogger; RDLogger.DisableLog("rdApp.*")
    sk = lab.drop_duplicates("skeleton")[["skeleton", "smiles_canonical", "split", "nn_sim_train", "novel_class"]].copy()
    EL = ["F", "Cl", "Br", "I", "P", "S", "Si", "N", "O"]
    rows = []
    for s in sk.smiles_canonical:
        m = Chem.MolFromSmiles(s) if isinstance(s, str) else None
        syms = {a.GetSymbol() for a in m.GetAtoms()} if m else set()
        rows.append({e: (e in syms) for e in EL} | {"heavy": m.GetNumHeavyAtoms() if m else np.nan, "parsed": m is not None})
    sk = pd.concat([sk.reset_index(drop=True), pd.DataFrame(rows)], axis=1)
    N["space"] = {"n_skeletons": {k: int(v) for k, v in sk.split.value_counts().items()},
                  "element_frac_by_split": {sp: {e: float(g[e].mean()) for e in EL} for sp, g in sk.groupby("split")},
                  "nn_median_by_split": {sp: float(g.nn_sim_train.median()) for sp, g in sk.groupby("split") if sp != "train"},
                  "nn_bin_counts_test": {b: int(((sk.split == "test") & (pd.cut(sk.nn_sim_train, [x[0] for x in BINS] + [1.01], labels=BL, right=False) == b)).sum()) for b in BL},
                  "rows_by_endpoint_split": {f"{e}|{s}": int(n) for (e, s), n in lab.groupby(["endpoint", "split"]).size().items()},
                  "novel_class_skeletons": {k: int(v) for k, v in sk.novel_class.value_counts().items()},
                  "unparsed": int((~sk.parsed).sum())}
    SPACE_DF.append(sk)


# ---------------- 8. the swarm itself (ledger + board) ----------------
@section("swarm")
def _():
    L = pd.read_csv(P("ledger")); a = L[L.event != "reserve"] if "event" in L else L
    act = L[L.actual_usd.notna()]
    by = act.groupby("agent").actual_usd.agg(["sum", "count"]).sort_values("sum", ascending=False)
    B = json.load(open(P("board")))
    st = pd.Series([t["status"] for t in B["tasks"]]).value_counts().to_dict()
    ts = pd.to_datetime(L.ts)
    # per-agent spend, run total and cap are deliberately not exported (internal budget data)
    N["swarm"] = {"calls_by_agent": by["count"].to_dict(),
                  "first_ts": str(ts.min()), "last_ts": str(ts.max()), "elapsed_h": float((ts.max() - ts.min()).total_seconds() / 3600),
                  "board_status": st, "n_tasks": len(B["tasks"])}


# ======================================================================= figures
FIGS = {}
def fig_reg(key, file, src): FIGS[key] = {"file": f"figures/{file}", "source": src}

def draw_f1(subset, fname, key, title_tag):
    j = EJ[0]; j = j[j.subset == subset]
    eps = [e for e in j.endpoint.unique() if (j[(j.endpoint == e) & (j.cut == "i_all")].n >= MIN_N).any()]
    allc = j[j.cut == "i_all"].set_index("endpoint")
    eps = sorted(eps, key=lambda e: allc.loc[e, "rmse_pctnaive_model"])
    NF = N.get("noise_floor", {})
    panels = [("i_all", "rmse", "a  RMSE, all EPI-matched rows"),
              ("ii_not_doubtful", "rmse", "b  RMSE, physically doubtful labels removed (eChemPortal-only, sulfonates, unpaired charges)"),
              ("iv_not_doubtful_non_physprop", "rmse", "c  RMSE, doubtful removed AND outside PhysProp (data EPI Suite was not built on)"),
              ("ii_not_doubtful", "medae", "d  Median absolute error, doubtful labels removed")]
    fig, axs = plt.subplots(len(panels), 1, figsize=(10, 2.35 * len(panels)), sharex=True)
    x = np.arange(len(eps)); w = .36
    for ax, (cut, met, ttl) in zip(axs, panels):
        t = j[j.cut == cut].set_index("endpoint")
        for i, (who, col, hatch) in enumerate([("model", OI[1], ""), ("epi", OI[5], "//")]):
            vals = [t.loc[e, f"{met}_pctnaive_{who}"] if e in t.index and t.loc[e, "n"] >= MIN_N else np.nan for e in eps]
            ax.bar(x + (i - .5) * w, vals, w, color=col, hatch=hatch, edgecolor="k", lw=.3, label=["our model (structure only)", "EPI Suite"][i])
        for xi, e in enumerate(eps):
            if e not in t.index: continue
            r = t.loc[e]; lo, hi = r[f"d_{met}_ci95_lo"], r[f"d_{met}_ci95_hi"]
            top = np.nanmax([r[f"{met}_pctnaive_model"], r[f"{met}_pctnaive_epi"], 0])
            if r["n"] < MIN_N: ax.text(xi, 5, f"n={int(r['n'])}\n<20", ha="center", fontsize=5.5); continue
            lab_ = "ours better" if (hi is not None and hi < 0) else ("EPI better" if (lo is not None and lo > 0) else "n.s.")
            ax.text(xi, min(top, 140) + 3, f"{lab_}\nn={int(r['n'])}", ha="center", fontsize=5.3)
            if met == "rmse" and cut == "i_all" and e in NF: ax.plot([xi - w, xi + w], [NF[e]["pct_naive"]] * 2, color="k", lw=1.4, ls=(0, (1, 1)))
        ax.axhline(100, ls="--", c="grey", lw=.8); ax.set_ylim(0, 165)
        ax.set_ylabel(("RMSE" if met == "rmse" else "median abs. error") + "\n% of naive", fontsize=7.5)
        ax.set_title(ttl, loc="left", fontsize=8)
    axs[0].plot([], [], color="k", lw=1.4, ls=(0, (1, 1)), label="replicate-noise floor of the labels")
    axs[0].legend(fontsize=6.5, frameon=False, ncol=3, loc="upper left")
    axs[-1].set_xticks(x, eps, fontsize=7, rotation=20, ha="right")
    fig.suptitle(f"{title_tag}: test compounds; 'better' = paired 95% cluster-bootstrap CI of the difference excludes zero", fontsize=8.5, x=.01, ha="left")
    fig.tight_layout(); save(fig, fname); fig_reg(key, fname, P("epi_joint"))

@section("figS_joint_lf")
def _(): draw_f1("leak_free", "figS7_epi_joint_leakfree.png", "figS7", "LEAK-FREE")

@section("fig1")
def _():
    d = ES[0]; d = d[d.bin == "all"]
    views = [("cluster_leakfree", "leak-free official test (headline)", OI[0], "o"), ("graph_all", "graph-partitioned 5-fold CV, all labels", OI[2], "s"),
             ("cluster_full", "full official test (flattered)", "#999999", "D"), ("epi_leakfree", "EPI Suite, same leak-free rows", OI[5], "X")]
    piv = {v: d[d.view == v].set_index("endpoint") for v, *_ in views}
    eps = [e for e in piv["graph_all"].index]
    eps = sorted(eps, key=lambda e: piv["graph_all"].loc[e, "pct_naive"])
    fig = plt.figure(figsize=(11, 8.6)); gs = fig.add_gridspec(2, 2, height_ratios=[1.15, 1], width_ratios=[1, 1.25])
    ax = fig.add_subplot(gs[0, :]); x = np.arange(len(eps))
    for k, (v, lab_, c, m) in enumerate(views):
        t = piv[v]; xs = x + (k - 1.5) * .18
        ys = [t.loc[e, "pct_naive"] if e in t.index and t.loc[e, "n"] >= MIN_N else np.nan for e in eps]
        lo = [t.loc[e, "pct_naive_lo"] if e in t.index and t.loc[e, "n"] >= MIN_N else np.nan for e in eps]
        hi = [t.loc[e, "pct_naive_hi"] if e in t.index and t.loc[e, "n"] >= MIN_N else np.nan for e in eps]
        ax.errorbar(xs, ys, yerr=[np.array(ys) - np.array(lo), np.array(hi) - np.array(ys)], fmt=m, color=c, ms=5, lw=.9, capsize=1.5, label=lab_,
                    mfc="white" if v == "epi_leakfree" else c)
    ax.axhline(100, ls="--", c="grey", lw=.8); ax.text(len(eps) - .5, 102, "no skill", ha="right", fontsize=6.5, color="grey")
    ax.set_xticks(x, [f"{e}\nlf n={int(piv['cluster_leakfree'].loc[e, 'n'])}\nCV n={int(piv['graph_all'].loc[e, 'n'])}" for e in eps], fontsize=6)
    ax.set_ylabel("RMSE, % of naive guess (95% CI)"); ax.set_ylim(0, 150); ax.legend(fontsize=6.5, frameon=False, ncol=4, loc="upper left")
    ax.set_title("a  Structure-only model far from training: leak-free test, graph-partitioned CV, and the flattered full test", loc="left", fontsize=8.5)
    # b: six-rule verdict grid
    v = ER[1]; v = v[v.subset == "leak_free"].set_index("endpoint"); rules = [c for c in v.columns if c.startswith("R")]
    axb = fig.add_subplot(gs[1, 0]); code = {"model": 0, "tie": 1, "EPI": 2}
    from matplotlib.colors import ListedColormap
    M = np.array([[code.get(v.loc[e, r], 1) for r in rules] for e in v.index])
    axb.imshow(M, cmap=ListedColormap([OI[1], "#EEEEEE", OI[5]]), vmin=-.5, vmax=2.5, aspect="auto")
    for (i, j), val in np.ndenumerate(M): axb.text(j, i, ["ours", "tie", "EPI"][val], ha="center", va="center", fontsize=5.5, color="k" if val == 1 else "white" if val == 2 else "k")
    axb.set_xticks(range(len(rules)), [r.split("_", 1)[1].replace("_", " ") for r in rules], rotation=35, ha="right", fontsize=6)
    axb.set_yticks(range(len(v.index)), v.index, fontsize=6.5)
    axb.set_title("b  Ours vs EPI (RMSE, leak-free) under six label-exclusion rules", loc="left", fontsize=8.5)
    # c: model vs EPI, doubtful removed AND outside PhysProp (joint file), RMSE and MedAE
    j = EJ[0]; j = j[(j.subset == "leak_free") & (j.cut == "iv_not_doubtful_non_physprop") & (j.n >= MIN_N)].set_index("endpoint")
    axc = fig.add_subplot(gs[1, 1]); ee = [e for e in eps if e in j.index]; xx = np.arange(len(ee)); w = .2
    for k, (col, lab_, c, h) in enumerate([("rmse_pctnaive_model", "ours, RMSE", OI[1], ""), ("rmse_pctnaive_epi", "EPI, RMSE", OI[5], ""),
                                           ("medae_pctnaive_model", "ours, median abs. error", OI[1], "///"), ("medae_pctnaive_epi", "EPI, median abs. error", OI[5], "///")]):
        axc.bar(xx + (k - 1.5) * w, [j.loc[e, col] for e in ee], w, color=c if not h else "white", edgecolor=c, hatch=h, lw=1, label=lab_)
    axc.axhline(100, ls="--", c="grey", lw=.8); axc.set_xticks(xx, [f"{e}\nn={int(j.loc[e, 'n'])}" for e in ee], fontsize=6, rotation=20, ha="right")
    axc.set_ylabel("% of naive"); axc.legend(fontsize=5.8, frameon=False, ncol=2, loc="upper left"); axc.set_ylim(0, 150)
    axc.set_title("c  Fairest cut: doubtful labels removed, outside PhysProp", loc="left", fontsize=8.5)
    fig.tight_layout(); save(fig, "fig1_headline.png")
    fig_reg("fig1", "fig1_headline.png", f"{P('eval_splits')} + {SRC['epi_rules']['verdicts']} + {P('epi_joint')}")

@section("figS_epi_full")
def _(): draw_f1("full_test", "figS5_epi_full_test.png", "figS5", "FULL test set (flattered by near-duplicates of training compounds)")

@section("figS_fate_lf")
def _():
    F = N["fate"]; cfg = SRC["fate"]
    eps = sorted([e for e in F if F[e][cfg["shipped"]]["leak_free"]["pct_naive"] is not None], key=lambda e: F[e][cfg["shipped"]]["leak_free"]["pct_naive"])
    fig, ax = plt.subplots(figsize=(10, 3.4)); x = np.arange(len(eps)); w = .38
    for i, v in enumerate([cfg["reference"], cfg["shipped"]]):
        ax.bar(x + (i - .5) * w, [nz(F[e][v]["leak_free"]["pct_naive"]) for e in eps], w, color=OI[i], edgecolor="k", lw=.3, hatch=["", ".."][i], label=f"{v.replace('_', ' ')}, leak-free")
        ax.scatter(x + (i - .5) * w, [nz(F[e][v]["full"]["pct_naive"]) for e in eps], marker="_", s=110, color="k", zorder=3, label="full test set" if i else None)
    ax.axhline(100, ls="--", c="grey", lw=.8); ax.set_ylabel("RMSE, % of naive guess"); ax.legend(fontsize=6.5, frameon=False)
    ax.set_xticks(x, [f"{e}\nn={F[e][cfg['shipped']]['leak_free']['n']}" for e in eps], fontsize=6.5)
    fig.tight_layout(); save(fig, "figS6_fate_all_endpoints.png"); fig_reg("figS6", "figS6_fate_all_endpoints.png", SRC["fate"]["path"])

@section("fig2")
def _():
    A = N["ablation"]; cfg = SRC["ablation"]; ref = cfg["reference"]; eps = sorted(A, key=lambda e: -A[e]["n"])
    VN = SRC["fate"].get("variant_names", {}); vs = cfg["variants"]; others = [v for v in vs if v != ref]
    nc = 6; nr = int(np.ceil(len(eps) / nc))
    fig = plt.figure(figsize=(12, 2.3 * nr + 3.2)); gs = fig.add_gridspec(nr + 1, nc, height_ratios=[1] * nr + [1.35])
    for k, ep in enumerate(eps):
        ax = fig.add_subplot(gs[k // nc, k % nc])
        for i, v in enumerate(vs):
            ys = [nz(A[ep]["variants"][v]["by_bin"][b]["pct_naive"]) for b in BL]
            ax.plot(range(4), ys, marker=MK[i], color=OI[i], lw=1.2, ms=3.5, label=VN.get(v, v), ls=["-", "--", ":", "-."][i % 4])
        ax.set_xticks(range(4), [f"{b}\n{A[ep]['variants'][ref]['by_bin'][b]['n']}" for b in BL], fontsize=4.8)
        ax.set_title(ep, fontsize=7); ax.axhline(100, ls="--", c="grey", lw=.6); ax.tick_params(axis="y", labelsize=6)
        if k == 0: ax.legend(fontsize=5.5, frameon=False); ax.set_ylabel("% of naive", fontsize=6.5)
    axf = fig.add_subplot(gs[nr, :]); x = np.arange(len(eps))
    for i, v in enumerate(others):
        for k, s_ in enumerate(["full", "leak_free"]):
            rr = [A[e]["paired_vs_ref"][v][s_] for e in eps]
            xs = x + (k - .5) * .3 + i * .08
            ys = [r["diff_pp"] if r else np.nan for r in rr]
            lo = [r["diff_pp"] - r["ci_lo"] if r else 0 for r in rr]; hi = [r["ci_hi"] - r["diff_pp"] if r else 0 for r in rr]
            axf.errorbar(xs, ys, yerr=[lo, hi], fmt=["o", "^"][k], color=OI[vs.index(v)], mfc="white" if k else OI[vs.index(v)], ms=4, lw=.9, capsize=1.5,
                         label=f"{VN.get(v, v)} minus {VN.get(ref, ref)}: {'full test' if k == 0 else 'leak-free'}")
    axf.axhline(0, c="k", lw=.7); axf.set_xticks(x, eps, fontsize=6.5, rotation=15)
    axf.set_ylabel("difference, pp of naive RMSE\n(95% cluster-bootstrap CI)\nbelow 0 = added block helps", fontsize=6.5); axf.legend(fontsize=6, frameon=False, ncol=2)
    fig.text(.5, 1 - 1 / (nr + 2.3) * nr - .01, "x axis of the small panels: nn_sim_train bin, with n test rows", ha="center", fontsize=6.5)
    fig.tight_layout(); save(fig, "fig2_familiarity_ablation.png")
    fig_reg("fig2", "fig2_familiarity_ablation.png", SRC["ablation"]["path"])

@section("fig4")
def _():
    F = N["fate"]; v = SRC["fate"]["shipped"]; eps = [e for e in F if F[e][v]["full"]["n"] >= 100]
    nominal = N.get("fate_nominal", {}); M = list(SRC["fate"].get("interval_methods", {}))
    fig, ax = plt.subplots(1, 3, figsize=(12, 3.9), gridspec_kw={"width_ratios": [1.4, 1, 1]})
    for j_, b in enumerate(BL):
        xs = np.arange(len(eps)) + (j_ - 1.5) * .18
        cov = [nz(F[e][v]["by_bin"][b].get("coverage")) for e in eps]
        ci = [F[e][v]["by_bin"][b].get("coverage_ci", (None, None)) for e in eps]
        err = np.array([[c - nz(l) if l is not None else 0 for c, (l, h) in zip(cov, ci)], [nz(h) - c if h is not None else 0 for c, (l, h) in zip(cov, ci)]])
        ax[0].errorbar(xs, cov, yerr=np.nan_to_num(err), fmt=MK[j_], color=OI[j_], ms=4, lw=.8, capsize=1.5, label=f"nn_sim {b}")
    for i_, e in enumerate(eps):
        if nominal.get(e): ax[0].plot([i_ - .45, i_ + .45], [nominal[e]] * 2, "k-", lw=1.2)
    ax[0].set_xticks(range(len(eps)), eps, rotation=45, ha="right", fontsize=6.5)
    ax[0].set_ylabel("empirical coverage (95% Wilson CI)"); ax[0].set_ylim(.55, 1.02); ax[0].legend(fontsize=6, frameon=False, ncol=2, loc="lower left")
    ax[0].set_title("a  Shipped intervals: coverage per familiarity bin\n(black bar = nominal)", loc="left", fontsize=8)
    if M:
        for k, m in enumerate(M):
            cv = [nz(F[e][v]["interval_methods"][m]["leak_free"].get("coverage")) for e in eps]
            wd = [nz(F[e][v]["interval_methods"][m]["leak_free"].get("median_width")) / max(F[e][v]["full"]["rmse_naive"], 1e-9) for e in eps]
            ax[1].scatter(np.arange(len(eps)) + (k - 1) * .22, cv, marker=MK[k], color=OI[k + 4 if k else 1], s=18, label=m)
            ax[2].scatter(np.arange(len(eps)) + (k - 1) * .22, wd, marker=MK[k], color=OI[k + 4 if k else 1], s=18, label=m)
        ax[1].axhline(nominal.get(eps[0], .9), c="k", lw=1); ax[1].set_ylim(.55, 1.02); ax[1].legend(fontsize=6, frameon=False, loc="lower left")
        ax[1].set_title("b  Coverage on leak-free compounds,\nby calibration method", loc="left", fontsize=8); ax[1].set_ylabel("empirical coverage")
        ax[2].set_title("c  Median interval width on leak-free\ncompounds / naive RMSE", loc="left", fontsize=8); ax[2].set_ylabel("width / naive RMSE")
        for a in ax[1:]: a.set_xticks(range(len(eps)), eps, rotation=45, ha="right", fontsize=6.5)
    fig.tight_layout(); save(fig, "fig4_coverage.png")
    fig_reg("fig4", "fig4_coverage.png", SRC["fate"]["path"])

def draw_modes(blk, fname, key):
    S_ = N["spectra_only"][blk]; cfg = SRC["spectra_only"]; lv = cfg["ei_levels"] if blk == "ei" and "ei_levels" in cfg else cfg["levels"]
    MR = N.get("spectra_mass_regularised", {})
    eps = [e for e in S_ if S_[e]["levels"][lv[0][0]]["full"]["pct_naive"] is not None]
    eps = sorted(eps, key=lambda e: S_[e]["levels"][lv[-1][0]]["full"]["pct_naive"] or 999)
    fig, ax = plt.subplots(2, 1, figsize=(11, 6.2), sharex=True)
    x = np.arange(len(eps)); w = .8 / len(lv)
    hatches = ["", "..", "", "//", ""]; colors = [OI[4], "#BBBBBB", OI[0], OI[2], OI[1]]
    for k, sub in enumerate(["leak_free", "full"]):
        for i, (c, l, *_r) in enumerate(lv):
            ax[k].bar(x + (i - (len(lv) - 1) / 2) * w, [nz(S_[e]["levels"][c][sub]["pct_naive"]) for e in eps], w, color=colors[i % 5], hatch=hatches[i % 5], label=l, edgecolor="k", lw=.3)
        if sub == "full" and MR:
            ys = [MR.get(f"{blk}/{e}", {}).get("S2_mass_ion_lgbm_regularised", np.nan) for e in eps]
            ax[k].scatter(x - (len(lv) - 1) / 2 * w, ys, marker="v", color="k", s=18, zorder=4, label="m/z + adduct, regularised refit")
        ax[k].axhline(100, ls="--", c="grey", lw=.8); ax[k].set_ylim(0, 135); ax[k].set_ylabel("RMSE, % of naive\n(subset's own train mean)", fontsize=7.5)
        ax[k].set_title(("a  Leak-free compounds (headline; bars missing where n<20)" if sub == "leak_free" else "b  All test compounds with this spectrum type (flattered)"), loc="left", fontsize=8.5)
        for xi, e in enumerate(eps): ax[k].text(xi, 128, f"n={S_[e]['levels'][lv[0][0]][sub]['n']}", ha="center", fontsize=5.5)
    ax[0].legend(fontsize=6.3, frameon=False, ncol=3, loc="upper left", bbox_to_anchor=(0, 1.0)); ax[1].legend(fontsize=6.3, frameon=False, ncol=3, loc="lower left")
    ax[1].set_xticks(x, eps, fontsize=7, rotation=15)
    fig.tight_layout(); save(fig, fname); fig_reg(key, fname, SRC["spectra_only"]["path"] + (f" + {SRC['spectra_only']['mass_regularised']}" if MR else ""))

@section("fig3")
def _(): draw_modes("pos", "fig3_input_modes.png", "fig3")
@section("figS_modes_neg")
def _(): draw_modes("neg", "figS13_input_modes_esineg.png", "figS13")
@section("figS_modes_ei")
def _(): draw_modes("ei", "figS14_input_modes_ei.png", "figS14")

@section("fig5")
def _():
    U = N.get("undefined_vs_gap"); sk = SPACE_DF[0]; S = N["space"]
    fig = plt.figure(figsize=(11, 10.5)); gs = fig.add_gridspec(2, 2, height_ratios=[2.6, 1])
    axU = fig.add_subplot(gs[0, :]); axA = fig.add_subplot(gs[1, 0]); axB = fig.add_subplot(gs[1, 1])
    if UCELLS:
        from matplotlib.colors import ListedColormap
        c = UCELLS[0]; c = c[c.cls != "ALL"]
        EPO = ["logkow", "water_solubility", "melting_point", "boiling_point", "vapor_pressure", "henry", "logkoa", "koh_gas", "koc", "bcf", "pka_acidic", "pka_basic"]
        EPO = [e for e in EPO if e in set(c.endpoint)]
        classes = list(dict.fromkeys(c.cls))
        ST = {"covered": 0, "C_genuine_gap": 1, "A_undefined": 2, "B_nonequivalent": 3, "mixed": 4}
        cols = ["#F2F2F2", OI[1], OI[3], OI[4], OI[6]]
        M = np.full((len(classes), len(EPO)), np.nan); TX = [[""] * len(EPO) for _ in classes]
        for r in c.itertuples():
            if r.endpoint not in EPO: continue
            a, b = classes.index(r.cls), EPO.index(r.endpoint); M[a, b] = ST.get(r.cell_status, 4)
            TX[a][b] = f"{100 * r.frac_labelled_of_C:.0f}" if r.cell_status == "covered" and r.frac_labelled_of_C == r.frac_labelled_of_C else {"A_undefined": "U", "C_genuine_gap": "G", "B_nonequivalent": "N", "mixed": "M"}.get(r.cell_status, "")
        axU.imshow(M, cmap=ListedColormap(cols), vmin=-.5, vmax=4.5, aspect="auto")
        for (a, b), _v in np.ndenumerate(M): axU.text(b, a, TX[a][b], ha="center", va="center", fontsize=4.6, color="k")
        axU.set_xticks(range(len(EPO)), EPO, rotation=30, ha="right", fontsize=6.5); axU.set_yticks(range(len(classes)), [x[:38] for x in classes], fontsize=5.2)
        from matplotlib.patches import Patch
        axU.legend(handles=[Patch(color=cols[0], label="labelled (number = % of defined compounds labelled)"), Patch(color=cols[1], label="G: no labels, genuine data gap"),
                            Patch(color=cols[2], label="U: no labels, physically undefined"), Patch(color=cols[3], label="N: no labels, measurement not equivalent"), Patch(color=cols[4], label="M: no labels, mixed")],
                   fontsize=5.5, frameon=False, loc="upper left", bbox_to_anchor=(1.0, 1.0))
        axU.set_title("a  Compound class x endpoint over the visible inventory: what an empty cell means", loc="left", fontsize=8.5)
    else:
        axU.axis("off"); axU.text(.5, .5, "panel a pending: W-SPACE undefined-vs-gap table not yet written", ha="center", fontsize=9, color="grey")
    for i, sp in enumerate(["calib", "test"]):
        axA.hist(sk[sk.split == sp].nn_sim_train.dropna(), bins=np.linspace(0, 1, 41), histtype="step", lw=1.5, color=OI[i],
                 label=f"{sp} (median {S['nn_median_by_split'].get(sp, float('nan')):.2f})", density=True, ls=["-", "--"][i])
    for b in [.3, .5, .7]: axA.axvline(b, c="grey", ls=":", lw=.8)
    axA.axvline(.4, c="k", ls="--", lw=.8); axA.text(.41, axA.get_ylim()[1] * .92, "leak-free below 0.40", fontsize=6.5)
    axA.set_xlabel("nn_sim_train (Tanimoto to nearest training compound)"); axA.set_ylabel("density"); axA.legend(fontsize=7, frameon=False)
    axA.set_title("b  How far held-out compounds sit from training", loc="left", fontsize=8.5)
    EL = ["F", "Cl", "Br", "I", "P", "S", "Si"]; x = np.arange(len(EL))
    for i, sp in enumerate(["train", "calib", "test"]):
        axB.bar(x + (i - 1) * .27, [100 * S["element_frac_by_split"][sp][e] for e in EL], .27, color=OI[i], label=sp, edgecolor="k", lw=.3, hatch=["", "..", "//"][i])
    axB.set_xticks(x, EL); axB.set_ylabel("% of skeletons containing element"); axB.legend(fontsize=7, frameon=False)
    axB.set_title("c  Heteroatom coverage of the labelled set by split", loc="left", fontsize=8.5)
    fig.tight_layout(); save(fig, "figS8_space_and_cells.png")
    fig_reg("figS8", "figS8_space_and_cells.png", f"{P('undefined_cells')} + {P('labels')}")
    import shutil
    shutil.copy(P("wspace_fig5"), OUT / "fig5_undefined_vs_gap.png")
    fig_reg("fig5", "fig5_undefined_vs_gap.png", f"{P('wspace_fig5')} (drawn by W-SPACE/fig_undefined_vs_gap.py from {P('undefined_cells')} + {P('undefined_vs_gap')})")
    shutil.copy(P("wspace_figsplit"), OUT / "figS9_split_comparison.png")
    fig_reg("figS9", "figS9_split_comparison.png", f"{P('wspace_figsplit')} (drawn by W-SPACE/fig_split_comparison.py from {P('eval_splits')})")

@section("fig6")
def _():
    T = N["tox_r3"]; C = [e for e in T if T[e]["kind"] == "classification"]; Rg = [e for e in T if T[e]["kind"] == "regression"]
    fig, ax = plt.subplots(1, 3, figsize=(12, 3.8), gridspec_kw={"width_ratios": [1, 1, 1.3]})
    x = np.arange(len(C))
    for k, sub in enumerate(["full", "leak_free"]):
        ax[0].bar(x + (k - .5) * .38, [nz(T[e][sub].get("pr_auc")) for e in C], .38, color=[OI[0], OI[5]][k], hatch=["", "//"][k], edgecolor="k", lw=.3, label=["all test", "leak-free (nn_sim < 0.40)"][k])
        for xi, e in enumerate(C): ax[0].plot([xi + (k - 1) * .38, xi + k * .38], [T[e][sub]["base_rate"]] * 2, "k--", lw=1)
        ax[1].bar(x + (k - .5) * .38, [nz(T[e][sub].get("balanced_accuracy")) for e in C], .38, color=[OI[0], OI[5]][k], hatch=["", "//"][k], edgecolor="k", lw=.3)
    ax[0].plot([], [], "k--", label="base rate = no-skill PR-AUC"); ax[0].legend(fontsize=6, frameon=False, loc="upper left"); ax[0].set_ylim(0, 1)
    ax[0].set_xticks(x, [f"{e}\nbase rate {T[e]['full']['base_rate']:.2f}\nn={T[e]['full']['n']} (lf {T[e]['leak_free']['n']})" for e in C], fontsize=6.5)
    ax[0].set_ylabel("PR-AUC"); ax[0].set_title("a  Precision-recall AUC vs base rate", loc="left", fontsize=8.5)
    ax[1].axhline(.5, c="k", ls="--", lw=.9); ax[1].set_ylim(0, 1); ax[1].set_xticks(x, C, fontsize=7); ax[1].set_ylabel("balanced accuracy (0.5 = no skill)")
    ax[1].set_title("b  Balanced accuracy at the frozen threshold", loc="left", fontsize=8.5)
    xr = np.arange(len(Rg))
    for k, sub in enumerate(["full", "leak_free"]):
        ax[2].bar(xr + (k - .5) * .38, [nz(T[e][sub].get("pct_naive")) for e in Rg], .38, color=[OI[0], OI[5]][k], hatch=["", "//"][k], edgecolor="k", lw=.3)
        for xi, e in enumerate(Rg):
            cv = T[e][sub].get("coverage")
            if cv is not None: ax[2].text(xi + (k - .5) * .38, nz(T[e][sub].get("pct_naive")) + 2, f"cov\n{cv:.2f}", ha="center", fontsize=5.3)
    ax[2].axhline(100, c="grey", ls="--", lw=.8); ax[2].set_ylim(0, 120); ax[2].set_ylabel("RMSE, % of naive")
    ax[2].set_xticks(xr, [f"{e}\n({T[e]['units']})\nn={T[e]['full']['n']} (lf {T[e]['leak_free']['n']})" for e in Rg], fontsize=6)
    ax[2].set_title(f"c  Potency and LD50: error and interval coverage (nominal {T[Rg[0]]['nominal']:.2f})", loc="left", fontsize=8.5)
    fig.tight_layout(); save(fig, "fig6_toxicity.png"); fig_reg("fig6", "fig6_toxicity.png", f"{SRC['tox_r3']['path']} + per-row preds_*.parquet")

@section("figS_parity")
def _():
    d = FATE["df"]; v = SRC["fate"]["shipped"]; eps = sorted(d.endpoint.unique())
    nc = 4; nr = int(np.ceil(len(eps) / nc)); fig, axs = plt.subplots(nr, nc, figsize=(10, 2.5 * nr))
    for ax, ep in zip(axs.flat, eps):
        de = d[d.endpoint == ep]
        ax.scatter(de[~de.lf].y, de[~de.lf][v], s=3, alpha=.35, color=OI[0], label="has close training analogue", rasterized=True)
        ax.scatter(de[de.lf].y, de[de.lf][v], s=5, alpha=.7, color=OI[5], marker="^", label="leak-free", rasterized=True)
        lo, hi = np.nanmin([de.y.min(), de[v].min()]), np.nanmax([de.y.max(), de[v].max()]); ax.plot([lo, hi], [lo, hi], "k-", lw=.6)
        ax.set_title(f"{ep} ({UNITS.get(ep, '')})", fontsize=7); ax.tick_params(labelsize=6)
    for ax in list(axs.flat)[len(eps):]: ax.axis("off")
    axs.flat[0].legend(fontsize=5.5, frameon=False); fig.supxlabel("measured", fontsize=8); fig.supylabel("predicted", fontsize=8)
    fig.tight_layout(); save(fig, "figS1_parity.png"); fig_reg("figS1", "figS1_parity.png", SRC["fate"]["path"])

@section("figS_paired")
def _():
    A = N["ablation_run2"]; rows = []
    for ep, a in A.items():
        for v, pr in a["paired_vs_ref"].items():
            for s, r in pr.items():
                if r: rows.append((f"{ep}: {v.replace('_', ' ')}", s, r))
    labels = sorted({r[0] for r in rows}); yy = {l: i for i, l in enumerate(labels)}
    fig, ax = plt.subplots(figsize=(7, .22 * len(labels) + 1))
    for l, s, r in rows:
        off = -.15 if s == "full" else .15; c = OI[0] if s == "full" else OI[5]
        ax.errorbar(r["diff_pp"], yy[l] + off, xerr=[[r["diff_pp"] - r["ci_lo"]], [r["ci_hi"] - r["diff_pp"]]], fmt="o" if s == "full" else "^", color=c, ms=3, lw=.8)
    ax.axvline(0, c="k", lw=.7); ax.set_yticks(range(len(labels)), labels, fontsize=6)
    ax.errorbar([], [], fmt="o", color=OI[0], label="full test set"); ax.errorbar([], [], fmt="^", color=OI[5], label="leak-free")
    ax.legend(fontsize=6.5, frameon=False); ax.set_xlabel("variant minus struct_only, percentage points of naive RMSE (95% cluster-bootstrap CI); left = better")
    fig.tight_layout(); save(fig, "figS2_paired_ablation.png"); fig_reg("figS2", "figS2_paired_ablation.png", SRC["ablation_run2"]["path"])

# figS_swarm (per-agent spend chart, formerly figS4_swarm_spend.png) removed: internal budget data.

@section("figS_tp")
def _():
    c = N["tp_control"]; eps = [e for e in c if isinstance(c[e], dict) and "rule_pairs" in c[e]]
    fig, ax = plt.subplots(figsize=(8, 3.2)); x = np.arange(len(eps))
    ax.bar(x - .18, [c[e]["rule_pairs"]["delta_pct_naive"] for e in eps], .36, color=OI[0], edgecolor="k", lw=.3, label="rule-generated parent -> product pairs")
    med = [c[e]["control_20_draws"]["delta_pct_naive"]["median"] for e in eps]; lo = [c[e]["control_20_draws"]["delta_pct_naive"]["min"] for e in eps]; hi = [c[e]["control_20_draws"]["delta_pct_naive"]["max"] for e in eps]
    ax.bar(x + .18, med, .36, color=OI[1], hatch="//", edgecolor="k", lw=.3, label="control: random pairs matched on similarity and size (median of 20 draws)")
    ax.errorbar(x + .18, med, yerr=[np.array(med) - lo, np.array(hi) - med], fmt="none", ecolor="k", lw=.8, capsize=2)
    ax.axhline(100, ls="--", c="grey", lw=.8); ax.set_ylabel("error of predicted change,\n% of naive (no-change) guess")
    ax.set_xticks(x, [f"{e}\nn={c[e]['rule_pairs']['n']}" for e in eps], fontsize=7); ax.legend(fontsize=6.5, frameon=False, loc="upper left"); ax.set_ylim(0, 130)
    fig.tight_layout(); save(fig, "figS15_tp_control.png"); fig_reg("figS15", "figS15_tp_control.png", P("tp"))

@section("r2_figs")
def _():
    import shutil
    c = SRC["r2_figs"]
    for k, (png, csv, cap) in c["files"].items():
        src_ = pathlib.Path(RP(c["path"])) / png
        if src_.exists():
            shutil.copy(src_, OUT / png); fig_reg(k, png, f"{src_} (drawn by READER-2 from {pathlib.Path(RP(c['path'])) / csv})"); FIGS[k]["caption"] = cap

N["figures"] = FIGS
json.dump(N, open(H / "scribe_numbers_v4.tmp", "w"), indent=1, default=lambda o: None if o is None else (float(o) if isinstance(o, (np.floating, np.integer)) else str(o)))
os.replace(H / "scribe_numbers_v4.tmp", H / "scribe_numbers.json"); print("figures:", list(FIGS)); print("errors:", N["errors"])
