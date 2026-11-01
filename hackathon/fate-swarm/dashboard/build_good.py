"""Builds good_v3.json: the dashboard's "How good is it?" tables (W-TOOL, run 3).

Error metric: RMSE as % of the naive guess (predict the TRAIN-split mean of labels_v2 for that endpoint),
on the TEST split (leak-free cluster split), overall and by nn_sim_train bin (<0.3, 0.3-0.5, 0.5-0.7, >=0.7;
nn_sim_train taken from labels_v2 by endpoint+full InChIKey). Methods are compared on the SAME rows: for each
endpoint, rows where every listed method has a prediction (EPI included when it has a value); pKa has no EPI.
Interval coverage: empirical fraction of test y inside [lo,hi], printed next to the nominal level.
Config: GOOD_CONFIG below (swap in the frozen model of the run by editing one path).
"""
import json, os, sys
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
LAB = '<TEAM_ROOT>/results/v2/labels_v2.parquet'
EPI = '<TEAM_ROOT>/agents/work/W-TOOL/epi_comparator_v3.parquet'
BINS = [(0, .3, '<0.3'), (.3, .5, '0.3-0.5'), (.5, .7, '0.5-0.7'), (.7, 1.01, '>=0.7')]
CFG_PATH = os.path.join(HERE, 'good_config.json')
DEFAULT_CFG = {
  'structure_methods': [
    {'method': 'this tool: structure only', 'path': '<TEAM_ROOT>/agents/work/W-MODEL/test_predictions_v4_long.parquet', 'variant': 'struct_only', 'nominal': 0.9},
    {'method': 'this tool: + quantum chemistry', 'path': '<TEAM_ROOT>/agents/work/W-MODEL/test_predictions_v4_long.parquet', 'variant': 'struct_physics', 'nominal': 0.9}],
  'spectra_methods': [],
  'card_stats_sources': [{'model_dir': '<TEAM_ROOT>/agents/work/W-MODEL/frozen_v4', 'path': '<TEAM_ROOT>/agents/work/W-MODEL/test_predictions_v4_long.parquet'}],
  'undefined_cells_csv': '<TEAM_ROOT>/agents/work/W-SPACE/refuse_cells_for_dashboard.csv'}


def load_cfg():
    if os.path.exists(CFG_PATH):
        return json.load(open(CFG_PATH))
    json.dump(DEFAULT_CFG, open(CFG_PATH, 'w'), indent=1)
    return DEFAULT_CFG


def stats(y, yhat, mu, lo=None, hi=None):
    if len(y) == 0:
        return dict(n=0, rmse=None, rmse_naive=None, pct=None)
    e = yhat - y; n0 = y - mu
    r = dict(n=int(len(y)), rmse=float(np.sqrt(np.mean(e ** 2))), rmse_naive=float(np.sqrt(np.mean(n0 ** 2))))
    r['pct'] = 100 * r['rmse'] / r['rmse_naive'] if r['rmse_naive'] > 0 else None
    if lo is not None:
        r['coverage'] = float(np.mean((y >= lo) & (y <= hi)))
    return r


def load_wide(m):
    """W-MODEL v5 wide test_predictions: value, <V>, <V>_lo, <V>_hi per row -> long y/yhat/lo/hi."""
    d = pd.read_parquet(m['path'])
    if 'split' in d:
        d = d[d.split == 'test']
    c = m['pred_col']
    d = d[d[c].notna()].rename(columns={'value': 'y'})
    d = d.assign(yhat=d[c], lo=d[c + '_lo'], hi=d[c + '_hi'], variant=m.get('variant_label', c))
    d['skeleton'] = d['inchikey_std']   # run 4 (CRITIC): identity = full standardized InChIKey (stereo kept); column name kept for diff-minimality
    return d[['endpoint', 'skeleton', 'y', 'yhat', 'lo', 'hi', 'variant']]


def load_method(m, lab_test):
    if 'pred_col' in m:
        return load_wide(m).drop_duplicates(['endpoint', 'skeleton'])
    d = pd.read_parquet(m['path'])
    if 'variant' in m and 'variant' in d:
        d = d[d.variant == m['variant']]
    d['skeleton'] = d['inchikey_std']   # full InChIKey identity (run 4)
    d = d.drop_duplicates(['endpoint', 'skeleton'])
    return d


QPATH = '<TEAM_ROOT>/agents/work/W-SPACE/quarantine_v3.parquet'
# quarantine_v3 is one row per (InChIKey first block, endpoint): leak-freeness is a skeleton-level property, so it is
# joined on the first block (sk14) while row identity stays the full InChIKey (run 4).
QV = pd.read_parquet(QPATH)[['skeleton', 'endpoint', 'split', 'leak_free']].rename(columns={'skeleton': 'sk14'})
QV = QV[QV.split == 'test'].drop_duplicates(['sk14', 'endpoint'])
MIN_LF = 10  # W-SPACE: logkoa has 3 leak-free test rows -> do not report


MISC = '<TEAM_ROOT>/results/v2/labels_tox_v2_miscibility.parquet'
NBOOT = 1000


def train_mean(lab):
    """Naive guess = train-split mean per endpoint. water_solubility: miscibility-gated rows
    (labels_tox_v2_miscibility.exclude_from_solubility_fit) are dropped, as in the frozen model's fit (READER-2 N-027)."""
    tr = lab[lab.split == 'train']
    mu = tr.groupby('endpoint').value.mean()
    if os.path.exists(MISC):
        ex = pd.read_parquet(MISC)
        ex = set(ex.loc[ex.exclude_from_solubility_fit == True, 'inchikey_std'])
        w = tr[(tr.endpoint == 'water_solubility') & ~tr.inchikey_std.isin(ex)]
        mu['water_solubility'] = w.value.mean()
    return mu


def boot_ci(df, cols, mu, seed=0):
    """Cluster bootstrap (resample labels_v2 test clusters, NBOOT reps) of RMSE % of naive for each column in cols,
    and of the paired difference cols[i] - cols[-1] (cols[-1] = EPI when present). 95% percentile intervals."""
    if len(df) < MIN_LF or df.cluster.isna().all():
        return {}, {}
    rng = np.random.default_rng(seed)
    cl = df.cluster.fillna(-1).values; uc = np.unique(cl); idx = {c: np.where(cl == c)[0] for c in uc}
    y = df.y.values; P = {c: df[c].values for c in cols}
    res = {c: [] for c in cols}
    for _ in range(NBOOT):
        ii = np.concatenate([idx[c] for c in rng.choice(uc, len(uc), replace=True)])
        nv = np.sqrt(np.mean((y[ii] - mu) ** 2))
        for c in cols:
            res[c].append(100 * np.sqrt(np.mean((P[c][ii] - y[ii]) ** 2)) / nv)
    ci = {c: (float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))) for c, v in res.items()}
    ref = np.array(res[cols[-1]])
    dci = {c: (float(np.percentile(np.array(res[c]) - ref, 2.5)), float(np.percentile(np.array(res[c]) - ref, 97.5))) for c in cols[:-1]}
    return ci, dci


def section(methods, lab, epi, with_epi=True):
    mu = train_mean(lab)
    test = lab[lab.split == 'test'].copy(); test['skeleton'] = test.inchikey_std
    nn = test.groupby(['endpoint', 'skeleton']).nn_sim_train.max().rename('nn').reset_index()
    clu = test.groupby('skeleton').cluster.first().reset_index()
    tabs = [(m, load_method(m, test)) for m in methods]
    out = {}
    for ep in sorted(set().union(*[set(t.endpoint) for _, t in tabs])):
        base = None
        for m, t in tabs:
            tt = t[t.endpoint == ep][['skeleton', 'y', 'yhat'] + [c for c in ('lo', 'hi') if c in t]].rename(
                columns={'yhat': 'yhat_' + m['method'], 'lo': 'lo_' + m['method'], 'hi': 'hi_' + m['method']})
            base = tt if base is None else base.merge(tt.drop(columns=['y']), on='skeleton', how='inner')
        e = None
        if with_epi and not ep.startswith('pka'):
            e = epi[(epi.endpoint == ep) & epi.epi_value.notna()].copy(); e['skeleton'] = e.inchikey_std
            e = e.drop_duplicates('skeleton')[['skeleton', 'epi_value']]
            base = base.merge(e, on='skeleton', how='inner')
        base = base.merge(nn[nn.endpoint == ep][['skeleton', 'nn']], on='skeleton', how='left')
        base['sk14'] = base.skeleton.str[:14]
        base = base.merge(QV[QV.endpoint == ep][['sk14', 'leak_free']], on='sk14', how='left')
        base = base.merge(clu, on='skeleton', how='left')
        rows = []
        cols = [(m['method'], 'yhat_' + m['method'], m.get('nominal')) for m, _ in tabs] + ([('EPI Suite (optimistic: its training data overlap CompTox)', 'epi_value', None)] if e is not None else [])
        lfb = base[base.leak_free == True]
        ccols = [c for _, c, _ in cols]
        ci_lf, d_lf = boot_ci(lfb, ccols, mu[ep]); ci_all, d_all = boot_ci(base, ccols, mu[ep], seed=1)
        has_epi = e is not None
        for name, col, nom in cols:
            has_int = ('lo_' + name) in base
            r = dict(method=name, overall=stats(base.y.values, base[col].values, mu[ep]), bins={})
            lf = base[base.leak_free == True]
            r['leak_free'] = stats(lf.y.values, lf[col].values, mu[ep]) if len(lf) >= MIN_LF else dict(n=int(len(lf)), pct=None, too_few=True)
            for lo, hi, lb in BINS:
                s = base[(base.nn >= lo) & (base.nn < hi)]
                if len(s):
                    r['bins'][lb] = stats(s.y.values, s[col].values, mu[ep])
            if col in ci_all:
                r['overall']['ci95'] = ci_all[col]
            if col in ci_lf and not r['leak_free'].get('too_few'):
                r['leak_free']['ci95'] = ci_lf[col]
            if has_epi and col != 'epi_value':
                for key, dd in (('leak_free', d_lf), ('overall', d_all)):
                    if col in dd and not r[key].get('too_few'):
                        lo_, hi_ = dd[col]
                        r[key]['vs_epi_diff_ci95'] = [lo_, hi_]
                        r[key]['vs_epi'] = 'better than EPI' if hi_ < 0 else ('worse than EPI' if lo_ > 0 else 'not resolved vs EPI')
                        if key == 'leak_free' and r[key]['vs_epi'] == 'better than EPI' and BONF.get(ep) not in (None, 'model better'):
                            # S-7 run 4: do not claim more than the paper. Paper claims only wins surviving Bonferroni over m=9
                            # (W-MODEL/v5_main/vs_epi_intervals.csv verdict_bonferroni); koc/logkow are raw-CI wins only.
                            r[key]['vs_epi'] = 'marginal: better on the unadjusted interval only; not significant after Bonferroni correction over 9 comparisons, so not claimed'
                            r[key]['vs_epi_bonferroni'] = BONF.get(ep)
            if has_int:
                cv = lambda x: dict(empirical=float(np.mean((x.y >= x['lo_' + name]) & (x.y <= x['hi_' + name]))), n=int(len(x))) if len(x) else None
                r['coverage'] = dict(nominal=nom, **cv(base))
                r['coverage']['leak_free'] = cv(lf) if len(lf) >= MIN_LF else None   # CRITIC run 4: coverage on the leak-free rows too
                r['coverage']['bins'] = {lb: cv(base[(base.nn >= lo) & (base.nn < hi)]) for lo, hi, lb in BINS}
            rows.append(r)
        out[ep] = dict(rows=rows, n_same_rows=int(len(base)), n_missing_nn=int(base.nn.isna().sum()),
                       note=(f'{len(base)} test chemicals with a prediction from every method listed'
                             + ('' if e is not None else ('; EPI Suite has no pKa module' if ep.startswith('pka') else ''))
                             + ('. These are the rows where EPI Suite (AOPWIN) returns a value: it abstains on 4 perhalogenated halons'
                                ' (no abstractable H; measured log10 kOH -15 to -16 cm3/molecule/s), which are excluded here. On all 101'
                                ' test rows the shipped model is 47.8% of naive (W-TOOL/dashboard/crosscheck_paper_r4.md)' if ep == 'koh_gas' else '')))
    return out


_BF = pd.read_csv('<TEAM_ROOT>/agents/work/W-MODEL/v5_main/vs_epi_intervals.csv')
BONF = dict(zip(_BF.endpoint, _BF.verdict_bonferroni))


def card_stats(cfg, lab):
    """Per model_dir/variant/endpoint: test n, % of naive, empirical coverage, median width - overall and per
    nn_sim_train bin, on ALL test rows of that model (not the same-rows subset). Written to tool/card_stats.json;
    the dashboard cards cite these next to each prediction."""
    mu = train_mean(lab)
    test = lab[lab.split == 'test'].copy(); test['skeleton'] = test.inchikey_std
    nn = test.groupby(['endpoint', 'skeleton']).nn_sim_train.max().rename('nn').reset_index()
    out = {}
    for src in cfg.get('card_stats_sources', []):
        d = load_wide(src) if 'pred_col' in src else pd.read_parquet(src['path'])
        if 'skeleton' not in d:
            d['skeleton'] = d.inchikey_std
        d = d.merge(nn, on=['endpoint', 'skeleton'], how='left')
        for (var, ep), g in d.groupby(['variant', 'endpoint']):
            def st(x):
                r = stats(x.y.values, x.yhat.values, mu[ep], x.lo.values, x.hi.values)
                r['median_width'] = float(np.median(x.hi - x.lo)); r['rmse_pct_naive'] = r['pct']; r['empirical_coverage'] = r['coverage']
                return r
            bins = {lb: st(g[(g.nn >= lo) & (g.nn < hi)]) for lo, hi, lb in BINS if ((g.nn >= lo) & (g.nn < hi)).sum() > 0}
            gl = g.assign(sk14=g.skeleton.str[:14]).merge(QV[QV.endpoint == ep][['sk14', 'leak_free']], on='sk14', how='left')
            gl = gl[gl.leak_free == True]
            lf = st(gl) if len(gl) >= MIN_LF else dict(n=int(len(gl)), rmse_pct_naive=None, too_few=True)
            out.setdefault(src['model_dir'], {}).setdefault(var, {})[ep] = dict(all=st(g), bins=bins, leak_free=lf, source=src['path'], n_missing_nn=int(g.nn.isna().sum()))
    json.dump(out, open('<TEAM_ROOT>/agents/work/W-TOOL/tool/card_stats.json', 'w'), indent=1, default=float)
    return out


def main():
    cfg = load_cfg()
    lab = pd.read_parquet(LAB); epi = pd.read_parquet(EPI)
    card_stats(cfg, lab)
    g = dict(_doc=__doc__, bins=[b[2] for b in BINS], config=cfg,
             note=('LEAK-FREE column first: test chemicals with Tanimoto < 0.40 to every training skeleton (W-SPACE quarantine_v3, canonical; fewer than 10 rows = not reported). '
                   'The other columns use the whole cluster-held-out test set, which still contains near neighbours of training chemicals. '
                   'Naive guess = training-set mean of each property (water solubility: miscibility-gated rows excluded, as in the model fit). 95% intervals: cluster bootstrap over test clusters (1000 reps). A method is called better or worse than EPI Suite only when the 95% interval of the paired difference excludes 0; otherwise not resolved. Same test chemicals for every method in a row block. '
                   'Identity here: one row per full standardized InChIKey (stereo kept), the same key as the paper (run 4 fix after CRITIC audit; earlier builds merged stereoisomers on the first InChIKey block). '
                   'nn_sim = highest Tanimoto (Morgan r2) similarity to any training compound. EPI Suite has no intervals.'),
             sources=[m['path'] for m in cfg['structure_methods']] + [EPI, LAB, QPATH],
             endpoints=section(cfg['structure_methods'], lab, epi, True))
    SPM = '<TEAM_ROOT>/agents/work/W-SPECTRA/spectrum_only_v31/manifest.json'
    if os.path.exists(SPM):
        man = json.load(open(SPM)); BM = {'0-0.3': '<0.3', '0.3-0.5': '0.3-0.5', '0.5-0.7': '0.5-0.7', '0.7-1.0': '>=0.7'}
        names = {'pos': 'ESI positive', 'neg': 'ESI negative', 'ei': 'EI (GC-MS)'}
        sp = {}
        LFS = '<TEAM_ROOT>/agents/work/W-SPECTRA/v31/report/leak_free_v31.csv'
        lfs = pd.read_csv(LFS) if os.path.exists(LFS) else pd.DataFrame(columns=['block', 'endpoint', 'arm'])
        lfs = lfs[lfs.arm == 'SINGLE_spectrum'].set_index(['block', 'endpoint'])

        def spec_lf(blk, ep):
            # leak-free = W-SPACE quarantine_v3 rows, computed by W-SPECTRA for the deployed SINGLE_spectrum arm
            if (blk, ep) not in lfs.index:
                return None, 'not checked on unseen chemistry'
            r = lfs.loc[(blk, ep)]
            if pd.isna(r.pct_naive_leak_free) or r.n_leak_free < MIN_LF:
                return dict(n=int(r.n_leak_free), too_few=True), 'not checked on unseen chemistry (too few)'
            d = dict(n=int(r.n_leak_free), pct=float(r.pct_naive_leak_free), ci95=[float(r.lf_ci_lo), float(r.lf_ci_hi)],
                     coverage_empirical=float(r.lf_cov_empirical), coverage_nominal=float(r.cov_nominal))
            return d, ('leak-free 95% CI below 100% of naive' if r.lf_ci_hi < 100 else 'leak-free 95% CI reaches 100% of naive: skill not established')
        for blk, B in man['blocks'].items():
            for ep, E in B['endpoints'].items():
                T = E['test']
                bins = {BM.get(k, k): dict(n=v.get('n'), pct=v.get('pct_naive')) for k, v in (T.get('by_bin') or {}).items()}
                rows = sp.setdefault(ep, dict(rows=[]))['rows']
                lfd, lab_ = spec_lf(blk, ep)
                rows.append(dict(method=f'spectrum only, {names.get(blk, blk)} ({lab_})', skill_label=lab_,
                                 overall=dict(n=E.get('n_test'), pct=T.get('pct_naive')), leak_free=lfd, bins=bins,
                                 coverage=dict(empirical=T.get('conformal_empirical'), nominal=E.get('conformal_nominal'))))
                mm = (E.get('mass_model') or {}).get('test') or {}
                if mm.get('pct_naive') is not None:
                    rows.append(dict(method=f'  mass + adduct only, {names.get(blk, blk)}', overall=dict(n=E.get('n_test'), pct=mm.get('pct_naive')), bins={},
                                     coverage=dict(empirical=mm.get('conformal_empirical'), nominal=E.get('conformal_nominal'))))
                if E.get('structure_same_compounds_pct_naive') is not None:
                    rows.append(dict(method=f'  known structure, same compounds ({names.get(blk, blk)})', overall=dict(n=E.get('n_test'), pct=E.get('structure_same_compounds_pct_naive')), bins={}))
        g['spectra'] = dict(endpoints=sp, sources=[SPM, LFS], note=('Spectrum-only models by ion block (W-SPECTRA spectrum_only_v31). The bins are the STRUCTURAL novelty of the test compounds. '
                            'Mass + adduct only shows what the fragments add; "known structure, same compounds" shows the gap to having the structure. '
                            'Spectral similarity was found UNINFORMATIVE about error for HR-ESI, so no novelty tag is shown on spectrum-only predictions. '
                            'LEAK-FREE column (ESI only; W-SPECTRA leak_free_v31.csv, deployed single-spectrum model): states only whether its 95% CI stays below 100% of naive. '
                            'DISPUTED, left open: how many endpoints a spectrum alone has skill for differs between our deliverables (3 or 4, scored on different models under different bars); this column is not a verdict on that count. '
                            'EI has no leak-free check. Spectrum-only intervals under-cover on unseen chemistry (empirical 0.81-0.96 at nominal 0.90). '
                            'These are the models this page runs; the paper\'s spectral ablation used separate W-MODEL v5 models, so its numbers differ.'))
    elif cfg.get('spectra_methods'):
        g['spectra'] = dict(endpoints=section(cfg['spectra_methods'], lab, epi, False), sources=[m['path'] for m in cfg['spectra_methods']],
                            note=cfg.get('spectra_note', ''))
    else:
        g['spectra'] = dict(endpoints={}, sources=[], note='Spectrum-only test results not yet delivered by W-SPECTRA this run.')
    uc = cfg.get('undefined_cells_csv')
    if uc and os.path.exists(uc):
        u = pd.read_csv(uc)
        keep = [c for c in ['cls', 'endpoint', 'n_inventory', 'n_A_undefined', 'n_B_nonequivalent', 'reason'] if c in u.columns]
        g['undefined_cells'] = u[keep].rename(columns={'cls': 'compound class', 'n_inventory': 'n in inventory', 'n_A_undefined': 'n undefined (A)',
                                                      'n_B_nonequivalent': 'n not standard-measurable (B)'}).astype(str).replace('nan', '').to_dict('records')
        g['undefined_cells_source'] = uc
    json.dump(g, open(os.path.join(HERE, 'good_v3.json'), 'w'), indent=1, default=float)
    for ep, v in g['endpoints'].items():
        print(ep, v['n_same_rows'], ' | '.join(f"{r['method'][:28]}: {(r['overall']['pct'] or -1):.0f}% n={r['overall']['n']}" + (f" cov {r['coverage']['empirical']:.2f}" if 'coverage' in r else '') for r in v['rows']))


if __name__ == '__main__':
    main()
