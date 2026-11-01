#!/usr/bin/env python
"""Addendum loader for whitepaper v5.

Reads result files that landed after make_figures.py was written, and writes
scribe_addendum.json.  Nothing here is typed by hand: every value is read out
of the file named in SRC.  build_whitepaper.py reads the json and renders it.
"""
import json, csv, re, pathlib, statistics, datetime

W = pathlib.Path("(internal path removed)")
OUT = pathlib.Path("SCRIBE/scribe_addendum.json")

SRC = {
    "tox_chembl":          "CRITIC/audit_wtox_chembl.csv",
    "tox_chembl_control":  "CRITIC/audit_wtox_chembl_control.csv",
    "normmondrian":        "CRITIC/audit_normmondrian_width.json",
    "spec_audit":          "CRITIC/audit_spectra_v31.csv",
    "spec_domain":         "CRITIC/audit_spectra_v31_domain.csv",
    "ld50_spectrum_only":  "W-TOX/r3/spectrum_only_ld50.json",
    "ld50_spectrum_fig":   "W-TOX/fig_wtox_6_spectrum_only_ld50.csv",
    "tox_hazard":          "W-TOX/r3/results_hazard.json",
    "nmr":                 "W-TP/nmr_summary.csv",
    "recall_control":      "W-SPACE/recall_control_summary.md",
    "p009":                "W-SPACE/p009_physics_graphcv_summary.md",
    "epi_graphcv":         "W-SPACE/epi_graphcv_paired.csv",
    "epi_graphcv_cov":     "W-SPACE/epi_graphcv_coverage.csv",
    "vod_A":               "READER-2/vod_summary_A.csv",
    "vod_B":               "READER-2/vod_summary_B.csv",
    "vs_epi":              "W-MODEL/v5_main/vs_epi.csv",
    "spec_leakfree":       "W-SPECTRA/v31/report/leak_free_v31.csv",
    "p004":                "W-TOX/r3/p004_round2_literature.json",
    "p001":                "W-PHYSICS/results/p001_contrasts.csv",
    "ridge":               "W-MODEL/v5_main/learner_control_ridge.csv",
    "tox_inventory":       "W-TOX/r3/inventory_hazard_domain.json",
    "market":              "PRINCIPAL/market_decisions_run3.csv",
    "inv_cov":             "W-SPACE/inventory_coverage.csv",
    "q003_cells":          "CRITIC/undefined_vs_gap_cells_q003.csv",
    "phys_inv_cov":        "W-PHYSICS/physics_inventory_v1_coverage.json",
    "inv_cov_sum":         "W-SPACE/inventory_coverage_summary.json",
    "inv_pred":            "W-MODEL/inventory_predictions_v5_summary.json",
    "sigma_terciles":      "W-MODEL/v5_main/sigma_terciles.csv",
    "audit_v5":            "CRITIC/audit_wmodel_v5.csv",
    "audit_v5_nodedup":    "CRITIC/audit_wmodel_v5_nodedup.csv",
}

def path(k):
    return W / SRC[k]

def rows(k):
    p = path(k)
    if not p.exists():
        return []
    with open(p, newline="") as fh:
        return list(csv.DictReader(fh))

def jload(k):
    p = path(k)
    return json.load(open(p)) if p.exists() else {}

def num(x):
    try:
        return float(x)
    except Exception:
        return None

def md_table(k):
    """Parse the first pipe table out of a markdown file into list[dict]."""
    p = path(k)
    if not p.exists():
        return []
    lines = [l.strip() for l in p.read_text().splitlines()]
    tbl = [l for l in lines if l.startswith("|")]
    if len(tbl) < 3:
        return []
    hdr = [c.strip() for c in tbl[0].strip("|").split("|")]
    out = []
    for l in tbl[2:]:
        cells = [c.strip() for c in l.strip("|").split("|")]
        if len(cells) != len(hdr):
            continue
        out.append(dict(zip(hdr, cells)))
    return out

def ci_pair(s):
    """'-0.58 [-5.64, +4.66]' -> (point, lo, hi)."""
    m = re.match(r"\s*([+-]?[\d.]+)\s*\[\s*([+-]?[\d.]+)\s*,\s*([+-]?[\d.]+)\s*\]", s or "")
    if not m:
        return (None, None, None)
    return tuple(float(g) for g in m.groups())

AD = {"built": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
      "sources": {k: str(path(k)) for k in SRC},
      "missing": [k for k in SRC if not path(k).exists()]}

# ---------- 1. toxicity: measured ChEMBL audit + familiarity-only control ----------
AD["tox_chembl"] = [
    {"endpoint": r["endpoint"], "task": r["task"], "subset": r["subset"],
     "n": num(r["n"]), "base_rate": num(r["base_rate"]), "pr_auc": num(r["pr_auc"]),
     "pr_auc_minus_base": num(r["pr_auc_minus_base"]), "balanced_acc": num(r["balanced_acc"]),
     "recall": num(r["recall"]), "precision": num(r["precision"]),
     "nominal": num(r["nominal_level"]), "empirical_coverage": num(r["empirical_coverage"]),
     "mean_set_size": num(r["mean_set_size"]),
     "pct_of_naive": num(r["pct_of_naive"]), "pct_ci": r["pct_ci"], "rmse": num(r["rmse"]),
     "naive_train_mean": num(r["naive_train_mean"])}
    for r in rows("tox_chembl")]
AD["tox_chembl_control"] = [
    {"endpoint": r["endpoint"], "n": num(r["n"]), "base_rate": num(r["base_rate"]),
     "pr_auc_model": num(r["pr_auc_model"]),
     "pr_auc_nnsim_only": num(r["pr_auc_nnsim_only"]),
     "pr_auc_nnsim_continuous": num(r["pr_auc_nnsim_continuous"])}
    for r in rows("tox_chembl_control")]

# ---------- 2. normalised-Mondrian interval audit ----------
NM = jload("normmondrian")
AD["normmondrian"] = {
    "width_ratio_vs_global": NM.get("mean_width_ratio_normmondrian_vs_global_all_rows"),
    "width_ratio_range": NM.get("range"),
    "width_ratio_mondrian_vs_global": NM.get("mean_width_ratio_mondrian_vs_global"),
    "under_covered_class_cells": NM.get("under_covered_class_cells"),
    "familiar_bin": NM.get("familiar_bin_coverage_normmondrian"),
}
fb = NM.get("familiar_bin_coverage_normmondrian") or []
AD["normmondrian"]["familiar_bin_worst"] = sorted(
    [r for r in fb if r.get("cov_normmondrian") is not None],
    key=lambda r: r["cov_normmondrian"])[:3]

# ---------- 3. spectrum-only: single-spectrum coverage + domain signal ----------
AD["spec_single_coverage"] = [
    {"endpoint": r["endpoint"], "n": num(r["n"]), "cov_single": num(r["cov_SINGLE"]),
     "single_pct": num(r["SINGLE_spectrum"]), "struct_pct": num(r["STRUCT"]),
     "mass_ion_pct": num(r["S2_mass_ion"]), "full_pct": num(r["FULL"])}
    for r in rows("spec_audit") if r.get("subset") == "all" and num(r.get("cov_SINGLE"))]
AD["spec_domain"] = [
    {"endpoint": r["endpoint"], "n": num(r["n"]),
     "rho_err_vs_maxcos": num(r["rho_abs_err_vs_maxcos"]),
     "rho_err_vs_prec_dist": num(r["rho_abs_err_vs_prec_dist"]),
     "rho_err_vs_nn_sim": num(r["rho_abs_err_vs_nn_sim"])}
    for r in rows("spec_domain")]
if AD["spec_single_coverage"]:
    cv = [r["cov_single"] for r in AD["spec_single_coverage"]]
    AD["spec_single_coverage_range"] = [min(cv), max(cv)]
if AD["spec_domain"]:
    rr = [abs(r["rho_err_vs_maxcos"]) for r in AD["spec_domain"] if r["rho_err_vs_maxcos"] is not None]
    AD["spec_domain_max_abs_rho"] = max(rr) if rr else None
    AD["spec_domain_median_abs_rho"] = statistics.median(rr) if rr else None

# ---------- 4. spectrum-only acute toxicity (W-TOX) ----------
LD = jload("ld50_spectrum_only")
AD["ld50_spectrum_only"] = {
    "n_test": LD.get("n_test"), "n_train": LD.get("n_train"), "n_calib": LD.get("n_calib"),
    "units": LD.get("units"), "subset": LD.get("subset"),
    "naive_rmse": LD.get("naive_rmse_this_subset"),
    "nominal": (list(LD.get("arms", {}).values()) or [{}])[0].get("nominal_coverage"),
    "arms": {k: {"pct_of_naive": v.get("pct_of_naive"), "rmse": v.get("rmse"),
                 "empirical_coverage": v.get("empirical_coverage"),
                 "width": v.get("interval_width")}
             for k, v in LD.get("arms", {}).items()},
    "paired": LD.get("paired") or LD.get("contrasts") or {},
}
AD["ld50_spectrum_only_fig_rows"] = rows("ld50_spectrum_fig")

# ---------- 5. NMR input mode (W-TP) ----------
AD["nmr"] = [
    {"endpoint": r["endpoint"], "block": r["block"], "arm": r["arm"],
     "n_test": num(r["n_test"]), "pct_naive": num(r["pct_naive"]),
     "ci": [num(r["ci_lo"]), num(r["ci_hi"])], "skill": r["skill"] == "True",
     "cov_nominal": num(r["cov_nominal"]), "cov_empirical": num(r["cov_empirical"]),
     "n_leak_free": num(r["n_leak_free"]), "pct_naive_leak_free": num(r["pct_naive_leak_free"])}
    for r in rows("nmr")]

# ---------- 6. near-neighbour recall control (W-SPACE; replaces the withdrawn ratio) ----------
RC = md_table("recall_control")
rc = []
for r in RC:
    eff = ci_pair(r.get("recall effect", ""))
    size = ci_pair(r.get("size effect", ""))
    rc.append({"endpoint": r.get("endpoint"), "rows": r.get("rows"), "n": num(r.get("n")),
               "full": num(r.get("FULL")), "prune": num(r.get("PRUNE")), "rand": num(r.get("RAND")),
               "recall_effect": eff[0], "recall_ci": [eff[1], eff[2]],
               "size_effect": size[0], "size_ci": [size[1], size[2]]})
AD["recall_control"] = rc
alltest = [r for r in rc if r["rows"] == "all_test" and r["recall_effect"] is not None]
AD["recall_control_summary"] = {
    "n_endpoints": len(alltest),
    "median_recall_effect_pp": statistics.median([r["recall_effect"] for r in alltest]) if alltest else None,
    "n_ci_excludes_0": sum(1 for r in alltest if r["recall_ci"][0] is not None and
                           (r["recall_ci"][0] > 0 or r["recall_ci"][1] < 0)),
}
neg = [r for r in rc if r["rows"] == "leakfree_test" and r["recall_ci"][0] is not None]
AD["recall_control_summary"]["negative_control_n"] = len(neg)
AD["recall_control_summary"]["negative_control_pass"] = sum(
    1 for r in neg if r["recall_ci"][0] <= 0 <= r["recall_ci"][1])

# ---------- 7. P-009 physics under graph CV ----------
P9 = md_table("p009")
AD["p009"] = [{"endpoint": r.get("endpoint"), "bin": r.get("bin"), "n": num(r.get("n")),
               "S": num(r.get("S")), "SP": num(r.get("SP")), "SPperm": num(r.get("SPperm")),
               "SP_minus_S": r.get("SP-S"), "SP_minus_SPperm": r.get("SP-SPperm")}
              for r in P9 if r.get("bin") in ("all", "ALL", None, "")]

# ---------- 8. model vs EPI under graph CV (PRINCIPAL / W-SPACE) ----------
AD["epi_graphcv"] = [
    {"endpoint": r["endpoint"], "rows": r["rows"], "n": num(r["n"]),
     "model_pct_naive": num(r["model_pct_naive"]), "epi_pct_naive": num(r["epi_pct_naive"]),
     "diff": num(r["diff_model_minus_epi"]),
     "diff_ci": [num(r["diff_lo"]), num(r["diff_hi"])]}
    for r in rows("epi_graphcv") if r["rows"] == "all_graphcv_rows_with_epi"]
AD["epi_graphcv_cov"] = rows("epi_graphcv_cov")

# ---------- 9. value of data (READER-2, regenerated) ----------
AD["vod_A"] = [{"endpoint": r["endpoint"], "eval_set": r["eval_set"], "n": num(r["n_eval"]),
                "pct_at_1_8": num(r["pct_at_1_8"]), "pct_full": num(r["pct_full"]),
                "pct_change_per_doubling": num(r["pct_change_per_doubling"])}
               for r in rows("vod_A")]
vb = []
for r in rows("vod_B"):
    vb.append({"endpoint": r["endpoint"], "cls": r["cls"], "n_test": num(r["n_test"]),
               "pct_full": num(r["pct_full"]), "pct_lco": num(r["pct_lco"]),
               "penalty_pp": num(r["novelty_penalty_pp"]), "penalty_ci": r["novelty_penalty_ci95"],
               "ctrl_penalty_pp": num(r["ctrl_penalty_pp"])})
AD["vod_B"] = vb
sig = [r for r in vb if r["penalty_pp"] is not None and r["penalty_ci"] and
       re.match(r"\[\s*([+-]?[\d.]+)", r["penalty_ci"]) and
       float(re.match(r"\[\s*([+-]?[\d.]+)", r["penalty_ci"]).group(1)) > 0]
AD["vod_B_significant"] = sorted(sig, key=lambda r: -r["penalty_pp"])[:8]

# ---------- 9b. spectrum-only, LEAK-FREE (W-SPECTRA v31) ----------
AD["spec_leakfree"] = [
    {"block": r["block"], "endpoint": r["endpoint"], "arm": r["arm"],
     "n_test": num(r["n_test"]), "n_leak_free": num(r["n_leak_free"]),
     "pct_all": num(r["pct_naive_all"]), "pct_lf": num(r["pct_naive_leak_free"]),
     "lf_ci": [num(r["lf_ci_lo"]), num(r["lf_ci_hi"])],
     "lf_cov": num(r["lf_cov_empirical"]), "cov_nominal": num(r["cov_nominal"])}
    for r in rows("spec_leakfree") if num(r.get("pct_naive_leak_free")) is not None]
_lfc = [r["lf_cov"] for r in AD["spec_leakfree"] if r["lf_cov"] is not None]
AD["spec_leakfree_cov_range"] = [min(_lfc), max(_lfc)] if _lfc else None

# ---------- 9c. P-004 round 2: measured vs model-derived training labels ----------
_p4 = jload("p004")
AD["p004"] = {"benchmark": _p4.get("benchmark"), "active_definition": _p4.get("active_definition"),
              "targets": {t: {"n": v.get("n_benchmark"),
                              "base_rate": v.get("A_chembl_measured_potency", {}).get("base_rate"),
                              "positives": v.get("A_chembl_measured_potency", {}).get("positives"),
                              "pr_auc_measured_potency": v.get("A_chembl_measured_potency", {}).get("pr_auc"),
                              "pr_auc_measured_call": v.get("A2_chembl_measured_call", {}).get("pr_auc"),
                              "pr_auc_model_labels": v.get("B_opera_consensus_labels", {}).get("pr_auc"),
                              "pr_auc_model_labels_equal_n": v.get("B_eq_opera_equal_n", {}).get("pr_auc"),
                              "delta_ci": v.get("delta_pr_auc_A_minus_B_95CI")}
                          for t, v in (_p4.get("targets") or {}).items()},
              "caveats": _p4.get("caveats")}

# ---------- 9d. P-001 conformer ensembles (W-PHYSICS) ----------
def _c(r, k):
    return (num(r.get("d_" + k)), num(r.get("lo_" + k)), num(r.get("hi_" + k)))
_p1 = [r for r in rows("p001") if r.get("group") == "overall" and r.get("powered") == "True"]
AD["p001"] = [{"endpoint": r["endpoint"], "subset": r["subset"], "n": num(r["n"]),
               "pct_S": num(r["pct_S"]), "pct_SP1": num(r["pct_SP1"]), "pct_SPens": num(r["pct_SPens"]),
               "ens_vs_single_eqdim": _c(r, "SPbz-SP1"),
               "ens_vs_permuted": _c(r, "SPens-SPensperm")} for r in _p1]
_allrows = [r for r in rows("p001") if r.get("powered") == "True"]
def _contains0(r, k):
    lo, hi = num(r.get("lo_" + k)), num(r.get("hi_" + k))
    return lo is not None and hi is not None and lo <= 0 <= hi
AD["p001_summary"] = {
    "n_powered_endpoints": len({r["endpoint"] for r in _allrows}),
    "n_contrast_cells": len(_allrows),
    "n_cells_eqdim_ci_contains_0": sum(1 for r in _allrows if _contains0(r, "SPbz-SP1")),
    "n_cells_perm_ci_contains_0": sum(1 for r in _allrows if _contains0(r, "SPens-SPensperm")),
    "strata": sorted({(r.get("group"), r.get("bin")) for r in _allrows})[:12],
}
for _k in ("SPbz-SP1", "SPens-SPensperm"):
    _cells = [r for r in _allrows if num(r.get("lo_" + _k)) is not None]
    _ex = [r for r in _cells if not (num(r["lo_" + _k]) <= 0 <= num(r["hi_" + _k]))]
    AD["p001_summary"][_k] = {
        "n_cells": len(_cells), "n_exclude_0": len(_ex),
        "n_favouring_ensemble": sum(1 for r in _ex if num(r["hi_" + _k]) < 0),
        "n_overall_cells": len([r for r in _cells if r.get("group") == "overall"]),
        "n_overall_exclude_0": len([r for r in _ex if r.get("group") == "overall"]),
    }

# ---------- 9e. learner control: is the physics effect a LightGBM artefact? ----------
AD["ridge"] = [{"endpoint": r["endpoint"], "subset": r["subset"], "n": num(r["n"]),
                "ridge_S": num(r["ridge_S"]), "ridge_SP": num(r["ridge_SP"]),
                "ridge_ci": [num(r["ridge_SP_minus_S_lo"]), num(r["ridge_SP_minus_S_hi"])],
                "lgbm_S": num(r["lgbm_S"]), "lgbm_SP": num(r["lgbm_SP"]),
                "lgbm_ci": [num(r["lgbm_SP_minus_S_lo"]), num(r["lgbm_SP_minus_S_hi"])]}
               for r in rows("ridge")]

# ---------- 9f. hazard-model domain coverage of the EPA inventory ----------
_ti = jload("tox_inventory")
AD["tox_inventory"] = {k: v for k, v in _ti.items() if k.endswith("|epa_inventory")}

# ---------- 9g. the hypothesis market, as a file ----------
AD["market"] = rows("market")

# ---------- 9h. inventory-scale domain coverage ----------
AD["inv_cov"] = [{k: (num(v) if k != "endpoint" else v) for k, v in r.items()} for r in rows("inv_cov")]
AD["inv_cov_sum"] = jload("inv_cov_sum")
_ip = jload("inv_pred")
AD["inv_pred"] = {"n_predicted": _ip.get("n_predicted"), "n_rows": _ip.get("n_inventory_physics_rows"),
                  "model": _ip.get("model"), "bin_fraction": _ip.get("bin_fraction"),
                  "endpoints": {e: {"units": v.get("units"),
                                    "width_by_bin": v.get("median_interval_width_by_bin"),
                                    "frac_new_element": v.get("frac_new_element")}
                                for e, v in (_ip.get("endpoints") or {}).items()}}
AD["sigma_terciles"] = [{"endpoint": r["endpoint"], "tercile": r["sigma_tercile"], "n": num(r["n"]),
                         "rmse": num(r["rmse"]), "cov_shipped": num(r["cov_shipped"]),
                         "cov_plain": num(r["cov_plain_mondrian"]),
                         "width_shipped": num(r["width_shipped"]), "width_plain": num(r["width_plain"])}
                        for r in rows("sigma_terciles")]

# ---------- 9i. Q-003 amended definedness cells (CRITIC) ----------
_q3 = rows("q003_cells")
AD["q003_changed"] = [{k: r.get(k) for k in r if k in ("endpoint", "compound_class", "class", "cls",
                                                       "q003_verdict", "q003_reason", "n_labelled",
                                                       "n_labelled_skeletons", "changed_by_q003")}
                      for r in _q3 if str(r.get("changed_by_q003")).lower() in ("true", "1", "yes")]
AD["q003_n_cells"] = len(_q3)
AD["phys_inv_cov"] = jload("phys_inv_cov")

# ---------- 10. model vs EPI, shipped model, named file ----------
AD["vs_epi"] = rows("vs_epi")

# ---------- 11. instability of the "physics helps" endpoint set ----------
def sig_set(key):
    out = set()
    for r in rows(key):
        if r.get("bin") == "all" and str(r.get("excludes_0")) == "True" and r.get("subset") == "leak_free":
            out.add(r["endpoint"])
    return sorted(out)
def scored_set(key):
    return sorted({r["endpoint"] for r in rows(key)
                   if r.get("bin") == "all" and r.get("subset") == "leak_free" and r.get("excludes_0") in ("True", "False")})
AD["physics_sig_sets"] = {
    "n_scored": len(scored_set("audit_v5")),
    "scored": scored_set("audit_v5"),
    "v5_dedup": sig_set("audit_v5"),
    "v5_nodedup": sig_set("audit_v5_nodedup"),
    "files": {"v5_dedup": str(path("audit_v5")), "v5_nodedup": str(path("audit_v5_nodedup"))},
}

OUT.write_text(json.dumps(AD, indent=1, default=str))
print("wrote", OUT, "missing sources:", AD["missing"])
for k in ("recall_control_summary", "spec_single_coverage_range", "physics_sig_sets"):
    print(k, json.dumps(AD.get(k), default=str)[:300])
