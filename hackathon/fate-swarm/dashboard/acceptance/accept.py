"""T-020 (PRINCIPAL P3) dashboard acceptance on structures nobody in the run has seen.
Inputs: pred_<name>.json written by run_e2e.sh (tool/wtool_backend.py, live CPU physics + live EPI).
Checks (PRINCIPAL/ACCEPTANCE.md D1):
  novelty: standardised InChIKey absent from labels_v2 AND from the CompTox chemicals table; first-block absent from labels_v2
  per endpoint: either status=undefined with a kind + reason (no number), or value + units (log base stated for log
    quantities) + interval + EMPIRICAL coverage with n + domain flag + attribution + EPI value or explicit "no EPI";
    attribution spectra share == 0 and no spectral block used (frozen_v5 has zero spectral columns).
  render: the page's own show() renders each record in headless Chromium (tool/shoot.py); screenshot + visible text;
    visible text must contain "held" coverage wording and must not attribute anything to a spectrum.
Outputs: accept_report.json, accept_report.md, shots acc_<name>.png (collapsed) and acc_<name>_open.png (all rows expanded)."""
import json, os, sqlite3, subprocess, sys
import pandas as pd
D = os.path.dirname(os.path.abspath(__file__)); W = os.path.dirname(D)
PY = '<TEAM_ROOT>/envs/swarm/bin/python'
NAMES = ['ordinary', 'quat_ammonium', 'pfas_ether_acid', 'no_site_hydrocarbon', 'long_alkane_c40', 'inorganic_nacl']
lab = pd.read_parquet('<TEAM_ROOT>/results/v2/labels_v2.parquet', columns=['inchikey_std'])
LK = set(lab.inchikey_std.dropna()); LB = {k[:14] for k in LK}
con = sqlite3.connect('file:<TEAM_ROOT>/data/comptox_swarm/epa-comptox-swarm.sqlite?mode=ro&immutable=1', uri=True)
NOEPI = {'pka_acidic', 'pka_basic', 'rat_oral_ld50', 'er_potency', 'er_active', 'ar_potency', 'ar_active'}  # EPI has no module
rep = {}; steps = []; r_by = {}
for n in NAMES:
    r = json.load(open(f'{D}/pred_{n}.json'))['records'][0]; r_by[n] = r
    ik = r['input']['inchikey']
    nov = dict(inchikey=ik, in_labels_v2=ik in LK, first_block_in_labels_v2=ik[:14] in LB,
               in_comptox_chemicals=con.execute('select count(*) from chemicals where inchikey=?', (ik,)).fetchone()[0] > 0,
               first_block_in_comptox=con.execute('select count(*) from chemicals where inchikey like ?', (ik[:14] + '%',)).fetchone()[0] > 0)
    fails = []; cnt = dict(numeric=0, undefined=0, classifier=0)
    for ep, e in r['endpoints'].items():
        if e.get('status') == 'undefined':
            cnt['undefined'] += 1
            if e.get('value') is not None or not e.get('kind'):
                fails.append(f'{ep}: undefined but carries a value or no kind')
            continue
        if e.get('status') != 'ok':
            fails.append(f'{ep}: status {e.get("status")}'); continue
        ab = e.get('attribution_blocks') or {}
        if (ab.get('spectra') or 0) != 0 or any('spec' in b for b in e.get('blocks_used') or []):
            fails.append(f'{ep}: spectral attribution {ab}')
        if not ab and not e.get('top_features'):
            fails.append(f'{ep}: no attribution')
        if not e.get('domain'):
            fails.append(f'{ep}: no domain flag')
        if e.get('kind') == 'classifier':
            cnt['classifier'] += 1; continue   # no interval by design; page shows PR-AUC vs base rate
        cnt['numeric'] += 1
        if e.get('value') is None or not e.get('units'):
            fails.append(f'{ep}: value/units missing')
        u = str(e.get('units'))
        if ep not in ('melting_point', 'boiling_point') and 'log' not in u and 'p_activity' not in u:
            fails.append(f'{ep}: units {u} without a stated log base')
        cv = e.get('coverage') or {}
        if not e.get('interval') or cv.get('empirical_coverage') is None or not cv.get('n'):
            fails.append(f'{ep}: interval or empirical coverage/n missing ({cv})')
        if ep not in NOEPI and not (e.get('epi') or {}).get('value') is not None and not e.get('epi_reason'):
            fails.append(f'{ep}: no EPI value and no reason')
    rep[n] = dict(smiles=r['input'].get('smiles'), novelty=nov, counts=cnt, json_fails=fails, physics=r['physics'].get('status'),
                  physics_parity=r['physics'].get('parity'), epi_status=r['epi'].get('status'), epi_returned_smiles=r['epi'].get('returned_smiles'),
                  seconds_total=r.get('seconds_total'))
    js = "document.getElementById('m-struct').click();show('out'," + json.dumps(r) + ");"
    txt = "document.getElementById('out').innerText"
    steps.append(dict(js=js, wait_ms=900, eval=txt, name=n, shot=n, full=True))
    steps.append(dict(js=js + "Array.prototype.forEach.call(document.querySelectorAll('#out tr.main'),function(x){x.click();});",
                      wait_ms=1200, eval=txt, name=n + '_open', shot=n + '_open', full=True))
json.dump(steps, open(f'{D}/steps_acc.json', 'w'))
if '--no-shoot' not in sys.argv: subprocess.run(['timeout', '400', PY, f'{W}/tool/shoot.py', f'{W}/dashboard/index.html', f'{D}/acc', f'{D}/steps_acc.json'],
               stdout=open(f'{D}/shoot_acc.out', 'w'), stderr=subprocess.STDOUT)
log = json.load(open(f'{D}/acc_log.json')) if os.path.exists(f'{D}/acc_log.json') else {}
for n in NAMES:
    vis = {}
    for k in (n, n + '_open'):
        vis[k] = (log.get('evals') or {}).get(k)
    t = vis.get(n + '_open') or ''
    low = t.lower()
    pf = []
    if not t: pf.append('no visible text captured')
    if 'held' not in low: pf.append('no "held" empirical-coverage wording')
    if 'nominal' in low and 'held' not in low: pf.append('nominal without empirical')
    for bad in ('spectrum drove', 'spectrum ' + '1', 'spectral features drove'):
        if bad in low: pf.append(f'spectral attribution text: {bad}')
    nsz = sum(1 for e in r_by[n]['endpoints'].values() if any('OUTSIDE_TRAINING_DESCRIPTOR_RANGE' in str(x) for x in (e.get('flags') or [])))
    if nsz and low.count('extrapolation (size/lipophilicity)') < nsz: pf.append(f'size-range flag on {nsz} rows but badge shown {low.count("extrapolation (size/lipophilicity)")}x')
    rep[n]['size_range_flag_rows'] = nsz
    if rep[n]['counts']['numeric'] and 'spectrum not supplied' not in low and 'spectrum' in low: pf.append('check: spectrum mentioned but not as "not supplied"')
    rep[n]['render'] = dict(chars=len(t), fails=pf, shot=f'{D}/acc_{n}.png', shot_open=f'{D}/acc_{n}_open.png',
                            console_errors=log.get('console'))
    open(f'{D}/visible_{n}_open.txt', 'w').write(t)
json.dump(rep, open(f'{D}/accept_report.json', 'w'), indent=1, default=str)
L = ['# T-020 dashboard acceptance on unseen structures', '', 'Generated by r4_e2e/accept.py from pred_*.json (run_e2e.sh: live CPU AIMNet2 physics + live EPI).', '',
     '| name | SMILES | in labels_v2 | in CompTox chemicals (InChIKey / first block) | numeric / undefined / classifier rows | JSON fails | render fails | physics | EPI |', '|---|---|---|---|---|---|---|---|---|']
for n, x in rep.items():
    v = x['novelty']; c = x['counts']
    L.append(f"| {n} | `{x['smiles']}` | {v['in_labels_v2']} (block {v['first_block_in_labels_v2']}) | {v['in_comptox_chemicals']} / {v['first_block_in_comptox']} | {c['numeric']} / {c['undefined']} / {c['classifier']} | {len(x['json_fails'])} | {len(x['render']['fails'])} | {x['physics']} | {x['epi_status']} |")
L += ['', 'Failures in detail:', ''] + [f"- {n}: {x['json_fails'] + x['render']['fails']}" for n, x in rep.items()]
open(f'{D}/accept_report.md', 'w').write('\n'.join(L) + '\n')
print('\n'.join(L))
