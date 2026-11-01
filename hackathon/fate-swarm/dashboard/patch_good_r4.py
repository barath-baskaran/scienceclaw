"""Run-4 patch to build_good.py (W-TOOL): gated water_solubility naive mean (READER-2 N-027),
cluster-bootstrap 95% CIs on every % of naive cell, and a paired model-vs-EPI verdict that only says
better/worse when the 95% CI of the difference excludes 0. Idempotent: applies to build_good.py.bak_r4."""
import os
D = os.path.dirname(os.path.abspath(__file__))
s = open(os.path.join(D, 'build_good.py.bak_r4')).read()


def rep(a, b):
    global s
    assert s.count(a) == 1, a[:80]
    s = s.replace(a, b)


rep("""def section(methods, lab, epi, with_epi=True):
    mu = lab[lab.split == 'train'].groupby('endpoint').value.mean()""", '''MISC = '<TEAM_ROOT>/results/v2/labels_tox_v2_miscibility.parquet'
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
    mu = train_mean(lab)''')
rep("""        base = base.merge(QV[QV.endpoint == ep][['skeleton', 'leak_free']], on='skeleton', how='left')
        rows = []""", """        base = base.merge(QV[QV.endpoint == ep][['skeleton', 'leak_free']], on='skeleton', how='left')
        base = base.merge(clu, on='skeleton', how='left')
        rows = []""")
rep("""    nn = test.groupby(['endpoint', 'skeleton']).nn_sim_train.max().rename('nn').reset_index()
    tabs = [(m, load_method(m, test)) for m in methods]""", """    nn = test.groupby(['endpoint', 'skeleton']).nn_sim_train.max().rename('nn').reset_index()
    clu = test.groupby('skeleton').cluster.first().reset_index()
    tabs = [(m, load_method(m, test)) for m in methods]""")
rep("""        for name, col, nom in cols:
            has_int""", """        lfb = base[base.leak_free == True]
        ccols = [c for _, c, _ in cols]
        ci_lf, d_lf = boot_ci(lfb, ccols, mu[ep]); ci_all, d_all = boot_ci(base, ccols, mu[ep], seed=1)
        has_epi = e is not None
        for name, col, nom in cols:
            has_int""")
rep("""            if has_int:
                r['coverage']""", """            if col in ci_all:
                r['overall']['ci95'] = ci_all[col]
            if col in ci_lf and not r['leak_free'].get('too_few'):
                r['leak_free']['ci95'] = ci_lf[col]
            if has_epi and col != 'epi_value':
                for key, dd in (('leak_free', d_lf), ('overall', d_all)):
                    if col in dd and not r[key].get('too_few'):
                        lo_, hi_ = dd[col]
                        r[key]['vs_epi_diff_ci95'] = [lo_, hi_]
                        r[key]['vs_epi'] = 'better than EPI' if hi_ < 0 else ('worse than EPI' if lo_ > 0 else 'not resolved vs EPI')
            if has_int:
                r['coverage']""")
rep("""    the dashboard cards cite these next to each prediction.\"\"\"
    mu = lab[lab.split == 'train'].groupby('endpoint').value.mean()""", """    the dashboard cards cite these next to each prediction.\"\"\"
    mu = train_mean(lab)""")
rep("'Naive guess = training-set mean of each property. ",
    "'Naive guess = training-set mean of each property (water solubility: miscibility-gated rows excluded, as in the model fit). "
    "95% intervals: cluster bootstrap over test clusters (1000 reps). A method is called better or worse than EPI Suite only when the 95% interval "
    "of the paired difference excludes 0; otherwise not resolved. ")
open(os.path.join(D, 'build_good.py'), 'w').write(s)
print('patched build_good.py')
