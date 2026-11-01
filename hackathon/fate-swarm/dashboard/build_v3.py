"""Build the v3 dashboard: dashboard/index.html, ONE static file that opens offline (file://), no CDN, no network.

Embeds (window.__DATA__): endpoint metadata (plain-language), real example predictions computed NOW by
tool/wtool_backend.py from the frozen models in tool/models_registry.json, spectrum-only examples, the
"How good is it?" tables (good_v3.json from build_good.py), the model list and build info.
With tool/serve.py running on 127.0.0.1, the same page computes new structures live.

  <TEAM_ROOT>/envs/swarm/bin/python build_v3.py [--quick]    (--quick: no physics for examples, fewer examples)
"""
import argparse, datetime, json, os, sqlite3, subprocess, sys, time
import pandas as pd
D = os.path.dirname(os.path.abspath(__file__)); T = os.path.join(os.path.dirname(D), 'tool')
sys.path.insert(0, T)
import wtool_backend as B
from rdkit import Chem

ap = argparse.ArgumentParser(); ap.add_argument('--quick', action='store_true'); ap.add_argument('--out', default=os.path.join(D, 'index.html'))
a = ap.parse_args()
LAB = '<TEAM_ROOT>/results/v2/labels_v2.parquet'
lab = pd.read_parquet(LAB)

EPMETA = {
 'logkow': ('Octanol–water partition (log Kow)', 'how strongly it prefers fat-like phases over water', 'log10 (unitless)', 'KOWWIN'),
 'water_solubility': ('Water solubility', 'how much dissolves in water', 'log10 mol/L', 'WSKOWWIN'),
 'vapor_pressure': ('Vapour pressure', 'how readily it evaporates (25 °C)', 'log10 mmHg', 'MPBPVP'),
 'henry': ("Henry's law constant", 'how it splits between air and water', 'log10 atm·m³/mol', 'HENRYWIN'),
 'boiling_point': ('Boiling point', '', '°C', 'MPBPVP'),
 'melting_point': ('Melting point', '', '°C', 'MPBPVP'),
 'koc': ('Soil sorption (log Koc)', 'how strongly it binds to soil organic carbon', 'log10 L/kg', 'KOCWIN'),
 'bcf': ('Bioconcentration in fish (log BCF)', 'how much it accumulates in fish from water', 'log10 L/kg', 'BCFBAF'),
 'logkoa': ('Octanol–air partition (log Koa)', 'how it splits between fat-like phases and air', 'log10 (unitless)', 'KOAWIN'),
 'koh_gas': ('Breakdown in air by OH radicals (log kOH)', 'gas-phase reaction rate; sets lifetime in air', 'log10 cm³/(molecule·s)', 'AOPWIN'),
 'pka_acidic': ('Acid strength (pKa, most acidic site)', 'pH at which the most acidic group is half ionised', 'pKa units', None),
 'pka_basic': ('Base strength (pKa, most basic site)', 'pH at which the most basic group is half protonated', 'pKa units', None),
 'er_binding': ('Estrogen receptor binding', 'screening-level call', 'probability active', None),
 'ar_agonist': ('Androgen receptor agonism', 'screening-level call', 'probability active', None),
 'rat_oral_ld50': ('Acute oral toxicity, rat (LD50)', 'trained on measured rat LD50; acute lethality only', 'log10 mmol/kg body weight', None),
 'er_active': ('Estrogen receptor: potent in vitro?', 'call = model predicts in-vitro potency ≤ 1 µM (trained on measured potencies)', 'call + probability', None),
 'er_potency': ('Estrogen receptor potency (in vitro)', 'p_activity = -log10(M); higher = more potent', 'p_activity (-log10 M)', None),
 'ar_active': ('Androgen receptor: potent in vitro?', 'call = model predicts in-vitro potency ≤ 1 µM (trained on measured potencies)', 'call + probability', None),
 'ar_potency': ('Androgen receptor potency (in vitro)', 'p_activity = -log10(M); higher = more potent', 'p_activity (-log10 M)', None),
}
tr = lab[lab.split == 'train']
endpoints = {}
for ep, (label, what, units, epi) in EPMETA.items():
    g = tr[tr.endpoint == ep].value
    endpoints[ep] = dict(label=label, what=what, units=units, epi=epi,
                         scale=[float(g.quantile(.02)), float(g.quantile(.98))] if len(g) else None,
                         n_train=int(len(g)), n_test=int(((lab.split == 'test') & (lab.endpoint == ep)).sum()))
endpoints['er_binding']['scale'] = [0, 1]; endpoints['ar_agonist']['scale'] = [0, 1]
for _e in ('er_potency', 'ar_potency'): endpoints[_e]['scale'] = [3, 10]
endpoints['rat_oral_ld50']['scale'] = [-3, 2]

con = sqlite3.connect('file:<TEAM_ROOT>/data/comptox_swarm/epa-comptox-swarm.sqlite?mode=ro&immutable=1', uri=True)
def name_of(dtx, ik=None):
    """CompTox preferred name, only if that record's InChIKey equals the label's (labels are desalted: a salt's DTXSID
    can carry the parent structure, e.g. pyridinium chlorochromate -> pyridine)."""
    try:
        cols = [r[1] for r in con.execute('pragma table_info(chemicals)')]
        nc = next(c for c in ('preferredName', 'preferred_name', 'name') if c in cols)
        ic = next(c for c in ('dtxsid', 'DTXSID') if c in cols)
        r = con.execute(f'select {nc}, inchikey from chemicals where {ic}=?', (dtx,)).fetchone()
        if r and (ik is None or (r[1] or '')[:14] == ik[:14]):
            return r[0]
        return None
    except Exception:
        return None


models = B.discover_models()
examples = []
def add(smi, short, why, truth=False, physics=True):
    t = time.time()
    r = B.predict_record(smi, None, models, epi_live=True, physics=physics and not a.quick)
    r['seconds_total'] = round(time.time() - t, 1)
    if truth:
        ik = r['input'].get('inchikey')
        rows = lab[lab.inchikey_std == ik]
        r['truth'] = {x.endpoint: dict(value=float(x.value), split=x.split, units=x.units) for x in rows.itertuples()}
    r['label'] = why
    examples.append(dict(short=short, why=why, rec=r))
    print(f'  example {short}: {r["seconds_total"]} s, physics {r.get("physics", {}).get("status")}', flush=True)

# 1. genuinely new structures (not in labels_v2 by InChIKey or skeleton; checked below)
NEW = [('CC(C)(C)c1ccc(OCC(F)(F)C(F)F)cc1', 'New: fluorinated aryl ether', 'A structure that is not in any of our label sets (checked by InChIKey and skeleton).'),
       ('CC(Oc1ccc(F)cc1)C(=O)O', 'New: hydrolysis product', 'Amide-hydrolysis product of a test-set chemical (W-TP); never measured and not in the label sets.'),
       ('O=C(O)c1cc(S(=O)(=O)N2CCC(C(F)(F)F)CC2)ccc1F', 'New: sulfonamide acid', 'A drug-like structure that is not in the label sets.')]
SALT = [('C[N+](C)(C)CCCCCCCCCCCCCC.[Br-]', 'Quaternary ammonium salt', 'A permanently charged surfactant: some properties do not exist for it, so the tool refuses rather than giving a number.'),
        ('CCCCCCCCCCCCc1ccc(S(=O)(=O)[O-])cc1.[Na+]', 'Sodium sulfonate salt', 'A salt: estimates are made for the neutral parent, with the caveats W-SPACE derived.')]
try:  # one W-TP transformation product (unmeasured, first-generation abiotic), with provenance
    # W-TP run 4: the uncleaned file held 2 ring-cleavage artefacts (atoms dropped); use the cleaned file and the small
    # OX-SOXID <0.3 row (CPU physics is fast for it). Audit: W-TP/tp_ring_artefact_audit.json
    tp = pd.read_csv('<TEAM_ROOT>/agents/work/W-TP/tp_dashboard_examples_v3_clean.csv')
    tp = tp[tp.product_smiles == 'NC1CCS(=O)C1=O'] if (tp.product_smiles == 'NC1CCS(=O)C1=O').any() else tp[tp.c_bin == '<0.3'].head(1)
    for r in tp.itertuples():
        NEW.append((r.product_smiles, 'New: transformation product',
                    f'Predicted {r.pathway} product ({r.rule_id}: {r.rule_rationale}; rate class {r.rate_class}) of test-set chemical {r.parent_dtxsid} '
                    f'({r.parent_smiles}). Never measured. Source: W-TP tp_dashboard_examples_v3_clean.csv; rules reviewed by W-TOX (R5).'))
except Exception as e:
    print('W-TP examples unavailable', e)
known_sk = set(lab.skeleton)
for smi, short, why in NEW + SALT:
    sk = Chem.MolToInchiKey(Chem.MolFromSmiles(smi))[:14]
    if sk in known_sk:
        why += ' NOTE: skeleton IS in labels_v2.'
    add(smi, short, why, truth=False, physics=(smi, short, why) in NEW)
# 2. test-split chemicals with several measured properties (shows measured vs estimate), one per novelty band
t = lab[lab.split == 'test']
c = t.groupby('inchikey_std').agg(n=('endpoint', 'size'), nn=('nn_sim_train', 'max'), smi=('smiles_canonical', 'first'), dtx=('dtxsid', 'first'))
c = c[(c.n >= 5) & c.smi.str.len().between(8, 70) & ~c.smi.str.contains(r'\+|\.|-\]|Cr|Sn|Hg|Pb|Si|B')]
for lo, hi, lb in [(0.3, 0.5, 'somewhat new'), (0.5, 0.7, 'fairly familiar'), (0.7, 1.01, 'familiar')]:
    g = c[(c.nn >= lo) & (c.nn < hi)].sort_values('n', ascending=False).head(15)
    g = g[[bool(name_of(r.dtx, i)) and len(name_of(r.dtx, i)) <= 30 for i, r in g.iterrows()]].head(1)
    for ik, row in g.iterrows():
        nm = name_of(row.dtx, ik)
        add(row.smi, f'Measured: {nm[:28]}', f'{nm} ({row.dtx}): a TEST-set chemical, never used in training, with {row.n} measured values shown next to the estimates. Similarity to training: {row.nn:.2f} ({lb}).', truth=True, physics=False)

# spectrum-only examples
spec_examples = []
SX = '<TEAM_ROOT>/agents/work/W-SPECTRA/dashboard_examples.json'
srcs = []
if os.path.exists(SX):
    try:
        srcs = json.load(open(SX))
        srcs = srcs.get('examples', srcs) if isinstance(srcs, dict) else srcs
    except Exception as e:
        print('W-SPECTRA examples unreadable', e)
if not srcs and os.path.exists('<TEAM_ROOT>/agents/work/W-UNKNOWN/demo_spectrum.json'):
    d = json.load(open('<TEAM_ROOT>/agents/work/W-UNKNOWN/demo_spectrum.json'))
    m = dict(d['meta']); m.setdefault('collision_energy', m.get('collision_energy_eV')); m.setdefault('ionization_mode', m.get('polarity'))
    srcs = [dict(dtxsid=d.get('dtxsid'), short='Test-set spectrum (run 2 demo)', spectrum=dict(mz=d['mz'], intensity=d['intensity'], meta=m))]
for sx in srcs[:4]:
    spec = sx.get('spectrum') or sx.get('input') or sx
    r = B.predict_record(None, spec, models)
    r['input']['spectrum'] = spec
    rows = lab[lab.dtxsid == sx.get('dtxsid')]
    r['truth'] = {x.endpoint: dict(value=float(x.value), split=x.split, units=x.units) for x in rows.itertuples()}
    why = f'Measured MS/MS of a test-set chemical ({sx.get("dtxsid")}); its structure is hidden from the model. Measured values are shown for comparison.'
    r['label'] = why
    spec_examples.append(dict(short=sx.get('short') or sx.get('name') or sx.get('dtxsid'), why=why, rec=r))

subprocess.run([sys.executable, os.path.join(D, 'build_good.py')], check=True)
good = json.load(open(os.path.join(D, 'good_v3.json')))
models_pub = [{k: v for k, v in m.items() if k not in ('meta',)} for m in models]
here = os.path.dirname(D)
build = dict(built_utc=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M UTC'), version='W-TOOL dashboard v3 (run 3)',
             start_cmd=f'bash {here}/start_dashboard.sh',
             physics_note='Physics is computed on this computer (AIMNet2 on CPU, ETKDG+MMFF start, same settings as the training table).',
             hazard_caveat=('Hazard rows come from W-TOX models trained on MEASURED data (each row states its label source). In-vitro receptor potency is not an in-vivo endocrine hazard call and says nothing about exposure or dose. LD50: acute lethality only, not chronic, not ecological.'),
             hazard_caveat_old=('ER/AR: Source: OPERA 2.8 (CERAPP/CoMPARA) consensus call from a set of QSAR models, derived from screening assays. '
                            'This is a model output, not a measurement. No OPERA comparator is shown, because that would compare our model with another model\'s labels. '
                            'Rat LD50: trained on measured acute oral LD50 in rat, median over records (CompTox hazards table), log10 mmol/kg bw. Acute lethality only; not chronic, not ecological. '
                            '(Wording: W-TOX review R4.)'),
             about=['Predictions come only from frozen models listed below; nothing is fitted in this page.',
                    'Novelty ("new to the model?") = highest Tanimoto similarity (Morgan radius-2 fingerprint) to any training compound: below 0.3 = new, 0.3-0.5 = somewhat new, 0.5 and above = familiar. For spectra: cosine similarity to the nearest training spectrum.',
                    'Likely range = split-conformal interval at the nominal level shown; "range held in testing" is the empirical fraction of TEST chemicals in the same novelty band whose measured value fell inside their range (n given).',
                    'Error as % of naive: RMSE of the model divided by RMSE of always predicting the training mean, on held-out test chemicals.',
                    'Physically undefined properties (W-SPACE rules, derived from first principles following BB\'s expert note) are refused, not predicted.',
                    'EPI Suite values come from the EPI Suite web API (needs internet), identity-checked against the structure sent; EPI\'s training data overlap the measured data, so its test errors are optimistic.',
                    'Quantum-chemistry descriptors: RDKit ETKDGv3 (seed 0xF00D) + MMFF94, then AIMNet2 (wB97M-D3) relaxation to 0.01 eV/Å on CPU. CPU vs GPU training table: median |ΔE| 2 meV; descriptors drift for molecules with 4 or more rotatable bonds (labelled "approximate").'],
             files_note=f'Labels: {LAB}. Registry: {B.REGISTRY}. EPI comparator: <TEAM_ROOT>/agents/work/W-TOOL/epi_comparator_v3.parquet.')
try:
    rc = pd.read_parquet('<TEAM_ROOT>/results/v2/labels_tox_v2_receptor.parquet')
    build['base_rates'] = {ep: dict(rate=float(g.activity_binary.mean()), n=int(len(g)), source='labels_tox_v2_receptor.parquet (all rows, OPERA consensus calls)')
                           for ep, g in rc.groupby('endpoint')}
except Exception as e:
    build['base_rates'] = {}; print('base rates unavailable', e)
DATA = dict(build=build, endpoints=endpoints, examples=examples, spec_examples=spec_examples, good=good, models=models_pub)


def clean(o):
    if isinstance(o, float):
        return o if o == o and abs(o) != float('inf') else None
    if isinstance(o, dict):
        return {k: clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    return o


js = ''.join(open(os.path.join(D, 'v3', f)).read() + '\n' for f in ['a_core.js', 'b_render.js', 'c_ui.js', 'd_init.js'])
data_js = 'window.__DATA__=' + json.dumps(clean(DATA), default=str, allow_nan=False).replace('</', '<\\/') + ';'
html = open(os.path.join(D, 'v3_head.html')).read() + '<script>' + data_js + '</script>\n<script>\n' + js + '</script>\n</body></html>\n'
assert 'http://' not in js.replace('http://127.0.0.1', '') and 'https://' not in js, 'no remote URLs in the page'
open(a.out, 'w').write(html)
json.dump(clean(DATA), open(os.path.join(D, 'data_v3.json'), 'w'), default=str, indent=0)
print('wrote', a.out, f'{len(html)/1e6:.2f} MB', len(examples), 'examples', len(spec_examples), 'spectrum examples')
