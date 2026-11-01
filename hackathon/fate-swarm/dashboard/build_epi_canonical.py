"""Canonical EPI Suite comparator for run 3 (owner: W-TOOL).

Inputs : labels_v2.parquet (test split), cached raw EPI responses
         (W-LADDER/epi_cache_ladder [main, 4999 test compounds], results/epi_cache, W-TOOL/epi_cache_wtool).
         Test compounds missing from every cache are fetched (<=1 req/s VM-wide via epi_rate.wait_turn)
         into W-TOOL/epi_cache_wtool with a .meta.json provenance record.
Identity: RDKit InChIKey of EPI's returned chemicalProperties.smiles must equal the label inchikey_std
         ('inchikey'), else first-block skeleton match ('skeleton'), else the row is REJECTED (epi value NaN,
         identity='mismatch').
Outputs: epi_comparator_v3.parquet  long table: one row per (test compound, endpoint) incl. pKa rows with
                                    epi_status='no_epi_module'
         epi_comparator_v3_metrics.json / .md: per endpoint EPI RMSE, naive RMSE (predict TRAIN mean),
                                    RMSE as % of naive, overall and by nn_sim_train bin
                                    (<0.3, 0.3-0.5, 0.5-0.7, >=0.7); n and n_test so coverage is visible.
         Cross-check vs W-LADDER/epi_v2_values.parquet (independent earlier extraction) printed + stored.
CAVEAT (carried into every output): EPI's training data (PhysProp) overlaps CompTox; the SMILES-only API
returns no experimental values, so per-compound overlap cannot be flagged -> EPI errors here are optimistic.
"""
import glob, hashlib, json, os, sys, time, urllib.parse, urllib.request, datetime
import numpy as np, pandas as pd
from rdkit import Chem, RDLogger
RDLogger.DisableLog('rdApp.*')
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from epi_extract import extract, EPI_ENDPOINTS, EPI_UNITS, EPI_MODULE
from epi_rate import wait_turn

CACHES = ['W-LADDER/epi_cache_ladder', 'data/epi_cache', f'{HERE}/epi_cache_wtool']
LAB = 'data/labels_v2.parquet'
BINS = [(0, .3, '<0.3'), (.3, .5, '0.3-0.5'), (.5, .7, '0.5-0.7'), (.7, 1.01, '>=0.7')]
CAVEAT = ('EPI numbers are optimistic: EPI Suite was trained on PhysProp, which overlaps CompTox; the SMILES-only API '
          'returns no experimental values, so overlap cannot be flagged per compound.')


def find(ik):
    for c in CACHES:
        p = f'{c}/{ik}.json'
        if os.path.exists(p):
            return p
    return None


def fetch(ik, smi):
    url = 'https://episuite.dev/api/submit?smiles=' + urllib.parse.quote(smi, safe='')
    wait_turn()
    with urllib.request.urlopen(url, timeout=120) as r:
        raw = r.read()
    json.loads(raw)
    p = f'{CACHES[-1]}/{ik}.json'
    open(p, 'wb').write(raw)
    json.dump(dict(inchikey=ik, sent_smiles=smi, request_url=url, retrieved_utc=datetime.datetime.utcnow().isoformat() + 'Z',
                   raw_sha256=hashlib.sha256(raw).hexdigest(), status='ok', fetched_by='W-TOOL build_epi_canonical.py'),
              open(p.replace('.json', '.meta.json'), 'w'), indent=1)
    return p


def main():
    lab = pd.read_parquet(LAB)
    train_mean = lab[lab.split == 'train'].groupby('endpoint').value.mean()
    test = lab[lab.split == 'test'].copy()
    cmp = test.drop_duplicates('inchikey_std')[['inchikey_std', 'smiles_canonical']]
    epi = {}
    nfetch = 0
    for ik, smi in zip(cmp.inchikey_std, cmp.smiles_canonical):
        p = find(ik)
        if p is None:
            try:
                p = fetch(ik, smi); nfetch += 1
            except Exception as e:
                epi[ik] = dict(status='fetch_failed', detail=repr(e)[:200]); continue
        d = json.load(open(p))
        rs = (d.get('chemicalProperties') or {}).get('smiles')
        m = Chem.MolFromSmiles(rs) if rs else None
        rik = Chem.MolToInchiKey(m) if m is not None else None
        ident = 'inchikey' if rik == ik else ('skeleton' if (rik and rik[:14] == ik[:14]) else 'mismatch')
        epi[ik] = dict(status='ok' if ident != 'mismatch' else 'identity_mismatch', identity=ident, returned_smiles=rs,
                       returned_inchikey=rik, cache=p, sha256=hashlib.sha256(open(p, 'rb').read()).hexdigest(),
                       vals=extract(d) if ident != 'mismatch' else {})
    rows = []
    for r in test.itertuples():
        e = epi.get(r.inchikey_std, {})
        if r.endpoint not in EPI_ENDPOINTS:
            st, v, he = 'no_epi_module', np.nan, None
        elif e.get('status') != 'ok':
            st, v, he = e.get('status', 'missing'), np.nan, None
        else:
            v, he = e['vals'].get(r.endpoint, (None, None))
            st = 'ok' if v is not None else 'epi_no_value'
            v = np.nan if v is None else v
        rows.append(dict(inchikey_std=r.inchikey_std, dtxsid=r.dtxsid, smiles=r.smiles_canonical, endpoint=r.endpoint,
                         units=r.units, measured=float(r.value), epi_value=v, epi_status=st,
                         epi_module=EPI_MODULE.get(r.endpoint), epi_units=EPI_UNITS.get(r.endpoint),
                         epi_has_experimental=he, identity=e.get('identity'), returned_smiles=e.get('returned_smiles'),
                         epi_cache=e.get('cache'), epi_raw_sha256=e.get('sha256'), split='test', cluster=r.cluster,
                         nn_sim_train=float(r.nn_sim_train), train_mean=float(train_mean[r.endpoint])))
    T = pd.DataFrame(rows)
    T.to_parquet(f'{HERE}/epi_comparator_v3.parquet', index=False)
    # cross-check with W-LADDER's earlier independent extraction
    xc = {}
    try:
        W = pd.read_parquet('W-LADDER/epi_v2_values.parquet')
        for ep in EPI_ENDPOINTS:
            a = T[(T.endpoint == ep) & T.epi_value.notna()][['inchikey_std', 'epi_value']].drop_duplicates('inchikey_std')
            b = a.merge(W[['inchikey_std', ep]].dropna(), on='inchikey_std')
            xc[ep] = dict(n_compared=int(len(b)), n_abs_diff_gt_1e6=int((np.abs(b.epi_value - b[ep]) > 1e-6).sum()),
                          max_abs_diff=float(np.abs(b.epi_value - b[ep]).max()) if len(b) else None)
    except Exception as ex:
        xc = dict(error=repr(ex))
    # metrics
    def st(g):
        e = g.epi_value - g.measured; n0 = g.measured - g.train_mean
        rm, rn = float(np.sqrt((e ** 2).mean())), float(np.sqrt((n0 ** 2).mean()))
        return dict(n=int(len(g)), rmse=rm, rmse_naive=rn, pct_naive=100 * rm / rn if rn > 0 else None,
                    mae=float(e.abs().mean()))
    M = {}
    for ep, g in T.groupby('endpoint'):
        if ep not in EPI_ENDPOINTS:
            M[ep] = dict(status='no_epi_module', n_test=int(len(g)), note='EPI Suite has no pKa module'); continue
        ok = g[g.epi_value.notna()]
        M[ep] = dict(units=g.units.iloc[0], n_test=int(len(g)), n_with_epi=int(len(ok)),
                     n_identity_skeleton_only=int((ok.identity == 'skeleton').sum()),
                     status_counts=g.epi_status.value_counts().to_dict(), overall=st(ok),
                     by_nn_sim_train={lb: st(ok[(ok.nn_sim_train >= lo) & (ok.nn_sim_train < hi)])
                                      for lo, hi, lb in BINS if ((ok.nn_sim_train >= lo) & (ok.nn_sim_train < hi)).sum() > 0})
    out = dict(_doc=__doc__, caveat=CAVEAT, naive='predict the TRAIN-split mean of labels_v2 for the endpoint',
               pct_naive='100 * RMSE(EPI) / RMSE(naive) on the same rows; 100 = no skill',
               n_fetched_this_run=nfetch, cross_check_vs_WLADDER_epi_v2_values=xc, metrics=M,
               table='epi_comparator_v3.parquet', built_utc=datetime.datetime.utcnow().isoformat() + 'Z')
    json.dump(out, open(f'{HERE}/epi_comparator_v3_metrics.json', 'w'), indent=1, default=float)
    L = ['# EPI Suite comparator v3 (canonical, test split of labels_v2)', '', CAVEAT, '',
         'Error = RMSE as % of the naive guess (train-split mean); 100% = no skill. Source: epi_comparator_v3_metrics.json', '',
         '| endpoint | units | n with EPI / n test | EPI RMSE | % of naive | ' + ' | '.join(f'nn_sim {b[2]}: n, % naive' for b in BINS) + ' |',
         '|' + '---|' * (5 + len(BINS))]
    for ep, m in M.items():
        if m.get('status') == 'no_epi_module':
            L.append(f'| {ep} | log10 | 0 / {m["n_test"]} | no EPI module | - |' + ' - |' * len(BINS)); continue
        cells = []
        for _, _, lb in BINS:
            b = m['by_nn_sim_train'].get(lb)
            cells.append(f'{b["n"]}, {b["pct_naive"]:.0f}%' if b else '0, -')
        L.append(f'| {ep} | {m["units"]} | {m["n_with_epi"]} / {m["n_test"]} | {m["overall"]["rmse"]:.3g} | {m["overall"]["pct_naive"]:.0f}% | ' + ' | '.join(cells) + ' |')
    L += ['', f'Cross-check vs W-LADDER/epi_v2_values.parquet: {json.dumps(xc)}', f'Fetched this run: {nfetch}']
    open(f'{HERE}/epi_comparator_v3_metrics.md', 'w').write('\n'.join(L) + '\n')
    print('\n'.join(L))


if __name__ == '__main__':
    main()
