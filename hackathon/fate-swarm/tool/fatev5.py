"""W-MODEL frozen v5 fate predictor (12 endpoints). FAILS LOUDLY on missing or unusable inputs.

    import sys; sys.path.insert(0, 'W-MODEL/frozen_v5'); from fatev5 import predict
    predict('CCOC(=O)c1ccccc1')                         # physics: table lookup (27k labelled structures)
    predict(smi, compute_physics=True)                  # unseen structure: AIMNet2 CPU relaxation (~1 min)
    predict(smi, physics=<dict from W-PHYSICS compute_physics>)   # physics computed by the caller
    predict(smi, allow_struct_only=True)                # explicit opt-in: structure-only model, flagged NO_PHYSICS

Errors raised (never silently degraded):
  InvalidStructureError  - SMILES does not parse / empty
  MissingPhysicsError    - no physics for this structure and the caller did not opt into compute or struct-only;
                           or a supplied physics dict lacks columns (names them) or has physics_ok=False (gives reason)
Per endpoint the output gives: value (None when the property is physically UNDEFINED for this species),
units, 90% conformal interval (normalised Mondrian; plain-Mondrian interval beside it), the EMPIRICAL test
coverage and n of that interval in this familiarity bin, nn_sim_train + bin, endpoint-specific similarity,
domain flags, naive (train-mean) guess, attribution (TreeSHAP, top features with readable meaning, block shares),
EPI Suite comparator from the swarm's cache (never fetched here unless epi_live=True).
"""
import json, os, sys, glob, subprocess
import numpy as np, pandas as pd, lightgbm as lgb
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from featurize_v4 import struct_row, bitfp, nn_bin
from rdkit import Chem, DataStructs, RDLogger
from rdkit.Chem import rdFingerprintGenerator
RDLogger.DisableLog('rdApp.*')
import domain_rules_v5 as DR


class InvalidStructureError(ValueError): pass
class MissingPhysicsError(RuntimeError): pass


COMPUTE_PHYSICS = 'W-PHYSICS/compute_physics.py'
AIMNET2_CKPT = '(internal path removed)'
PHYS_PARITY_NOTE = 'physics computed at inference by CPU AIMNet2 relaxation (CPU-vs-GPU parity: see model.json physics_parity)'
_C = {}


def _load():
    if _C: return _C
    _C['model'] = json.load(open(os.path.join(HERE, 'model.json')))
    _C['cols'] = json.load(open(os.path.join(HERE, 'columns.json')))
    _C['phys'] = pd.read_parquet(os.path.join(HERE, 'phys_table.parquet')).set_index('inchikey_std')
    _C['phys_nan_ok'] = set(c for c in _C['cols']['physics'] if _C['phys'][c].isna().any())  # element-absent charges etc.
    _C['phys_skel'] = _C['phys'].assign(sk=[i[:14] for i in _C['phys'].index]).drop_duplicates('sk').set_index('sk')
    tr = pd.read_parquet(os.path.join(HERE, 'train_smiles.parquet'))  # endpoint, skeleton, smiles_canonical
    allt = tr.drop_duplicates('skeleton')
    _C['train_fps'] = [bitfp(s) for s in allt.smiles_canonical]
    _C['ep_idx'] = {ep: np.flatnonzero(allt.skeleton.isin(set(g.skeleton)).values) for ep, g in tr.groupby('endpoint')}
    _C['ep_elems'] = json.load(open(os.path.join(HERE, 'train_elements.json')))
    epi = os.path.join(HERE, 'epi_comparator_cache.parquet')
    _C['epi'] = pd.read_parquet(epi).set_index(['inchikey_std', 'endpoint']) if os.path.exists(epi) else None
    tl = os.path.join(HERE, 'train_labels.parquet')
    _C['train_labels'] = pd.read_parquet(tl) if os.path.exists(tl) else None
    _C['boosters'] = {}
    return _C


def _bag(ep, var):
    C = _load(); k = (ep, var)
    if k not in C['boosters']:
        fs = sorted(glob.glob(os.path.join(HERE, f'{ep}__{var}__seed*.txt')))
        if not fs: raise FileNotFoundError(f'no boosters for {ep}/{var} in {HERE}')
        C['boosters'][k] = ([lgb.Booster(model_file=f) for f in fs],
                            lgb.Booster(model_file=os.path.join(HERE, f'{ep}__{var}__sigma.txt')))
    return C['boosters'][k]


def _morgan_meaning(mol):
    """bit -> list of SMILES fragments (atom environments) that set that bit in THIS molecule."""
    gen = rdFingerprintGenerator.GetMorganGenerator(radius=2, fpSize=2048)
    ao = rdFingerprintGenerator.AdditionalOutput(); ao.AllocateBitInfoMap()
    gen.GetCountFingerprint(mol, additionalOutput=ao)
    out = {}
    for bit, envs in ao.GetBitInfoMap().items():
        frags = []
        for a, r in envs[:3]:
            try:
                if r == 0:
                    frags.append(mol.GetAtomWithIdx(a).GetSymbol() + ' atom'); continue
                env = Chem.FindAtomEnvironmentOfRadiusN(mol, r, a)
                amap = {}; sub = Chem.PathToSubmol(mol, env, atomMap=amap)
                frags.append(Chem.MolToSmiles(sub))
            except Exception:
                pass
        out[bit] = sorted(set(frags))
    return out


DESC_NOTES = {'d_MolLogP': 'Crippen logP (structure-based estimate)', 'd_TPSA': 'topological polar surface area, A^2',
              'd_MolWt': 'molecular weight, g/mol', 'd_NumHDonors': 'H-bond donors', 'd_NumHAcceptors': 'H-bond acceptors',
              'phys_energy_per_atom_eV': 'AIMNet2 energy per atom: mostly element composition, not physics',
              'phys_dipole_D': 'point-charge dipole from AIMNet2 charges (no polarization), Debye',
              'phys_sasa_A2': 'solvent-accessible surface area of the relaxed geometry, A^2',
              'phys_sasa_polar_A2': 'polar (N, O, polar-H) SASA of the relaxed geometry, A^2',
              'phys_n_heavy': 'heavy-atom count (structure, carried in physics table)',
              'phys_dipole_per_heavy_D': 'point-charge dipole per heavy atom, Debye', 'phys_q_max_e': 'most positive AIMNet2 atomic charge, e',
              'phys_q_min_e': 'most negative AIMNet2 atomic charge, e', 'phys_q_std_e': 'spread (SD) of AIMNet2 atomic charges, e',
              'phys_q_abs_sum_per_atom_e': 'mean |atomic charge|, e', 'phys_q_O_min_e': 'most negative O charge (H-bond acceptor proxy), e',
              'phys_q_N_min_e': 'most negative N charge (H-bond acceptor / base proxy), e', 'phys_q_S_min_e': 'most negative S charge, e',
              'phys_q_halo_min_e': 'most negative halogen charge, e', 'phys_q_hetero_min_e': 'most negative heteroatom charge, e',
              'phys_q_hetero_max_e': 'most positive heteroatom charge, e', 'phys_q_hetero_spread_e': 'heteroatom charge range, e',
              'phys_q_C_max_e': 'most positive carbon (electrophilic-site proxy), e', 'phys_q_H_max_e': 'most positive H, e',
              'phys_q_Hpolar_max_e': 'most positive H on N/O/S (H-bond donor / acidity proxy), e',
              'phys_rg_A': 'radius of gyration of the relaxed geometry, A', 'phys_asphericity_A2': 'asphericity of the relaxed geometry, A^2',
              'phys_kappa2': 'relative shape anisotropy (0 sphere, 1 rod)', 'phys_max_extent_A': 'largest interatomic distance, A',
              'phys_sasa_polar_frac': 'polar fraction of the solvent-accessible surface',
              'phys_cpsa_pos_A2e': 'charge-weighted positive surface area, e*A^2', 'phys_cpsa_neg_A2e': 'charge-weighted negative surface area, e*A^2',
              'phys_cpsa_abs_frac': 'surface-averaged |charge|, e', 'phys_e_resid_eV': 'AIMNet2 energy relative to an additive element model (strain/stability), eV',
              'phys_e_resid_per_atom_eV': 'energy residual per atom, eV', 'phys_e_resid_robust_z': 'energy residual, robust z-score'}


def _block(c):
    if c.startswith('phys_'):
        return 'composition' if c in ('phys_energy_per_atom_eV', 'phys_n_heavy') else 'physics'
    if c.startswith('spec_'): return 'spectra'
    return 'structure_fingerprint' if c.startswith('mc') else 'structure_descriptor'


def _physics_vector(smiles, mol, ik, physics, compute_physics, allow_struct_only):
    """returns (vector or None, source string, flags). Raises MissingPhysicsError when appropriate."""
    C = _load(); pcols = C['cols']['physics']; flags = []
    if physics is None and ik in C['phys'].index:
        return C['phys'].loc[ik, pcols].values.astype(np.float32), 'GPU table (exact InChIKey)', flags
    if physics is None and ik[:14] in C['phys_skel'].index:
        flags.append('PHYSICS_FROM_STEREOISOMER: geometry shared by InChIKey skeleton (physics is not stereo-aware)')
        return C['phys_skel'].loc[ik[:14], pcols].values.astype(np.float32), 'GPU table (skeleton match)', flags
    if physics is None and compute_physics:
        env = dict(os.environ, AIMNET2_CKPT=os.environ.get('AIMNET2_CKPT', AIMNET2_CKPT))
        cp = subprocess.run([sys.executable, COMPUTE_PHYSICS, smiles], capture_output=True, text=True, env=env, timeout=1800)
        try: physics = json.loads(cp.stdout.strip().splitlines()[-1])
        except Exception:
            raise MissingPhysicsError(f'compute_physics failed for {smiles!r}: exit {cp.returncode}; stderr tail: {cp.stderr[-600:]}')
        flags.append('PHYSICS_COMPUTED_AT_INFERENCE')
    if physics is not None:
        if not physics.get('physics_ok', True):
            raise MissingPhysicsError(f'physics for {smiles!r} is not usable: physics_ok=False, error={physics.get("error")!r}, '
                                      f'qc_issue={physics.get("qc_issue")!r}. AIMNet2 covers neutral closed-shell single-component '
                                      f'molecules of H B C N O F Si P S Cl As Se Br I. Use allow_struct_only=True for a flagged '
                                      f'structure-only prediction.')
        p = {('phys_' + k if not k.startswith('phys_') else k): v for k, v in physics.items()}
        if 'phys_n_heavy' not in p and 'phys_n_heavy' in pcols:
            p['phys_n_heavy'] = mol.GetNumHeavyAtoms()  # structural count (W-PHYSICS table defines it this way)
        # columns that are legitimately NaN in training (element absent: q_N_min_e with no N, q_Hpolar_max_e with no
        # polar H, ...) may be absent/None -> NaN, exactly as in training. Any other absent column is an error.
        missing = [c for c in pcols if (c not in p or p[c] is None) and c not in C['phys_nan_ok']]
        if missing:
            raise MissingPhysicsError(f'physics dict lacks {len(missing)} required columns: {missing}. Compute them with '
                                      f'AIMNET2_CKPT={AIMNET2_CKPT} python {COMPUTE_PHYSICS} "{smiles}" and pass its JSON.')
        src = physics.get('source', 'supplied by caller')
        if src != 'gpu_table': flags.append(PHYS_PARITY_NOTE)
        return np.array([np.nan if p.get(c) is None else p[c] for c in pcols], dtype=np.float32), f'computed ({src})', flags
    if allow_struct_only:
        flags.append('NO_PHYSICS: structure-only model used at the caller\'s explicit request')
        if any(a.GetFormalCharge() != 0 for a in mol.GetAtoms()) or '.' in smiles:
            flags.append('PHYSICS_NOT_APPLICABLE: charged / multi-component species; AIMNet2 physics covers neutral single '
                         'molecules only (0 ions in the physics training set). Structure-only model trained on all defined rows.')
        return None, 'none (structure-only model, explicit opt-in)', flags
    if any(a.GetFormalCharge() != 0 for a in mol.GetAtoms()) or '.' in smiles:
        raise MissingPhysicsError(f'{smiles} is charged or multi-component: AIMNet2 physics is not defined for it in this '
                                  f'pipeline (neutral single molecules only). Call predict(..., allow_struct_only=True) for the '
                                  f'structure-only model (trained on all defined rows incl. ions), flagged NO_PHYSICS.')
    raise MissingPhysicsError(
        f'No AIMNet2 physics for {smiles} (InChIKey {ik}) in the precomputed table. Required columns ({len(pcols)}): {pcols}. '
        f'Either call predict(..., compute_physics=True) (CPU AIMNet2 relaxation, ~1 min), or run '
        f'AIMNET2_CKPT={AIMNET2_CKPT} python {COMPUTE_PHYSICS} "{smiles}" and pass physics=<its JSON>, '
        f'or call with allow_struct_only=True (flagged NO_PHYSICS).')


def domain_flag(nn):
    if nn < 0.3: return 'OUT_OF_DOMAIN'
    if nn < 0.5: return 'EXTRAPOLATING'
    return 'IN_DOMAIN'


def predict(smiles, physics=None, spectrum=None, compute_physics=False, allow_struct_only=False,
            endpoints=None, top_k=5, epi_live=False):
    if spectrum is not None:
        raise NotImplementedError('frozen_v5 structure model: spectra are used only by the spectral variants once '
                                  'W-SPECTRA\'s representation is signed off; see model.json["spectral_status"].')
    if not isinstance(smiles, str) or not smiles.strip():
        raise InvalidStructureError(f'empty or non-string SMILES: {smiles!r}')
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise InvalidStructureError(f'RDKit could not parse SMILES {smiles!r}')
    C = _load(); scols = C['cols']['struct']; pcols = C['cols']['physics']
    ik = Chem.MolToInchiKey(mol)
    pv, psrc, flags = _physics_vector(smiles, mol, ik, physics, compute_physics, allow_struct_only)
    sr = struct_row(smiles); xs = np.array([sr[c] for c in scols], dtype=np.float32)
    var = 'SP' if pv is not None else 'S'
    x = (np.concatenate([xs, pv]) if pv is not None else xs)[None, :]
    names = scols + (pcols if pv is not None else [])
    fp = bitfp(smiles); sims = np.array(DataStructs.BulkTanimotoSimilarity(fp, C['train_fps']))
    nn = float(sims.max()); b = nn_bin(nn)
    elems = sorted({a.GetSymbol() for a in mol.GetAtoms()})
    meaning = None
    out = {'smiles': smiles, 'inchikey': ik, 'model': 'W-MODEL frozen_v5', 'model_variant': var,
           'physics_source': psrc, 'nn_sim_train': round(nn, 3), 'nn_bin': b, 'domain_flag': domain_flag(nn),
           'flags': flags, 'endpoints': {}}
    M = C['model']
    for ep, em in M['endpoints'].items():
        if endpoints and ep not in endpoints: continue
        vm = em['variants'][var]
        ok, why = DR.definedness(smiles, ep)
        nn_ep = float(sims[C['ep_idx'][ep]].max()) if len(C['ep_idx'][ep]) else 0.0
        eflags = []
        new_el = [e for e in elems if e not in C['ep_elems'][ep]]
        if new_el: eflags.append(f'ELEMENT_NOT_IN_TRAINING: {new_el} never seen in {ep} training compounds')
        if nn_ep < 0.3: eflags.append(f'FAR_FROM_{ep.upper()}_TRAINING (endpoint-specific nn_sim {nn_ep:.2f} < 0.3)')
        try: cat = DR.category(smiles, ep)
        except Exception as e: cat = {'category': None, 'reason': f'category() failed: {e!r}'[:200]}
        if cat.get('category') == 'B': eflags.append('CAVEAT: ' + cat.get('reason', ''))
        meas = None
        if C['train_labels'] is not None:
            tl = C['train_labels']; mm = tl[(tl.endpoint == ep) & (tl.inchikey_std == ik)]
            if len(mm): meas = {'values': mm.value.round(4).tolist(), 'sources': mm.sources.tolist(),
                                'note': 'this compound is IN the training set; the measured value(s) are more reliable than the prediction'}
        rec = {'units': em['units'], 'defined': ok, 'definedness_reason': why, 'definedness_category': cat,
               'measured_in_training_set': meas, 'nn_sim_endpoint_train': round(nn_ep, 3),
               'domain_flag': domain_flag(min(nn, nn_ep)) if not new_el else 'OUT_OF_DOMAIN', 'flags': eflags,
               'naive_train_mean': em.get('train_mean_S', em['train_mean']) if var == 'S' else em['train_mean']}
        if not ok or cat.get('display') == 'refuse':
            # A = physically undefined (BB expert note Q-003); B with display 'refuse' = no populated neutral species in water
            # (e.g. sulfonic/sulfuric acids and their salts: gas-phase / neutral-species properties not meaningful) -> no number
            rec.update(value=None, interval=None,
                       note=('property physically UNDEFINED for this species' if not ok else
                             'property not meaningful for this species as it exists in water (' + str(cat.get('subtype')) + ')') +
                            '; no number is reported (BB expert note Q-003: refuse rather than give a wide interval)')
            out['endpoints'][ep] = rec; continue
        bag, sig = _bag(ep, var)
        y = float(np.mean([bb.predict(x)[0] for bb in bag])); s = float(np.exp(sig.predict(x)[0]))
        qn = vm['conformal_q']['normmondrian'][b]; qm = vm['conformal_q']['mondrian'][b]
        cov = vm['empirical_coverage_test_by_bin']
        sh = np.mean([bb.predict(x, pred_contrib=True)[0][:-1] for bb in bag], axis=0)
        tot = np.abs(sh).sum() or 1.0
        shares = {}
        for i, c in enumerate(names): shares[_block(c)] = shares.get(_block(c), 0.0) + abs(sh[i]) / tot
        top = []
        for i in np.argsort(-np.abs(sh))[:top_k]:
            c = names[i]; note = DESC_NOTES.get(c, '')
            if c.startswith('mc'):
                if meaning is None: meaning = _morgan_meaning(mol)
                fr = meaning.get(int(c[2:]), [])
                note = ('Morgan count bit; in this molecule: ' + ', '.join(fr)) if fr else 'Morgan count bit (absent in this molecule: its ABSENCE drove the prediction)'
            top.append({'feature': c, 'value': float(x[0, i]), 'shap': float(sh[i]), 'block': _block(c), 'meaning': note})
        rec.update({
            'value': y,
            'interval': [y - qn * s, y + qn * s], 'interval_method': 'normalised Mondrian split-conformal (|r|/sigma(x), per nn_sim bin)',
            'interval_plain_mondrian': [y - qm, y + qm],
            'nominal_coverage': M['level'],
            'empirical_coverage_test_this_bin': cov['normmondrian'].get(b),
            'empirical_coverage_test_this_bin_plain_mondrian': cov['mondrian'].get(b),
            'n_test_this_bin': vm['n_test_by_bin'].get(b), 'n_calib_this_bin': vm['conformal_q']['normmondrian']['_n_calib'][b],
            'attribution_block_shares': shares, 'attribution_top': top,
            'attribution_note': 'TreeSHAP (LightGBM pred_contrib), mean over the 3-seed bag; shares = |SHAP| fractions. '
                                'phys_energy_per_atom_eV and phys_n_heavy are counted as composition, not physics.',
            'epi_comparator': _epi(ik, ep, smiles, epi_live)})
        out['endpoints'][ep] = rec
    E = out['endpoints']
    if all(k in E and E[k].get('value') is not None for k in ('henry', 'vapor_pressure', 'water_solubility')):
        der = E['vapor_pressure']['value'] - np.log10(760.0) - (E['water_solubility']['value'] + 3.0)
        d = E['henry']['value'] - der
        out['thermo_consistency'] = {
            'henry_direct_log10_atm_m3_per_mol': E['henry']['value'], 'henry_from_vp_over_ws_log10_atm_m3_per_mol': der,
            'difference_log10': d, 'flag': 'INCONSISTENT (>1 log10 unit): treat Henry, VP and WS with extra caution' if abs(d) > 1 else 'consistent within 1 log10 unit',
            'note': 'log10 H = log10 VP[mmHg] - log10 760 - (log10 WS[mol/L] + 3); approximation valid for sparingly soluble species. '
                    'On the v5 test split, a 0.75/0.25 blend of direct/derived Henry (weight chosen on calib) lowered leak-free '
                    'Henry error from 52.1% to 49.2% of naive (v5_main/henry_consistency.json); the shipped Henry value is the direct model.'}
    return out


def _epi(ik, ep, smiles, live):
    C = _load()
    if ep.startswith('pka'): return {'value': None, 'note': 'EPI Suite has no pKa module'}
    if C['epi'] is not None and (ik, ep) in C['epi'].index:
        r = C['epi'].loc[(ik, ep)]
        if isinstance(r, pd.DataFrame): r = r.iloc[0]
        return {'value': float(r.epi_value), 'module': r.get('epi_module'), 'source': 'swarm EPI cache (structure-matched)'}
    if live:
        try:
            import urllib.request, urllib.parse
            sys.path.insert(0, 'W-TOOL')
            from epi_rate import wait_turn          # VM-wide <=1 request/s gate
            import epi_comparator as EC             # W-TOOL's unit conversion of EPI estimated values
            wait_turn()
            with urllib.request.urlopen('https://episuite.dev/api/submit?smiles=' + urllib.parse.quote(smiles, safe=''), timeout=90) as r:
                j = json.loads(r.read())
            rs = EC._get(j, ('chemicalProperties', 'smiles')); rik = EC.ik_of(rs)
            if rik != ik:
                return {'value': None, 'note': f'EPI returned a different structure ({rs!r}, {rik}); comparator withheld'}
            raw, units, module, conv = EC.extract(j)[ep]
            return {'value': conv, 'module': module, 'raw_value': raw, 'raw_units': units, 'source': 'EPI Suite API (live, identity-checked)'}
        except Exception as e:
            return {'value': None, 'note': f'live EPI call failed: {e!r}'[:200]}
    return {'value': None, 'note': 'not in the swarm EPI cache; the dashboard fetches EPI live (W-TOOL)'}


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument('smiles'); ap.add_argument('--compute-physics', action='store_true')
    ap.add_argument('--allow-struct-only', action='store_true'); ap.add_argument('--endpoints', default='')
    a = ap.parse_args()
    print(json.dumps(predict(a.smiles, compute_physics=a.compute_physics, allow_struct_only=a.allow_struct_only,
                             endpoints=a.endpoints.split(',') if a.endpoints else None), indent=1, default=str))
