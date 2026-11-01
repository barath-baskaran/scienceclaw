#!/usr/bin/env python
"""W-TOOL backend: runs the swarm's FROZEN models (via <TEAM_ROOT>/swarm/seed/predict.py internals)
for the dashboard. No model logic lives here; this file only orchestrates, times and reports.

Usage
  python wtool_backend.py --smiles "CCOc1ccccc1"                       # one structure
  python wtool_backend.py --smiles "CCO" --spectrum spec.json          # structure + MS/MS
  python wtool_backend.py --spectrum spec.json                         # spectrum-only (no structure)
  python wtool_backend.py --file batch.csv [--smiles-col smiles]       # batch (.csv/.tsv/.smi/.txt)
  python wtool_backend.py ... --out preds.json [--epi-live]            # load preds.json in the dashboard

Output schema 'wtool_predictions/v2' (one record per input) -- see README.md.

Honesty rules implemented here
 * an endpoint with no frozen model is reported status='no_model' (the card says "not yet available")
 * coverage is never shown without its source: empirical coverage per familiarity bin is looked up
   in the producing agent's results.json (or model.json 'coverage_by_bin'); missing -> null + reason
 * if a spectrum is supplied, the structure-only prediction is ALSO computed and the difference is
   reported; |delta| < 5% of the interval width -> card states "the spectrum changed nothing"
 * EPI Suite comparator: estimated values only, and only if EPI's returned structure has the same
   InChIKey (or skeleton) as the input
"""
from __future__ import annotations

import argparse, datetime, glob, hashlib, importlib.util, json, math, os, sys, time, traceback
import urllib.parse, urllib.request

os.environ.setdefault('AIMNET2_CKPT', '<TEAM_ROOT>/models/aimnet/aimnet2_wb97m_d3_0.pt')  # on disk since run 3
SEED = '<TEAM_ROOT>/agents/work/LEAD/seed_v2_1' if os.path.isfile('<TEAM_ROOT>/agents/work/LEAD/seed_v2_1/predict.py') else '<TEAM_ROOT>/swarm/seed'
WORK = '<TEAM_ROOT>/agents/work'
HERE = os.path.dirname(os.path.abspath(__file__))
REGISTRY = os.path.join(HERE, 'models_registry.json')
sys.path.insert(0, SEED)
sys.path.insert(0, os.path.dirname(HERE))
import predict as P  # frozen interface

from rdkit import Chem, RDLogger
RDLogger.DisableLog('rdApp.*')

FATE = ['logkow', 'water_solubility', 'vapor_pressure', 'henry', 'melting_point', 'boiling_point',
        'koc', 'bcf', 'logkoa', 'koh_gas', 'pka_acidic', 'pka_basic']
SPECTRAL_BLOCKS = {'mz', 'nl', 'nlx', 'int', 'meta', 'spectra', 'spectra_all'}
PHYSICS_BLOCKS = {'physics', 'phys', 'aimnet2', 'alchemi'}
NOTHING_FRAC = 0.05  # spectrum effect below 5% of interval width => "changed nothing"


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def block_group(b: str) -> str:
    b = (b or '').lower()
    if b in SPECTRAL_BLOCKS or b.startswith('spec'):
        return 'spectra'
    if b in PHYSICS_BLOCKS or b.startswith('phys'):
        return 'physics'
    return 'structure'


# ------------------------------------------------------------------ model discovery
def discover_models(include_mock=False):
    """Registry entries first (explicit), then any */frozen*/**/model.json under the work tree."""
    dirs = []
    excl = set()
    if os.path.isfile(REGISTRY):
        excl = set(os.path.realpath(x) for x in json.load(open(REGISTRY)).get('exclude', []))
        for e in json.load(open(REGISTRY)).get('models', []):
            dirs.append(e['model_dir'] if isinstance(e, dict) else e)
    n_explicit = len(dirs)
    pats = [f'{WORK}/*/frozen*/model.json', f'{WORK}/*/frozen*/*/model.json',
            f'{WORK}/*/frozen*/*/*/model.json', f'{WORK}/*/models/*/model.json', '<TEAM_ROOT>/models/*/model.json']
    if os.path.isfile(REGISTRY) and json.load(open(REGISTRY)).get('no_autodiscovery'):
        pats = []   # run 3: only the explicitly frozen models in the registry are used
    for p in pats:
        dirs += [os.path.dirname(x) for x in sorted(glob.glob(p))]
    out, seen = [], set()
    explicit = set(os.path.realpath(x) for x in dirs[:n_explicit])
    for d in dirs:
        d = os.path.realpath(d)
        skip = any(w in os.path.basename(d).lower() for w in ('prelim', 'old', 'scratch', 'tmp'))
        has_api = os.path.isfile(f'{d}/predict_spectrum.py') or os.path.isfile(f'{d}/rat_oral_ld50_meta.json')
        if d in seen or d in excl or not (os.path.isfile(f'{d}/model.json') or has_api) or (skip and d not in explicit):
            continue
        seen.add(d)
        try:
            meta = json.load(open(f'{d}/model.json')) if os.path.isfile(f'{d}/model.json') else {}
        except Exception as e:
            out.append(dict(model_dir=d, error=f'model.json unreadable: {e!r}'[:200])); continue
        if meta.get('mock') and not include_mock:
            continue
        if os.path.isfile(f'{d}/rat_oral_ld50_meta.json'):
            out.append(dict(model_dir=d, model_id='wtox_' + os.path.basename(d), endpoints=['rat_oral_ld50', 'er_potency', 'er_active', 'ar_potency', 'ar_active'],
                            feature_blocks=['struct'], kind='tox_api', owner='W-TOX', meta=meta))
            continue
        if os.path.isfile(f'{d}/predict_spectrum.py'):
            out.append(dict(model_dir=d, model_id='wspectra_' + os.path.basename(d), endpoints=[], feature_blocks=['spectrum'], kind='spectra_api',
                            owner=d.split('/')[5] if d.startswith(WORK) else '', meta=meta))
            continue
        api_file = next((f for f in ('fatev5.py', 'predict.py') if os.path.isfile(f'{d}/{f}') and 'def predict(' in open(f'{d}/{f}').read()), None)
        if api_file and (meta.get('version') == 'v5' or 'impl' not in meta):
            eps = list((meta.get('endpoints') or {}).keys()) if isinstance(meta.get('endpoints'), dict) else meta.get('endpoints', [])
            out.append(dict(model_dir=d, model_id=meta.get('model_id', 'wmodel_' + os.path.basename(d)), endpoints=eps,
                            feature_blocks=['struct', 'physics'], kind='api', api_file=api_file, owner=d.split('/')[5] if d.startswith(WORK) else '', meta=meta))
            continue
        out.append(dict(model_dir=d, model_id=meta.get('model_id', os.path.basename(d)),
                        endpoints=meta.get('endpoints', []), feature_blocks=meta.get('feature_blocks', []),
                        kind=meta.get('kind') or ('spectra_only' if 'struct' not in meta.get('feature_blocks', ['struct']) else 'structure'),
                        owner=d.split('/')[5] if d.startswith(WORK) else '', meta=meta))
    return out


_MODEL_CACHE = {}


def load_model(d):
    if d not in _MODEL_CACHE:
        _MODEL_CACHE[d] = P._load_model(d)
    return _MODEL_CACHE[d]


# ------------------------------------------------------------------ results.json lookup (coverage)
_RES = None


def all_results():
    global _RES
    if _RES is None:
        _RES = []
        for f in sorted(glob.glob(f'{WORK}/*/results.json')):
            try:
                j = json.load(open(f))
                for r in j.get('results', []):
                    r = dict(r); r['_file'] = f; _RES.append(r)
            except Exception:
                pass
    return _RES


def coverage_for(model_dir, model_id, meta, endpoint, fbin, out=None):
    """Empirical coverage + median width of the producing model in the familiarity bin."""
    ec = (out or {}).get('empirical_coverage_test_bin')
    if isinstance(ec, dict) and ec.get('coverage') is not None:
        return dict(empirical_coverage=ec['coverage'], median_width=ec.get('median_interval_width'), n=ec.get('n'),
                    source=f'{model_dir} predict_one empirical_coverage_test_bin',
                    scope=f'test split, bin {fbin}, variant {out.get("variant_used")}')
    cb = (meta.get('coverage_by_bin') or {}).get(endpoint, {}).get(fbin)
    if isinstance(cb, dict) and cb.get('coverage') is not None:
        return dict(empirical_coverage=cb.get('coverage'), median_width=cb.get('median_interval_width'),
                    n=cb.get('n'), source=f'{model_dir}/model.json coverage_by_bin', scope=f'test, bin {fbin}')
    for r in all_results():
        if r.get('endpoint') != endpoint:
            continue
        if not (os.path.realpath(r.get('model_dir', '') or '-') == model_dir or r.get('model_id') == model_id):
            continue
        b = (r.get('by_familiarity') or {}).get(fbin) or {}
        if b.get('coverage') is not None:
            return dict(empirical_coverage=b['coverage'], median_width=b.get('median_interval_width'),
                        n=b.get('n'), interval_level=b.get('interval_level'),
                        source=r['_file'], scope=f'test, bin {fbin}, variant {r.get("model_variant")}')
    return dict(empirical_coverage=None, median_width=None, n=None, source=None,
                scope='no empirical coverage found for this model/endpoint/bin in model.json or any results.json')


# ------------------------------------------------------------------ physics (any-structure path)
def find_compute_physics():
    for p in [f'{WORK}/W-PHYSICS/compute_physics.py', f'{WORK}/W-PHYSICS/physics_features.py']:
        if os.path.isfile(p):
            spec = importlib.util.spec_from_file_location('wtool_compute_physics', p)
            m = importlib.util.module_from_spec(spec)
            try:
                spec.loader.exec_module(m)
            except Exception as e:
                return None, f'{p} failed to import: {e!r}'[:300]
            fn = getattr(m, 'compute_physics', None)
            if fn:
                return fn, p
    return None, 'W-PHYSICS compute_physics not found (not yet available)'


PHYS_TIMEOUT_S = 240
_PHYS = None
_PHYS_LAST = {}  # raw compute_physics dict of the current structure (consumed by models that accept it)


def run_physics(smiles):
    """Time W-PHYSICS compute_physics for this SMILES. The model may compute/consume physics
    itself inside predict_one; this call exists so the user sees the cost and the status."""
    global _PHYS
    if _PHYS is None:
        _PHYS = find_compute_physics()
    fn, src = _PHYS
    if fn is None:
        return dict(status='not_available', detail=src, seconds=None)
    t = time.time()
    import concurrent.futures as cf
    try:
        ex = cf.ThreadPoolExecutor(max_workers=1)
        fut = ex.submit(fn, smiles)
        try:
            r = fut.result(timeout=PHYS_TIMEOUT_S)
        except cf.TimeoutError:
            ex.shutdown(wait=False)
            _PHYS_LAST.clear()
            return dict(status='failed', detail=f'AIMNet2 relaxation did not finish within {PHYS_TIMEOUT_S} s; physics not used', seconds=round(time.time() - t, 2))
        ex.shutdown(wait=False)
        dt = time.time() - t
        r = r if isinstance(r, dict) else {}
        ok = bool(r.get('physics_ok', True)) and not r.get('error') and r.get('converged', True) is not False
        _PHYS_LAST.clear()
        if ok and r.get('source') != 'gpu_table':
            _PHYS_LAST.update(r)   # computed now -> handed to models that accept it; table hits are looked up by the model itself
        from rdkit.Chem import rdMolDescriptors
        m = Chem.MolFromSmiles(smiles)
        nrot = rdMolDescriptors.CalcNumRotatableBonds(m) if m is not None else None
        notes = []
        if ok and r.get('source') == 'cpu_relax' and nrot is not None and nrot >= 4:
            notes.append(f'physics approximate: flexible molecule ({nrot} rotatable bonds), dipole/shape descriptors depend on the conformer found '
                         '(OPS-2 CPU-vs-GPU parity: 12/18 molecules with >=4 rotatable bonds differed by >10% of training SD on these descriptors)')
        reason = r.get('error') or ('relaxation did not converge' if r.get('converged') is False else None)
        st = 'ok' if ok else ('unavailable_new_structure' if 'checkpoint' in str(reason) else 'failed')
        return dict(status=st, detail=(reason or src), seconds=round(dt, 2), n_features=sum(isinstance(v, float) for v in r.values()),
                    converged=r.get('converged'), source=r.get('source'), fmax_eV_A=r.get('fmax_eV_A'),
                    relax_wall_s=r.get('wall_s'), n_steps=r.get('n_steps'), n_rotatable=nrot, notes=notes,
                    parity='CPU vs GPU table: median |dE| 2 meV, 40/40 converged (W-PHYSICS parity_cpu_gpu_v1.json); descriptors within 3% of training SD for <=3 rotatable bonds (OPS-2 cpu_parity_desc_summary.md)')
    except Exception as e:
        _PHYS_LAST.clear()
        return dict(status='failed', detail=f'{e!r}'[:300], seconds=round(time.time() - t, 2))


# ------------------------------------------------------------------ EPI comparator
EPI_CACHES = [f'{WORK}/W-TOOL/epi_cache_wtool', f'{WORK}/W-LADDER/epi_cache_ladder', '<TEAM_ROOT>/results/epi_cache']


def epi_lookup(ik, smiles, live=False):
    sys.path.insert(0, f'{WORK}/W-TOOL')
    from epi_extract import extract, EPI_MODULE, EPI_UNITS
    ik_of = lambda x: (Chem.MolToInchiKey(Chem.MolFromSmiles(x)) if x and Chem.MolFromSmiles(x) is not None else None)
    path = next((f'{c}/{ik}.json' for c in EPI_CACHES if os.path.exists(f'{c}/{ik}.json')), None)
    fetched = False
    if path is None and live:
        from epi_rate import wait_turn
        url = 'https://episuite.dev/api/submit?smiles=' + urllib.parse.quote(smiles, safe='')
        wait_turn()
        try:
            with urllib.request.urlopen(url, timeout=45) as r:
                raw = r.read()
            json.loads(raw)
            path = f'{EPI_CACHES[0]}/{ik}.json'
            open(path, 'wb').write(raw)
            json.dump(dict(inchikey=ik, sent_smiles=smiles, request_url=url, retrieved_utc=now(),
                           raw_sha256=hashlib.sha256(raw).hexdigest(), status='ok'),
                      open(path.replace('.json', '.meta.json'), 'w'), indent=1)
            fetched = True
        except Exception as e:
            return dict(status='fetch_failed', detail='EPI Suite web API not reachable (offline?) - ' + repr(e)[:160])
    if path is None:
        return dict(status='not_fetched', detail='no cached EPI result; rerun with --epi-live (1 request/s)')
    j = json.load(open(path))
    rs = (j.get('chemicalProperties') or {}).get('smiles')
    rik = ik_of(rs) if rs else None
    match = rik == ik or (rik is not None and rik[:14] == ik[:14])
    if not match:
        return dict(status='identity_mismatch', detail=f'EPI returned {rs} ({rik}) for input {ik}', cache=path)
    vals = {}
    for ep, (v, has_exp) in extract(j).items():
        vals[ep] = dict(value=v, units=EPI_UNITS[ep], module=EPI_MODULE[ep], epi_has_experimental=has_exp)
    return dict(status='ok', fetched_now=fetched, cache=path, returned_smiles=rs,
                stereo_exact=(rik == ik), values=vals,
                note='EPI estimated values only; EPI training sets overlap CompTox data, so its errors on known compounds are optimistic')


# ------------------------------------------------------------------ one prediction
def _top_features(out, k=3):
    tf = out.get('top_features') or out.get('drivers') or []
    rows = []
    for t in tf:
        if isinstance(t, dict):
            rows.append(dict(name=str(t.get('name')), block=block_group(t.get('block', '')),
                             shap=float(t.get('shap', t.get('contribution', 0.0)) or 0.0)))
        elif isinstance(t, (list, tuple)) and len(t) >= 2:
            rows.append(dict(name=str(t[0]), shap=float(t[1]), block=block_group(t[2] if len(t) > 2 else '')))
    rows.sort(key=lambda r: -abs(r['shap']))
    return rows[:k]


def _group_attr(attr):
    g = {'structure': 0.0, 'physics': 0.0, 'spectra': 0.0}
    for b, v in (attr or {}).items():
        g[block_group(b)] += abs(float(v))
    tot = sum(g.values())
    return {k: (v / tot if tot else None) for k, v in g.items()}


def hazard_band(meta, endpoint, out, lo, hi):
    if out.get('band') is not None:
        br = out.get('band_range_from_interval') or out.get('band_range')
        if isinstance(br, dict):
            br = [br.get('lo', br.get('low')), br.get('hi', br.get('high'))]
        return dict(band=out['band'], band_probs=out.get('band_probs'), band_range=br,
                    band_scheme=out.get('band_scheme'), label_caveat=out.get('label_caveat') or meta.get('label_caveat'),
                    source='model')
    edges = (meta.get('band_edges') or {}).get(endpoint)
    if not edges:
        return None
    # edges: list of {"name":..,"upper":x} ascending in model units (value < upper -> band)
    def which(x):
        for e in edges:
            if e.get('upper') is None or x < e['upper']:
                return e['name']
        return edges[-1]['name']
    return dict(band=which(out['value']), band_range=[which(lo), which(hi)], source='model.json band_edges',
                edges=edges)


def ladder_contrib(model, endpoint, smiles, k=5):
    """W-LADDER's predict_one returns no per-prediction attributions. Rebuild its exact feature vector
    (same code path as ladder_model.py) and ask the frozen LightGBM booster for pred_contrib (TreeSHAP)."""
    import numpy as np
    from rdkit.Chem import Descriptors
    mod = sys.modules[type(model).__module__]
    mol = Chem.MolFromSmiles(smiles)
    x = list(mod._cnt.GetCountFingerprintAsNumPy(mol).astype(np.float64))
    for n, f in Descriptors.descList:
        try: x.append(float(f(mol)))
        except Exception: x.append(np.nan)
    x = np.array(x, dtype=np.float32).astype(np.float64); x[~np.isfinite(x)] = np.nan
    b = model._load(endpoint)
    c = b.predict(x[None, :], pred_contrib=True)[0][:-1]
    names = model.meta.get('feature_columns') or b.feature_name()
    idx = np.argsort(-np.abs(c))[:k]
    return [dict(name=str(names[i]) if i < len(names) else f'f{i}', block='struct', shap=float(c[i])) for i in idx]


_POOLED = None


def pooled_vector(skeleton, cols):
    global _POOLED
    import pandas as pd
    if _POOLED is None:
        _POOLED = pd.read_parquet('<TEAM_ROOT>/results/v2/spectra_pooled_v2.parquet').set_index('skeleton')
    if skeleton not in _POOLED.index or any(c not in _POOLED.columns for c in cols):
        return None
    return _POOLED.loc[skeleton, cols].astype(float).values.ravel()[:len(cols)]


def run_one(m, endpoint, smiles, spectrum, phys=None):
    model = load_model(m['model_dir'])
    flags = []
    if isinstance(spectrum, dict) and spectrum.get('pooled_from_v2'):
        # measured AMOS spectra of this compound, pooled by the swarm (spectra_pooled_v2 row for the
        # skeleton); handed over in the producing model's own spectra_columns layout
        feats = P._featurize(smiles, None, flags)
        cols = m['meta'].get('spectra_columns') or []
        if isinstance(cols, str):
            cols = []
        vec = pooled_vector(spectrum['pooled_from_v2'], cols) if cols else None
        if vec is None:
            flags.append('pooled_spectrum_unavailable_for_this_model')
        else:
            feats['mz'] = vec
    else:
        feats = P._featurize(smiles, spectrum, flags)
    # seed _featurize drops the measured metadata (polarity, adduct, precursor m/z); spectra-only
    # models (W-UNKNOWN) need it as features['meta'] (dict) - measurement-derived, not structure-derived
    if spectrum is not None and isinstance(spectrum, dict) and isinstance(spectrum.get('meta'), dict) \
            and m['kind'] == 'spectra_only':
        feats['meta'] = spectrum['meta']
    if smiles and phys and m['meta'].get('accepts_computed_physics'):
        feats['physics'] = dict(phys)
    elif smiles and phys:
        flags.append('physics_computed_but_this_model_cannot_use_it_for_new_structures')
    blocks = [b for b in P.FEATURE_BLOCKS if feats.get(b) is not None]
    t = time.time()
    out = model.predict_one(endpoint, feats, blocks)
    dt = time.time() - t
    if not out.get('top_features') and smiles and hasattr(model, '_load') and hasattr(sys.modules[type(model).__module__], '_cnt'):
        try:
            out = dict(out, top_features=ladder_contrib(model, endpoint, smiles),
                       top_features_source='TreeSHAP (LightGBM pred_contrib) computed by W-TOOL on the frozen booster')
        except Exception as e:
            out = dict(out, top_features_error=repr(e)[:200])
    fam = float(out.get('familiarity', 0.0))
    lo, hi = sorted(float(x) for x in out['interval'])
    return dict(out=out, value=float(out['value']), lo=lo, hi=hi, fam=fam, flags=flags + list(out.get('flags', [])),
                blocks=blocks, seconds=round(dt, 3))


def input_card(mol):
    """What the user typed, as the tool understood it: formula, MW, a 2D depiction (SVG, RDKit), fragments."""
    from rdkit.Chem import Descriptors, rdMolDescriptors
    import depict  # own SVG depiction: RDKit's rdMolDraw2D needs libXrender, absent on the VM
    out = dict(formula=rdMolDescriptors.CalcMolFormula(mol), mw=round(Descriptors.MolWt(mol), 3),
               n_fragments=len(Chem.GetMolFrags(mol)), formal_charge=Chem.GetFormalCharge(mol))
    try:
        out['svg'] = depict.svg(mol)
    except Exception as e:
        out['svg_error'] = repr(e)[:120]
    return out


_API = {}


def api_predict(m, smiles, phys):
    """Models exposing predict(smiles, physics=None, allow_struct_only=False) (W-MODEL frozen_v4+)."""
    d = m['model_dir']
    if d not in _API:
        spec = importlib.util.spec_from_file_location('api_' + hashlib.md5(d.encode()).hexdigest()[:8], f"{d}/{m.get('api_file', 'predict.py')}")
        mod = importlib.util.module_from_spec(spec); sys.path.insert(0, os.path.dirname(d)); spec.loader.exec_module(mod)
        _API[d] = mod
    mod = _API[d]
    flags = []
    t = time.time()
    if phys:
        try:
            out = mod.predict(smiles, physics=phys)
            flags.append('physics_at_inference')
        except Exception as e:
            flags.append('physics_rejected_by_model: ' + repr(e)[:300])
            out = mod.predict(smiles, allow_struct_only=True)
    else:
        try:
            out = mod.predict(smiles)            # labelled compound: physics from the model's own table
        except Exception:
            out = mod.predict(smiles, allow_struct_only=True)
            flags.append('no_physics')
    if any('no_physics' in f or 'physics_rejected' in f for f in flags) or not phys:
        # run 4 (T-020): the model's own flag says "at the caller's explicit request"; here the fallback was forced
        # because physics could not be computed or was rejected, so say that instead
        why = 'quantum-chemistry descriptors could not be computed for this structure' if not phys else 'quantum-chemistry descriptors were rejected by the model'
        out['flags'] = [str(x).replace("structure-only model used at the caller's explicit request", 'structure-only model used because ' + why)
                        for x in (out.get('flags') or [])]
    return out, flags, round(time.time() - t, 3)


def api_cards(m, out, flags, secs):
    """Map an API model's output (W-MODEL frozen_v4 / frozen_v5 schema) onto the dashboard card schema."""
    stats = card_stats()
    cards = {}
    nn = float(out.get('nn_sim_train', 0.0)); b = out.get('nn_bin')
    gflags = list(flags) + [str(x) for x in (out.get('flags') or [])]
    for ep, e in out['endpoints'].items():
        var = e.get('model_variant') or out.get('model_variant')
        var_name = {'S': 'struct_only', 'SP': 'struct_physics'}.get(var, var)
        if e.get('value') is None:
            cards[ep] = dict(status='undefined', kind='physically_undefined', reason=e.get('definedness_reason') or e.get('note'),
                             rule_source=m['model_id'] + ' definedness (W-SPACE rules)', model_id=m['model_id'])
            continue
        st = (stats.get(m['model_dir'], {}).get(var_name, {}).get(ep, {}) or stats.get(m['model_dir'], {}).get(var, {}).get(ep, {}) or {})
        sb = (st.get('bins') or {}).get(b) or {}
        nn_ep = e.get('nn_sim_endpoint_train')
        fam = nn   # GLOBAL nn_sim_train: the coverage/skill bins are defined on it (W-MODEL review); endpoint similarity shown in details
        dom = 'out' if fam < 0.3 else ('edge' if fam < 0.5 else 'in')
        if any('ELEMENT_NOT_IN_TRAINING' in str(x) for x in (e.get('flags') or [])):
            dom = 'out'
        fl = gflags + [str(x) for x in (e.get('flags') or [])] + ([] if var_name == 'struct_physics' else ['no_physics'])
        tf = [dict(name=a['feature'], block=('physics' if a.get('block') == 'physics' else 'structure'), shap=a['shap'],
                   note=a.get('meaning') or a.get('note', '')) for a in e.get('attribution_top', [])]
        sh = e.get('attribution_block_shares')
        if sh:
            tot = sum(sh.values()) or 1.0
            ab = dict(structure=sum(v for k, v in sh.items() if k != 'physics') / tot, physics=sh.get('physics', 0.0) / tot, spectra=0.0)
        else:
            ps = float(e.get('physics_shap_share') or 0.0); ab = dict(structure=1 - ps, physics=ps, spectra=0.0)
        epi = e.get('epi_comparator')
        cards[ep] = dict(status='ok', model_id=m['model_id'], model_dir=m['model_dir'], owner=m['owner'], value=e['value'], units=e['units'],
                         interval=sorted(e['interval']), interval_level=float(e.get('nominal_coverage', 0.9)), familiarity=fam, familiarity_bin=b,
                         familiarity_kind='tanimoto_ecfp4', domain=dom, flags=list(dict.fromkeys(fl)),
                         blocks_used=['struct'] + (['physics'] if var_name == 'struct_physics' else []),
                         seconds=secs, variant_used=var_name, domain_flag_model=e.get('domain_flag') or out.get('domain_flag'), physics_source=out.get('physics_source'),
                         interval_method=e.get('interval_method'), familiarity_endpoint=nn_ep, measured_in_training_set=e.get('measured_in_training_set'),
                         coverage=dict(empirical_coverage=e.get('empirical_coverage_test_this_bin'), n=e.get('n_test_this_bin') or sb.get('n'), median_width=sb.get('median_width'),
                                       source=f"{m['model_dir']}/model.json empirical_coverage_test_by_bin",
                                       scope=f'test split, nn_sim_train bin {b}, variant {var_name}'),
                         attribution_blocks=ab, top_features=tf,
                         top_features_note=e.get('attribution_note') or 'SHAP (LightGBM pred_contrib) from the model',
                         skill_naive=dict(overall=st.get('all'), this_bin=sb or None, leak_free=st.get('leak_free'), source=st.get('source'), variant=var_name))
    return cards


def tox_api_cards(m, smiles):
    """W-TOX r3 model_frozen_v3 predict(smiles) -> cards. Label provenance is shown verbatim (W-TOX R4)."""
    d = m['model_dir']
    if d not in _API:
        r3 = os.path.dirname(d)
        for p in (r3, d):
            if p not in sys.path:
                sys.path.insert(0, p)
        spec = importlib.util.spec_from_file_location('wtox_api', f'{r3}/model_frozen_v3_predict.py')
        mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); _API[d] = mod
    t = time.time(); o = _API[d].predict(smiles); secs = round(time.time() - t, 3)
    def perf(ep, b):
        try:
            mt = json.load(open(f'{d}/{ep}_meta.json'))['measured_test_performance']
            return (mt.get('by_nn_sim_bin') or {}).get(b) or {}, mt.get('overall') or {}
        except Exception:
            return {}, {}
    cards = {}
    for ep, e in o['endpoints'].items():
        fam = e.get('familiarity_nn_sim_train'); dom = 'out' if (fam or 0) < 0.3 else ('edge' if fam < 0.5 else 'in')
        if e.get('status') != 'ok':
            cards[ep] = dict(status='undefined', kind='physically_undefined' if e.get('definedness') == 'undefined' else 'not_assessed',
                             headline='Withheld for this compound class', reason=e.get('reason') or e.get('definedness_reason'),
                             rule_source='W-TOX model_frozen_v3 (definedness / class)', model_id=m['model_id'])
            continue
        base = dict(status='ok', model_id=m['model_id'], model_dir=d, owner='W-TOX', units=e.get('units'), familiarity=fam, familiarity_bin=e.get('familiarity_bin'),
                    familiarity_kind='tanimoto_ecfp4', domain=dom, flags=[], blocks_used=['struct'], seconds=secs, label_provenance=e.get('label_provenance'),
                    compound_class=o.get('compound_class'), definedness_reason=e.get('definedness_reason'), attribution_blocks=dict(structure=1.0, physics=0.0, spectra=0.0),
                    top_features=[], top_features_note='hazard model: per-prediction attributions not returned')
        pb, po = perf(ep, e.get('familiarity_bin'))
        if 'probability' in e:
            p = float(e['probability']); thr = e.get('threshold')
            base.update(kind='classifier', value=p, interval=None, probability=p, threshold=thr, call=('active' if thr is not None and p >= thr else 'inactive'),
                        base_rate=e.get('base_rate_test_this_bin'), pr_auc=e.get('pr_auc_this_bin'), note=e.get('note'),
                        coverage=dict(empirical_coverage=None, scope='classifier: no interval'))
        else:
            base.update(value=e['value'], interval=sorted(e['interval']), interval_level=e.get('nominal_coverage', 0.9),
                        coverage=dict(empirical_coverage=e.get('empirical_coverage_this_bin'), n=e.get('n_test_this_bin') or pb.get('n'), scope=f"test, familiarity bin {e.get('familiarity_bin')}",
                                      source=f'{d}/*_meta.json'),
                        skill_naive=dict(this_bin=dict(rmse_pct_naive=e.get('pct_of_naive_this_bin'), n=e.get('n_test_this_bin') or pb.get('n')),
                                         overall=dict(rmse_pct_naive=po.get('pct_of_naive'), n=po.get('n')), source=f'{d}/{ep}_meta.json measured_test_performance'))
        cards[ep] = base
    return cards


def _spec_ntest(d, block, ep):
    try:
        return json.load(open(f'{d}/manifest.json'))['blocks'][block]['endpoints'][ep]['n_test']
    except Exception:
        return None


def spectra_api_cards(m, spectrum, rec):
    """W-SPECTRA spectrum_only_v31 predict(input) -> dashboard cards. Required metadata is enforced by the model
    (SpectrumInputError, plain language); nothing is defaulted here."""
    d = m['model_dir']
    if d not in _API:
        spec = importlib.util.spec_from_file_location('wspectra_api', f'{d}/predict_spectrum.py')
        mod = importlib.util.module_from_spec(spec); sys.path.insert(0, d); sys.path.insert(0, os.path.dirname(d)); spec.loader.exec_module(mod)
        _API[d] = mod
    t = time.time()
    o = _API[d].predict(dict(mz=spectrum.get('mz'), intensity=spectrum.get('intensity'), meta=spectrum.get('meta') or {}))
    secs = round(time.time() - t, 3)
    dm = o.get('domain') or {}
    rec['spectrum_model'] = dict(block=o.get('block'), warnings=o.get('warnings'), domain=dm)
    cards = {}
    for ep, e in (o.get('endpoints') or {}).items():
        lo, hi = sorted([e['lo'], e['hi']])
        mo = e.get('mass_only')
        cards[ep] = dict(status='ok', model_id=m['model_id'], model_dir=d, owner=m['owner'], value=e['value'], units=e['units'], interval=[lo, hi],
                         interval_level=e.get('nominal_coverage', 0.9), familiarity=dm.get('max_cosine_to_train'), familiarity_kind='spectral_cosine',
                         domain='na', domain_note=dm.get('verdict'), flags=list(o.get('warnings') or []), blocks_used=['spectrum'], seconds=secs,
                         coverage=dict(empirical_coverage=e.get('empirical_coverage_test'), n=_spec_ntest(d, o.get('block'), ep), scope='all spectrum-only test compounds of this ion block (not per similarity bin)',
                                       source=f'{d}/manifest.json'),
                         attribution_blocks=dict(structure=0.0, physics=0.0, spectra=1.0), top_features=[],
                         top_features_note='spectrum-only model: per-prediction attributions not returned',
                         no_skill=not e.get('skill', True),
                         skill_naive=dict(overall=dict(rmse_pct_naive=e.get('test_pct_naive'), n=None, ci95=e.get('test_pct_naive_ci95')), source=f'{d}/manifest.json'),
                         structure_same_compounds_pct_naive=e.get('structure_same_compounds_pct_naive'),
                         mass_only=mo, n_train=e.get('n_train_compounds'))
    return cards


_CS = None


def card_stats():
    global _CS
    if _CS is None:
        p = os.path.join(HERE, 'card_stats.json')
        _CS = json.load(open(p)) if os.path.exists(p) else {}
    return _CS


def domain_flag(fam, flags):
    if any('out_of_domain' in f for f in flags) or fam < 0.3:
        return 'out'
    if fam < 0.5:
        return 'edge'
    return 'in'


def predict_record(smiles=None, spectrum=None, models=None, epi_live=False, progress=None, physics=True):
    models = models if models is not None else discover_models()
    rec = dict(input=dict(smiles=smiles, has_spectrum=spectrum is not None), created_utc=now(),
               stages=[], endpoints={}, errors=[])
    say = progress or (lambda s: None)
    ik = None
    if smiles:
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            rec['errors'].append('RDKit could not parse SMILES'); return rec
        ik = Chem.MolToInchiKey(mol)
        rec['input'].update(inchikey=ik, canonical_smiles=Chem.MolToSmiles(mol), n_heavy=mol.GetNumHeavyAtoms())
        rec['input'].update(input_card(mol))
        # W-SPACE species(): strip counter-ions / neutralise. Models, physics and EPI run on the parent species;
        # definedness is judged on the structure as entered (postproc).
        try:
            if '<TEAM_ROOT>/agents/work/W-SPACE' not in sys.path:
                sys.path.insert(0, '<TEAM_ROOT>/agents/work/W-SPACE')
            from domain_rules import species as _species
            sp = _species(smiles)
            rec['species'] = sp
            plain = {'neutralisable': 'neutral compound (or a salt of one)', 'permanent_cation': 'permanent cation (no neutral form)',
                     'permanent_anion': 'permanent anion (no neutral form)', 'permanent_zwitterion': 'permanent zwitterion',
                     'metal_containing_not_assessed': 'contains a metal: not assessed', 'unparseable': 'could not be assessed'}
            sp['plain'] = plain.get(sp.get('species_class'), sp.get('species_class'))
            ps = sp.get('parent_smiles')
            if ps and Chem.MolFromSmiles(ps) is not None and Chem.MolToSmiles(Chem.MolFromSmiles(ps)) != Chem.MolToSmiles(mol):
                rec['parent_note'] = (f'Estimates are for {ps} (counter-ion(s) {", ".join(sp.get("removed_fragments") or []) or "none"} removed'
                                      + (', neutralised' if sp.get('species_class') == 'neutralisable' else '') + '). The salt as drawn can differ, '
                                      'especially in melting point and water solubility.')
                smiles = ps
                mol = Chem.MolFromSmiles(ps)
                ik = Chem.MolToInchiKey(mol)
                rec['input']['model_smiles'] = ps
        except Exception as e:
            rec['errors'].append('W-SPACE species() unavailable, structure used as entered: ' + repr(e)[:150])
        if physics:
            say('physics: ETKDG+MMFF -> AIMNet2 relaxation on CPU via W-PHYSICS compute_physics (about 30-90 s)')
            rec['physics'] = run_physics(smiles)
        else:
            _PHYS_LAST.clear()
            rec['physics'] = dict(status='skipped_by_user', detail='physics not requested (fast mode); models use their structure-only variant', seconds=0)
        rec['stages'].append(dict(stage='physics', **rec['physics']))
    # structure given -> structure models only (they consume the spectrum themselves if they can);
    # spectrum only -> spectra-only models only. A spectra-only model is never run without a spectrum.
    if smiles:
        usable = [m for m in models if 'error' not in m and m['kind'] != 'spectra_only']
    else:
        usable = [m for m in models if 'error' not in m and m['kind'] == 'spectra_only'] if spectrum is not None else []
    if spectrum is not None and not smiles:
        usable = [m for m in models if m.get('kind') == 'spectra_api'] or usable
    for m in usable:
        if m['kind'] == 'tox_api':
            if not smiles:
                continue
            say(f'{m["model_id"]}: hazard endpoints')
            try:
                for ep, card in tox_api_cards(m, smiles).items():
                    rec['endpoints'][ep] = card
            except Exception as e:
                rec['errors'].append(f'{m["model_id"]} failed: {e!r}'[:300])
            continue
        if m['kind'] == 'spectra_api':
            if smiles or spectrum is None:
                continue
            say(f'{m["model_id"]}: spectrum-only, all endpoints')
            try:
                for ep, card in spectra_api_cards(m, spectrum, rec).items():
                    rec['endpoints'][ep] = card
            except Exception as e:
                rec['errors'].append(f'spectrum-only model refused the input: {e}'[:400])
            continue
        if m['kind'] == 'api':
            if not smiles:
                continue
            say(f'{m["model_id"]}: all endpoints')
            try:
                o, fl, secs = api_predict(m, smiles, dict(_PHYS_LAST) if _PHYS_LAST else None)
                for ep, card in api_cards(m, o, fl, secs).items():
                    if not (ep in rec['endpoints'] and rec['endpoints'][ep].get('status') == 'ok'):
                        if spectrum is not None:
                            card['flags'].append('spectrum_given_but_not_used(model has no spectral block)')
                        rec['endpoints'][ep] = card
            except Exception as e:
                rec['errors'].append(f'{m["model_id"]} failed: {e!r}'[:300])
            continue
        for ep in m['endpoints']:
            if ep in rec['endpoints'] and rec['endpoints'][ep].get('status') == 'ok':
                continue
            say(f'{m["model_id"]}: {ep}')
            try:
                r = run_one(m, ep, smiles, spectrum, dict(_PHYS_LAST) if smiles else None)
            except Exception as e:
                rec['endpoints'][ep] = dict(status='error', model_id=m['model_id'], detail=repr(e)[:300])
                continue
            out, meta = r['out'], m['meta']
            fbin = P.bin_familiarity(r['fam'])
            card = dict(status='ok', model_id=m['model_id'], model_dir=m['model_dir'], owner=m['owner'],
                        value=r['value'], units=out.get('units', meta.get('units', {}).get(ep, 'unknown')),
                        interval=[r['lo'], r['hi']], interval_level=float(out.get('interval_level', 0.8)),
                        familiarity=r['fam'], familiarity_bin=fbin,
                        familiarity_kind=out.get('familiarity_kind', 'tanimoto_ecfp4' if smiles else 'spectral_cosine'),
                        domain=domain_flag(r['fam'], r['flags']), flags=list(dict.fromkeys(r['flags'])),
                        blocks_used=r['blocks'], seconds=r['seconds'],
                        coverage=coverage_for(m['model_dir'], m['model_id'], meta, ep, fbin, out), variant_used=out.get('variant_used'),
                        attribution_blocks=_group_attr(out.get('attribution_by_block') or out.get('attribution')),
                        attribution_raw=out.get('attribution'),
                        top_features=_top_features(out), n_train=meta.get('n_train'))
            if out.get('top_features_source'):
                card['top_features_note'] = out['top_features_source']
            if not card['top_features']:
                card['top_features_note'] = 'model did not return per-prediction feature attributions'
            hb = hazard_band(meta, ep, out, r['lo'], r['hi'])
            if hb:
                card['hazard'] = hb
            if spectrum is not None and smiles and 'struct' in m.get('feature_blocks', ['struct']):
                try:
                    r0 = run_one(m, ep, smiles, None, dict(_PHYS_LAST))
                    d = r['value'] - r0['value']
                    w = max(r['hi'] - r['lo'], 1e-9)
                    card['spectrum_effect'] = dict(value_without_spectrum=r0['value'], delta=d,
                                                   width_without=r0['hi'] - r0['lo'], width_with=w,
                                                   changed_nothing=abs(d) < NOTHING_FRAC * w,
                                                   rule=f'|delta| < {NOTHING_FRAC} x interval width')
                except Exception as e:
                    card['spectrum_effect'] = dict(error=repr(e)[:200])
            rec['endpoints'][ep] = card
    if smiles:
        say('EPI Suite comparator')
        rec['epi'] = epi_lookup(ik, smiles, live=epi_live)
        if rec['epi'].get('status') == 'ok':
            for ep, v in rec['epi']['values'].items():
                rec['endpoints'].setdefault(ep, dict(status='no_model'))['epi'] = v
    for ep in FATE:
        rec['endpoints'].setdefault(ep, dict(status='no_model'))
    import wtool_postproc  # run 3: undefined-physics rule + skill % of naive
    return wtool_postproc.apply(rec)


def read_batch(path, col=None):
    import pandas as pd
    if path.endswith(('.smi', '.txt')):
        return [l.split()[0] for l in open(path) if l.strip() and not l.startswith('#')]
    df = pd.read_csv(path, sep='\t' if path.endswith('.tsv') else ',')
    col = col or next((c for c in df.columns if c.lower() in ('smiles', 'smiles_canonical', 'canonical_smiles')), df.columns[0])
    return df[col].dropna().astype(str).tolist()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--smiles'); ap.add_argument('--spectrum'); ap.add_argument('--file')
    ap.add_argument('--smiles-col'); ap.add_argument('--out'); ap.add_argument('--epi-live', action='store_true')
    ap.add_argument('--no-physics', action='store_true', help='skip the ~1 min AIMNet2 relaxation (structure-only variants)')
    ap.add_argument('--include-mock', action='store_true'); ap.add_argument('--list-models', action='store_true')
    a = ap.parse_args()
    models = discover_models(a.include_mock)
    if a.list_models:
        print(json.dumps([{k: v for k, v in m.items() if k != 'meta'} for m in models], indent=1)); return
    spec = json.load(open(a.spectrum)) if a.spectrum else None
    if not a.file and not (a.smiles or '').strip() and spec is None:
        sys.exit('ERROR: no input. Give --smiles "<SMILES>", --spectrum spec.json, or --file batch.csv. Nothing was predicted.')
    smis = read_batch(a.file, a.smiles_col) if a.file else ([a.smiles] if a.smiles else [None])
    recs = []
    t0 = time.time()
    for i, s in enumerate(smis):
        t = time.time()
        r = predict_record(s, spec, models, a.epi_live, physics=not a.no_physics, progress=lambda x: print(f'[{i+1}/{len(smis)}] {x}', file=sys.stderr, flush=True))
        r['seconds_total'] = round(time.time() - t, 2)
        recs.append(r)
    res = dict(schema='wtool_predictions/v2', created_utc=now(), seconds_total=round(time.time() - t0, 2),
               models=[{k: v for k, v in m.items() if k != 'meta'} for m in models], records=recs)
    txt = json.dumps(res, indent=1, default=str)
    if a.out:
        open(a.out, 'w').write(txt); print('wrote', a.out, len(recs), 'records', file=sys.stderr)
    else:
        print(txt)


if __name__ == '__main__':
    main()
