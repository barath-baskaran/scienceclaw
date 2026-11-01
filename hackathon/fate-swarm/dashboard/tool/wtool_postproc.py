"""W-TOOL post-processing applied to every prediction record (run 3).

1. Physically-undefined rule: an endpoint that is defined via a gas phase or a neutral
   species is UNDEFINED for permanently charged / ionic / non-volatile species. The card's
   value is withheld (status='undefined') and a reason is shown. Rule source priority:
     a) W-SPACE rule file  <TEAM_ROOT>/agents/work/W-SPACE/undefined_rules.json  (if it exists)
        format: {"rules":[{"endpoint":..., "smarts":..., "reason":...}, ...]}
     b) provisional W-TOOL rule below (labelled 'provisional, W-TOOL' on the card).
2. Skill as % of naive guess: attaches skill_naive.json (built by skill_table.py) row for
   the card's endpoint x familiarity bin.
"""
import json, os
from rdkit import Chem

HERE = os.path.dirname(os.path.abspath(__file__))
WSPACE_RULES = '<TEAM_ROOT>/agents/work/W-SPACE/undefined_rules.json'
SKILL = os.path.join(HERE, 'skill_naive.json')

# Gas-phase-defined endpoints and neutral-species partition coefficients.
GAS = {'henry': 'Henry constant is a gas/water partition; a permanently charged or ionic species has no gas phase',
       'vapor_pressure': 'vapour pressure presumes a volatile neutral species; salts / permanent ions are non-volatile',
       'boiling_point': 'ionic / permanently charged species decompose rather than boil',
       'logkoa': 'octanol/air partition needs a gas-phase species',
       'koh_gas': 'gas-phase OH rate constant needs a gas-phase species'}
NEUTRAL = {'logkow': 'logKow is defined for the neutral species; a permanently charged species has no neutral form'}
METALS = set(range(3, 5)) | set(range(11, 14)) | set(range(19, 33)) | set(range(37, 52)) | set(range(55, 85)) | set(range(87, 104))


def charge_class(mol):
    """Return (label, why) or (None, None). Pure structure predicates, no lookup."""
    frags = Chem.GetMolFrags(mol, asMols=True)
    charged_frags = [f for f in frags if any(a.GetFormalCharge() != 0 for a in f.GetAtoms())]
    if len(frags) > 1 and len(charged_frags) >= 2:
        return 'ionic_salt', 'multi-component ionic salt'
    for a in mol.GetAtoms():
        if a.GetAtomicNum() in METALS:
            return 'metal_containing', f'contains metal {a.GetSymbol()}'
    for a in mol.GetAtoms():
        # permanent cation: positive N/P/S with no H that could be lost (quaternary ammonium, phosphonium, sulfonium)
        if a.GetFormalCharge() > 0 and a.GetSymbol() in ('N', 'P', 'S') and a.GetTotalNumHs() == 0:
            # exclude nitro / N-oxide style charge-separated neutral groups
            if not any(n.GetFormalCharge() < 0 for n in a.GetNeighbors()):
                return 'permanent_cation', f'permanently charged {a.GetSymbol()}+ (no removable H)'
    return None, None


def undefined_cells(smiles):
    mol = Chem.MolFromSmiles(smiles) if smiles else None
    if mol is None:
        return {}
    out = {}
    if os.path.exists(WSPACE_RULES):
        try:
            for r in json.load(open(WSPACE_RULES)).get('rules', []):
                p = Chem.MolFromSmarts(r['smarts'])
                if p is not None and mol.HasSubstructMatch(p):
                    out[r['endpoint']] = dict(reason=r['reason'], source='W-SPACE ' + WSPACE_RULES)
            out_ws = out; out = {}
        except Exception as e:  # fall through loudly to provisional rule
            print('W-SPACE rule file unreadable, using provisional rule:', repr(e))
    acid, base = pka_sites(mol)
    if not acid:
        out['pka_acidic'] = dict(reason='no ionisable acidic site found (checked: ' + ', '.join(ACID_SITES) + ')',
                                 compound_class='no_acidic_site', source='provisional, W-TOOL pKa-site rule (awaiting W-TOX review)', kind='not_applicable')
    if not base:
        out['pka_basic'] = dict(reason='no protonatable basic site found (checked: ' + ', '.join(BASE_SITES) + ')',
                                compound_class='no_basic_site', source='provisional, W-TOOL pKa-site rule (awaiting W-TOX review)', kind='not_applicable')
    ws = wspace_cells(smiles)
    if ws is not None:
        out.update(ws)
        return out
    cls, why = charge_class(mol)
    if cls:
        for ep, reason in {**GAS, **NEUTRAL}.items():
            out[ep] = dict(reason=f'{why}: {reason}', compound_class=cls, source='provisional, W-TOOL rule (awaiting W-SPACE)')
    return out


WSPACE_DIR = '<TEAM_ROOT>/agents/work/W-SPACE'
ALL_EPS = ['logkow','water_solubility','vapor_pressure','henry','boiling_point','melting_point','koc','bcf','logkoa','koh_gas','pka_acidic','pka_basic']


def wspace_cells(smiles):
    """Primary rule: W-SPACE domain_rules.definedness(smiles, endpoint). Returns None (loudly) if unavailable."""
    import sys
    try:
        if WSPACE_DIR not in sys.path:
            sys.path.insert(0, WSPACE_DIR)
        from domain_rules import definedness
    except Exception as e:
        print('W-SPACE domain_rules unavailable, falling back to provisional W-TOOL rule:', repr(e))
        return None
    out = {}
    for ep in ALL_EPS:
        ok, reason = definedness(smiles, ep)
        if not ok:
            out[ep] = dict(reason=reason, compound_class='see reason', source='W-SPACE domain_rules.py (definedness)', kind='physically_undefined')
    return out


# pKa applicability (provisional, W-TOOL; broad on purpose: only withhold when NO site matches)
ACID_SITES = {'carboxylic acid': '[CX3](=O)[OX2H1,OX1-]', 'phenol / enol / N-OH': '[OX2H1][c,$(C=C),$(N)]',
  'sulfonic/sulfinic/sulfuric acid': '[SX4,SX3](=O)[OX2H1,OX1-]', 'P-OH acid': '[PX4][OX2H1,OX1-]',
  'thiol': '[SX2H1]', 'sulfonamide / imide / acyl-NH': '[NX3H1,NX3H2]([SX4](=O)=O)', 'imide': '[CX3](=O)[NX3H1][CX3]=O',
  'acyl NH (amide/urea, weak)': '[CX3](=O)[NX3H1,NX3H2]', 'azole NH (tetrazole, imidazole, ...)': '[nH]',
  'activated CH (1,3-dicarbonyl, nitroalkane)': '[CX4H1,CX4H2]([CX3,$([NX3+](=O)[O-])]=O)', 'hydroxamic/oxime': '[OX2H1][NX2,NX3]',
  'boronic acid': '[BX3][OX2H1]', 'alcohol (very weak acid)': '[OX2H1][CX4]'}
BASE_SITES = {'aliphatic amine': '[NX3;!$(N-[C,S,P]=[O,S,N]);!$(N-a);!$(N#*);!$(N=*);!$(N-N=O)]', 'aromatic amine (aniline)': '[NX3;H2,H1,H0;!$(N-[C,S,P]=[O,S]);$(N-a)]',
  'aromatic N (pyridine-type)': '[nX2]', 'imine / amidine / guanidine': '[NX2]=[CX3]', 'hydrazine/hydroxylamine': '[NX3][NX3,OX2]',
  'N-oxide (W-TOX R4)': '[#7+;!$([#7+]=O)][OX1-]', 'phosphine (W-TOX R4)': '[PX3;!$(P=*);!$(P-[O,S,N])]'}
_AS = {k: Chem.MolFromSmarts(v) for k, v in ACID_SITES.items()}
_BS = {k: Chem.MolFromSmarts(v) for k, v in BASE_SITES.items()}


def pka_sites(mol):
    return ([k for k, p in _AS.items() if mol.HasSubstructMatch(p)], [k for k, p in _BS.items() if mol.HasSubstructMatch(p)])


WEAK_ACID_ONLY = {'alcohol (very weak acid)', 'acyl NH (amide/urea, weak)'}
EWG_ALCOHOL = Chem.MolFromSmarts('[OX2H1][CX4]([$(C(F)(F)),$(C(F)F),$(C[F,Cl,Br]),$(C-C(F)(F)F),$(C-[N+](=O)[O-]),$(C-C#N)])')
EWG_ALCOHOL2 = Chem.MolFromSmarts('[OX2H1][CX4]-C(F)(F)')


def pka_notes(smi):
    """W-TOX R4: when the ONLY acid sites are aliphatic alcohol / amide NH, warn that the pKa is above the label range
    (labels_v2 pka_acidic 5-95% = 2.1-11.5), unless the alcohol alpha carbon carries strong EWGs (e.g. HFIP, pKa 9.3)."""
    mol = Chem.MolFromSmiles(smi) if smi else None
    if mol is None:
        return None
    acid, _ = pka_sites(mol)
    if acid and set(acid) <= WEAK_ACID_ONLY and not mol.HasSubstructMatch(EWG_ALCOHOL2):
        return ('only very weak acid sites found (' + ', '.join(sorted(acid)) + '); the true pKa is likely 15-18, above the range '
                'covered by the training labels (5-95%: 2.1-11.5), so this estimate is an extrapolation (W-TOX review R4)')
    return None


FATE_EPS = ['logkow', 'water_solubility', 'vapor_pressure', 'henry', 'boiling_point', 'melting_point', 'koc', 'bcf', 'logkoa', 'koh_gas', 'pka_acidic', 'pka_basic']


def wspace_category(smiles, ep):
    import sys
    if WSPACE_DIR not in sys.path:
        sys.path.insert(0, WSPACE_DIR)
    from domain_rules import category
    return category(smiles, ep)


def headline(cat):
    sub = cat.get('subtype') or ''
    if cat.get('display') == 'refuse':
        if cat.get('category') == 'A2':
            return 'Not physically meaningful: strong-acid salt, the neutral form is not populated (PRINCIPAL resolution A2)'
        if cat.get('category') == 'B':
            return 'Defined only for a neutral form that does not exist at environmental pH'
        return 'Not physically defined for this compound class'
    if 'no_site' in sub:
        return 'No ionisable site detected (heuristic)'
    fl = cat.get('flags') or []
    if 'species_mismatch' in fl:
        return 'Value is for the neutral parent, not the salt as drawn'
    if 'ionic_condition_specific' in fl:
        return 'Depends strongly on test conditions for a permanent ion'
    if 'thermally_labile_possible' in fl:
        return 'May decompose before boiling'
    return 'Read with care'


CRITIC_DIR = '<TEAM_ROOT>/agents/work/CRITIC'


def q003_defined(smi, ep):
    """CRITIC q003_override: sulfonate/sulfate (acid or salt) is UNDEFINED for gas-phase/neutral-species endpoints
    (BB expert note Q-003). Returns (None, None) if the override is unavailable or does not apply."""
    import sys
    try:
        if CRITIC_DIR not in sys.path:
            sys.path.insert(0, CRITIC_DIR)
        from q003_override import definedness, is_sulfonate_or_sulfate, GAS_OR_NEUTRAL
    except Exception as e:
        print('CRITIC q003_override unavailable:', repr(e))
        return None, None
    if ep in GAS_OR_NEUTRAL and is_sulfonate_or_sulfate(smi):
        d, r = definedness(smi, ep)
        return (False, r) if not d else (None, None)
    return None, None


MODEL_FLAG = {'IN_DOMAIN': 'in', 'EXTRAPOLATING': 'edge', 'OUT_OF_DOMAIN': 'out'}
RANK = {'in': 0, 'edge': 1, 'out': 2}


def harmonise_domain(c):
    """S-1 review blocker 2: the card shows the STRICTER of the similarity bin and the model's own domain flag."""
    sim = c.get('domain'); mf = MODEL_FLAG.get(str(c.get('domain_flag_model') or '').upper())
    if sim not in RANK or mf is None or c.get('domain_similarity') is not None:
        return
    c['domain_similarity'] = sim
    if RANK[mf] > RANK[sim]:
        c['domain'] = mf
        c['domain_reason'] = ('similarity alone says ' + {'in': 'familiar', 'edge': 'somewhat new', 'out': 'new'}[sim] +
                              ', but the model\'s own applicability check says ' + str(c.get('domain_flag_model')) + '; the stricter is shown')


def width_check(c):
    """S-1 review blocker 3: say when this molecule's range is much wider than the typical range behind the coverage figure."""
    iv = c.get('interval'); cv = c.get('coverage') or {}
    mw = cv.get('median_width')
    if iv and mw and mw > 0 and None not in iv:
        r = (iv[1] - iv[0]) / mw
        c['width_ratio_to_typical'] = r
        if r > 1.5:
            c.setdefault('flags', []).append('interval_wider_than_typical')


def is_ionic_input(smi):
    """True if the structure as entered is a salt or carries a formal charge (the only case where the
    salt-dose vs organic-ion caveat applies; W-TOX's definedness_reason text is attached to every record)."""
    m = Chem.MolFromSmiles(smi) if smi else None
    if m is None:
        return False
    if len(Chem.GetMolFrags(m)) > 1:
        return True
    return any(a.GetFormalCharge() != 0 and not any(n.GetFormalCharge() * a.GetFormalCharge() < 0 for n in a.GetNeighbors())
               for a in m.GetAtoms())


SULFONYL = Chem.MolFromSmarts('[SX4](=O)(=O)')
SULF_ACID = Chem.MolFromSmarts('[SX4](=O)(=O)[OX2H1,OX1-]')


def sulfonyl_pka_fix(rec, smi):
    """Run-3 regression finding (SDS): W-SPACE's basic-site pattern '[P,As,Se,S;X3,X4]=O' matches the S=O of
    sulfonyl/sulfate groups, so a basic pKa (~6.6) was shown for sodium dodecyl sulfate. Protonation of a
    sulfonyl O happens far below pH 0, outside the aqueous window. When the W-TOOL site screen finds no
    other basic site, the basic pKa is withheld. For a sulfonic acid / sulfate monoester the acidic pKa is
    far below the training-label range (5-95%: 2.1-11.5), so the estimate carries a caveat."""
    m = Chem.MolFromSmiles(smi) if smi else None
    if m is None or not m.HasSubstructMatch(SULFONYL):
        return
    acid, base = pka_sites(m)
    c = rec['endpoints'].get('pka_basic')
    if c and c.get('status') == 'ok' and not base:
        rec['endpoints']['pka_basic'] = dict(status='undefined', kind='not_applicable',
            headline='Does not apply: no basic ionisable site found (rule of thumb)',
            reason='The only "basic site" matched was the S=O oxygen of a sulfonyl/sulfate group, whose protonation occurs far below pH 0 '
                   '(outside the aqueous window); no amine/aza-aromatic/other base was found by the W-TOOL site screen.',
            rule_source='W-TOOL sulfonyl override of W-SPACE pattern [P,As,Se,S;X3,X4]=O (regression finding, run 3)',
            withheld_model_output={k: c.get(k) for k in ('value', 'interval', 'model_id') if k in c}, epi=c.get('epi'))
    c = rec['endpoints'].get('pka_acidic')
    if c and c.get('status') == 'ok' and m.HasSubstructMatch(SULF_ACID) and not c.get('caveat'):
        c['caveat'] = dict(headline='Strong acid: true pKa is likely below 1, under the range the model was trained on',
                           reason='Sulfonic acids and sulfate monoesters are strong acids (pKa typically below 0). Training labels cover pKa 2.1-11.5 '
                                  '(5-95%), so this estimate is an extrapolation and is likely far too high.', flags=['strong_acid_extrapolation'],
                           source='W-TOOL rule (regression finding, run 3)')


def inorganic_not_assessed(rec, smi):
    """Run 4 stress test (W-TOOL): NaCl was given a vapour pressure, boiling point and two pKa values, predicted for the
    parent '[Na+]'. labels_v2 contains 0 compounds without a carbon atom (checked by parsing every smiles_canonical), so
    the fate models have no basis for, and no test evidence on, carbon-free species. Withhold every fate number there.
    This is a refusal ('not assessed'), not a statement that the property is undefined."""
    if not smi:
        return
    par = ((rec.get('species') or {}).get('parent_smiles')) or smi
    m = Chem.MolFromSmiles(par) or Chem.MolFromSmiles(smi)
    if m is None or any(a.GetAtomicNum() == 6 for a in m.GetAtoms()):
        return
    for ep in FATE_EPS:
        c = rec['endpoints'].get(ep)
        if not c or c.get('status') != 'ok':
            continue
        withheld = {k: c.get(k) for k in ('value', 'interval', 'model_id') if k in c}
        rec['endpoints'][ep] = dict(status='undefined', kind='not_assessed',
                                    headline='Not assessed: no carbon atom (inorganic species)',
                                    reason=('The structure the model would see (' + par + ') contains no carbon. The training labels '
                                            '(labels_v2) contain 0 carbon-free compounds, so the model has no basis for an estimate here and '
                                            'its tested ranges say nothing about this class. This does not mean the property is undefined.'),
                                    rule_source='W-TOOL inorganic rule (run 4 stress test)', withheld_model_output=withheld, epi=c.get('epi'))


def strong_acid_consistency(rec):
    """S-1 re-review (b): if the same card refuses logKow/VP because W-SPACE classes the compound as a strong acid
    (subtype contains 'strong_acid'), the acidic pKa must not be shown as an unqualified in-domain number."""
    c = rec['endpoints'].get('pka_acidic')
    if not c or c.get('status') != 'ok' or c.get('caveat'):
        return
    subs = [str((rec['endpoints'].get(e) or {}).get('subtype') or '') for e in ('logkow', 'vapor_pressure', 'henry')]
    if any('strong_acid' in x for x in subs):
        c['caveat'] = dict(headline='Treated as a strong acid elsewhere on this card: the true pKa may be lower than this estimate',
                           reason='The rules that withhold logKow / vapour pressure for this compound class it as a strong acid (neutral form not '
                                  'populated at environmental pH; heuristic pKa below ~1). The model estimate here is higher than that. '
                                  'Measured pKa values for such acids are scarce and disputed, so read this number as an upper bound, not a measurement.',
                           flags=['strong_acid_inconsistency'], source='W-TOOL consistency rule (S-1 re-review)')


def apply(rec):
    """Run 3 rule source: W-SPACE domain_rules.category(smiles, endpoint) (A/B/C + display refuse/caveat/normal),
    applied to the structure AS ENTERED. 'refuse' withholds the number (status='undefined'); 'caveat' keeps it and
    attaches the reason prominently. If W-SPACE's module cannot be imported, the provisional W-TOOL rule is used and
    every card says so."""
    smi = (rec.get('input') or {}).get('smiles')
    if smi:
        try:
            for ep in FATE_EPS:
                cat = wspace_category(smi, ep)
                c = rec['endpoints'].get(ep, {})
                q3d, q3r = q003_defined(smi, ep)
                if q3d is False and cat.get('display') != 'refuse':
                    cat = dict(cat, display='refuse', category='A2', subtype='q003_sulfonate_sulfate', reason=q3r)
                elif q3d is False:
                    cat = dict(cat, category='A2', subtype='q003_sulfonate_sulfate', reason=q3r)
                if ep in ('pka_acidic', 'pka_basic') and 'no_site' in (cat.get('subtype') or '') and c.get('status') == 'ok':
                    # S-1 review blocker 1: a pKa for a molecule with no ionisable site is not shown as a number.
                    withheld = {k: c.get(k) for k in ('value', 'interval', 'model_id') if k in c}
                    rec['endpoints'][ep] = dict(status='undefined', kind='not_applicable',
                                                headline='Does not apply: no ' + ('acidic' if ep == 'pka_acidic' else 'basic') + ' ionisable site found (rule of thumb)',
                                                reason=cat.get('reason'), category=cat.get('category'), subtype=cat.get('subtype'),
                                                rule_source='W-SPACE domain_rules.category (no_site heuristic); withheld per S-1 usability review',
                                                withheld_model_output=withheld, epi=c.get('epi'))
                    continue
                if (c.get('status') == 'undefined' and str(c.get('rule_source', '')).startswith('W-MODEL') and cat.get('display') != 'refuse'
                        and q3d is not False):
                    # run 4: W-SPACE v4.1 now calls this cell defined (e.g. a strong acid drawn neutral -> category B caveat),
                    # but the frozen model's built-in definedness (older rules) withheld the number. Say exactly that,
                    # instead of the model's self-contradictory "defined: ..." reason under an "undefined" headline.
                    rec['endpoints'][ep] = dict(c, kind='defined_not_measurable_neutral_absent', category=cat.get('category'), subtype=cat.get('subtype'),
                                                headline='No number: the frozen model withholds this class (its built-in rule predates the current one)',
                                                reason=('Current W-SPACE rule (v4.1): ' + str(cat.get('reason')) + ' -- the property is defined for the neat neutral form, '
                                                        'but the frozen model (W-MODEL frozen_v5) was built with an older rule that refused this class, so it gives no value. '
                                                        'This is a gap in the model, not a property that does not exist.'),
                                                model_reason=c.get('reason'), model_gap=True)
                    continue
                if cat.get('display') == 'refuse':
                    withheld = {k: c.get(k) for k in ('value', 'interval', 'model_id') if k in c}
                    rec['endpoints'][ep] = dict(status='undefined', kind=('physically_undefined' if cat.get('category') in ('A', 'A2') else 'defined_not_measurable_neutral_absent'), headline=headline(cat), reason=cat.get('reason'),
                                                category=cat.get('category'), subtype=cat.get('subtype'),
                                                rule_source='W-SPACE domain_rules.category (derived rule, BB expert note Q-003)',
                                                withheld_model_output=withheld, epi=c.get('epi'))
                elif cat.get('display') == 'caveat' and c.get('status') == 'ok':
                    c['caveat'] = dict(headline=headline(cat), reason=cat.get('reason'), category=cat.get('category'), subtype=cat.get('subtype'),
                                       flags=cat.get('flags') or [], source='W-SPACE domain_rules.category')
            rec['rule_source'] = 'W-SPACE domain_rules.category'
        except Exception as e:
            rec.setdefault('errors', []).append('W-SPACE definedness rules unavailable (' + repr(e)[:120] + '); provisional W-TOOL rule used')
            und = undefined_cells(smi)
            for ep, u in und.items():
                c = rec['endpoints'].get(ep, {})
                withheld = {k: c.get(k) for k in ('value', 'interval', 'model_id') if k in c}
                rec['endpoints'][ep] = dict(status='undefined', kind=u.get('kind', 'physically_undefined'), reason=u['reason'], rule_source=u['source'],
                                            compound_class=u.get('compound_class'), withheld_model_output=withheld, epi=c.get('epi'))
    sulfonyl_pka_fix(rec, smi)
    inorganic_not_assessed(rec, smi)
    strong_acid_consistency(rec)
    pn = pka_notes(smi)
    c = rec['endpoints'].get('pka_acidic')
    if pn and c and c.get('status') == 'ok':
        c.setdefault('flags', []).append('pka_weak_acid_only')
        c['note_plain'] = pn
    for ep, c in rec['endpoints'].items():
        dr = str(c.get('definedness_reason') or '')
        if c.get('status') == 'ok' and ep not in FATE_EPS and 'mismatch' in dr and not c.get('caveat') and is_ionic_input(smi):
            # S-1 review item 11: make the hazard species-mismatch warning visible on the row
            c['caveat'] = dict(headline='Dose refers to the salt as tested; the model sees the organic ion only', reason=dr, flags=['species_mismatch'],
                               source='W-TOX model definedness_reason')
        if c.get('status') == 'ok':
            harmonise_domain(c)
            width_check(c)
    skill = json.load(open(SKILL)) if os.path.exists(SKILL) else {}
    for ep, c in rec['endpoints'].items():
        if c.get('status') != 'ok' or c.get('skill_naive'):
            continue
        row = (skill.get(c.get('model_id'), {}).get(ep, {}) or {})
        if row:
            c['skill_naive'] = dict(overall=row.get('all'), this_bin=row.get('bins', {}).get(c.get('familiarity_bin')), source=SKILL)
    return rec
