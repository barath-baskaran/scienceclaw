"""W-SPACE physical-definedness rules, v3 (Run 3).

STATUS OF THE EXPERT NOTE: (internal path removed) was NOT read. It is mode 640
((user):team) and the swarm user gets 'Permission denied'. These rules are therefore derived from
first principles, from the one-sentence principle in the W-SPACE brief: a property defined in terms of a
gas phase or of a neutral species is undefined for a permanently charged or non-volatile species.

DERIVATION (no example compounds are hard-coded; everything follows from two tables):
 (a) What each endpoint REQUIRES of the species, from the endpoint's definition:
     henry          K_H = p_i / c_i,aq of the same species        -> needs a gas-phase form of the species
     vapor_pressure p of the gas in equilibrium with the condensed  -> needs a gas-phase form
     boiling_point  T at which p_vap = 1 atm                        -> needs a gas-phase form
     koh_gas        k(OH + X) in the GAS phase                       -> needs a gas-phase form
     logkoa         C_octanol / C_air                                -> needs a gas-phase form
     logkow         C_oct / C_w of the NEUTRAL (un-ionised) species  -> needs a neutral microspecies
     water_solubility, melting_point, koc, bcf: defined for any substance or dissolved species -> no requirement
     pka_acidic / pka_basic: need an ionisable acidic / basic site. This is NOT the note's rule; it is reported as a
                    separate state, "not applicable: no ionisable site (heuristic)", and never mixed into "undefined".
 (b) What the species CAN do, after standardisation (so that how a salt is drawn does not matter):
     1. RDKit rdMolStandardize.Cleanup (sanitise, metal disconnection, functional-group normalisation, reionise)
     2. Keep the largest organic fragment (counter-ions and other fragments are recorded and removed)
     3. Uncharger: remove every charge that a proton transfer can remove
     4. Whatever charge is left is PERMANENT. Charges on bonded +/- atom pairs (nitro, N-oxide, azide, diazo,
        isonitrile, sulfoxide drawn as S+-O-) cancel within a neutral group and are ignored.
        - a positive atom without H              -> permanent cation (quaternary N/P/As, ternary S/O, N-alkyl azinium, carbenium)
        - a negative atom on B/Al/Ga/P/As/Sb/Si/metal, or any negative atom left when no permanent cation needs it
                                                  -> permanent anion
        - permanent cation + balancing anion, net 0 -> permanent zwitterion (no uncharged microspecies exists)
        - a metal or metalloid cation left in the parent -> metal_containing: NOT ASSESSED (ionic and covalent
          drawings of organometals give different answers; the rule refuses to decide)
     capability: neutralisable -> has a gas-phase form (in principle) AND a neutral microspecies
                 permanent_cation / permanent_anion / permanent_zwitterion -> has neither (an ion, or an inner salt
                 with no uncharged form, has no vapour of the species and no neutral species to partition)
 UNDEFINED := endpoint requirement AND NOT species capability.

WHAT THE RULE DOES NOT DO (on purpose; listed as limitations):
 - Low-volatility NEUTRAL compounds (polymers, large dyes, sugars) keep their gas-phase endpoints: the value is
   very small, not undefined. Decomposition before boiling is real but cannot be decided from structure alone.
 - For salts of neutralisable parents, the endpoint is DEFINED FOR THE NEUTRAL PARENT, which is a different species
   from the salt as drawn. The tool must say so (see neutral_parent()).

API (stable; W-TOOL depends on it):
  definedness(smiles, endpoint) -> (bool defined, str reason)
  neutral_parent(smiles)        -> (parent smiles or None, str reason)
  species(smiles)               -> dict(species_class, parent_smiles, removed_fragments, net_charge, notes, ...)
  pka_site(smiles, kind)        -> (bool site_found, str reason)   kind in {'acidic','basic'}; heuristic
Rule table: domain_rules.json (written by running this file, which also runs the tests).
"""
import json
from functools import lru_cache
from rdkit import Chem, RDLogger
from rdkit.Chem.MolStandardize import rdMolStandardize
RDLogger.DisableLog('rdApp.*')

ENDPOINT_REQUIRES = {
    'henry': ('gas_phase', 'K_H relates the gas-phase partial pressure of the species to its aqueous concentration'),
    'vapor_pressure': ('gas_phase', 'vapour pressure is the pressure of the species in the gas phase over its condensed phase'),
    'boiling_point': ('gas_phase', 'the boiling point is where the vapour pressure of the species reaches 1 atm'),
    'koh_gas': ('gas_phase', 'kOH here is a gas-phase reaction rate constant'),
    'logkoa': ('gas_phase', 'K_OA is the octanol/air concentration ratio of the species'),
    'logkow': ('neutral_species', 'K_OW is defined for the neutral (un-ionised) species'),
    'water_solubility': (None, 'defined for any substance'),
    'melting_point': (None, 'defined for any solid substance'),
    'koc': (None, 'sorption to organic carbon is defined for dissolved ions and neutrals alike'),
    'bcf': (None, 'bioconcentration is defined for dissolved ions and neutrals alike'),
    'pka_acidic': ('acidic_site', 'needs an ionisable acidic site'),
    'pka_basic': ('basic_site', 'needs an ionisable basic site'),
}
CAPABILITY = {  # species_class -> (has gas-phase form, has neutral microspecies)
    'neutralisable': (True, True),
    'permanent_cation': (False, False),
    'permanent_anion': (False, False),
    'permanent_zwitterion': (False, False),
}
SPECIES_TEXT = {
    'permanent_cation': 'a permanent cation (positive charge on an atom with no removable proton)',
    'permanent_anion': 'a permanent anion (negative charge that no proton transfer removes)',
    'permanent_zwitterion': 'a permanent inner salt (a permanent cation balanced by an anion; no uncharged form exists)',
}
METALS = set('Li Na K Rb Cs Be Mg Ca Sr Ba Al Ga In Tl Sn Pb Bi Sc Ti V Cr Mn Fe Co Ni Cu Zn Y Zr Nb Mo Ru Rh Pd Ag Cd '
             'Hf Ta W Re Os Ir Pt Au Hg La Ce Pr Nd Sm Eu Gd Tb Dy Ho Er Tm Yb Lu U Th Ge Sb Te Po'.split())
PERM_ANION_ELEMENTS = set('B Al Ga P As Sb Si'.split())  # negative charge on these is not removable by protonation

# heuristic ionisable-site SMARTS (aqueous range, roughly pKa -2..14); used only for the separate pKa state
ACID_SITES = [
    ('carboxylic acid', '[CX3](=O)[OX2H1]'), ('sulfonic/sulfuric acid', '[SX4](=O)(=O)[OX2H1]'),
    ('sulfinic acid', '[SX3](=O)[OX2H1]'), ('phosphorus acid', '[PX4](=O)[OX2H1]'), ('phosphorus acid (S)', '[PX4](=S)[OX2H1]'),
    ('phenol/enol', '[OX2H1][c,$(C=C)]'), ('thiol', '[SX2H1]'), ('sulfonamide NH', '[NX3;H1,H2]S(=O)(=O)'),
    ('imide/acyl-sulfonyl NH', '[NX3H1](C=O)C=O'), ('acidic azole NH', '[nH]1nnnc1'), ('azole NH', '[nH]'),
    ('hydroxamic acid', 'C(=O)N[OH]'), ('oxime', '[CX3]=N[OH]'), ('1,3-dicarbonyl CH', '[CX4;H1,H2](C=O)C=O'),
    ('fluorinated/activated alcohol', '[OX2H1][CX4]C(F)(F)'), ('boronic acid', 'B[OH]'), ('nitro-alkane CH', '[CX4;H1,H2][N+](=O)[O-]'),
    ('N-H of aryl amide/urea/carbamate', '[NX3H1](C=O)c'), ('barbiturate/uracil-type NH', 'O=C[NH]C=O'),
    ('nitramine NH', '[NX3;H1,H2][N+](=O)[O-]'), ('N-hydroxy azole/amide', '[OX2H1][n,N]'), ('thioamide/thiourea NH', '[NX3;H1,H2]C=S'),
    ('peroxy acid / hydroperoxide', '[OX2H1][OX2]'), ('aryl/acyl CH acid (malononitrile-type)', '[CX4;H1,H2](C#N)C#N'),
    ('phenolate drawn zwitterionic', '[OX1-]c'), ('acidic NH of hydrazone/azo dye', '[NX3H1](N=*)c'),
]
BASE_SITES = [
    ('aliphatic amine', '[NX3;H2,H1,H0;!$(N[C,S,P]=[O,S,N]);!$(N-a);!$(N#*);!$(N=*);!$(N-[N,O]);!$(N-S)]'),
    ('aromatic amine', '[NX3;H2,H1,H0;$(N-a);!$(N[C,S,P]=[O,S,N]);!$(N-[N,O])]'),
    ('azine/azole ring N', '[nX2]'), ('amidine/guanidine', '[NX3][CX3]=[NX2]'), ('imine', '[CX3]=[NX2;!$(N-O);!$(N=N)]'),
    ('hydrazine N', '[NX3;H2,H1;$(N-N);!$(N[C,S]=O)]'),
    ('N-oxide / nitrone O', '[OX1-][#7+]'), ('hydroxylamine/alkoxyamine N', '[NX3;!$(N=*);!$(N[C,S]=O)][OX2]'),
    ('amide/urea/thioamide (weak, pKa ~ -2..1)', '[NX3][CX3]=[O,S]'), ('pyrrole-type ring (C-protonation)', '[nX3;H1,$(n[CH3])]1cccc1'),
    ('pyridone/quinolone carbonyl', '[#6]=,:[#6]-,:[#6](=O)-,:[#6]=,:[#6]'), ('phosphine/arsine/selenoxide O', '[P,As,Se,S;X3,X4]=O'),
    ('phosphazene/iminophosphorane N', 'N=P'),
]
_A = [(n, Chem.MolFromSmarts(s)) for n, s in ACID_SITES]
_B = [(n, Chem.MolFromSmarts(s)) for n, s in BASE_SITES]
_UNCH = rdMolStandardize.Uncharger(canonicalOrder=True)


def _heavy(f):
    return sum(1 for a in f.GetAtoms() if a.GetAtomicNum() > 1)


@lru_cache(maxsize=200000)
def species(smiles):
    out = dict(input=smiles, species_class='unparseable', parent_smiles=None, removed_fragments=[], net_charge=None,
               n_permanent_pos=0, n_permanent_neg=0, notes=[])
    m = Chem.MolFromSmiles(smiles) if isinstance(smiles, str) and smiles else None
    if m is None:
        out['notes'].append('RDKit could not parse the SMILES')
        return out
    try:
        m = rdMolStandardize.Cleanup(m)
    except Exception as e:  # keep going on the raw molecule
        out['notes'].append(f'Cleanup failed ({type(e).__name__}); raw structure used')
    frags = list(Chem.GetMolFrags(m, asMols=True, sanitizeFrags=False))
    org = [f for f in frags if any(a.GetAtomicNum() == 6 for a in f.GetAtoms())]
    pool = org if org else frags
    parent = max(pool, key=lambda f: (_heavy(f), Chem.MolToSmiles(f)))
    out['removed_fragments'] = sorted(Chem.MolToSmiles(f) for f in frags if f is not parent)
    if len(org) > 1:
        out['notes'].append('several organic components; assessed on the largest one')
    def _unch(f):
        try:
            q = _UNCH.uncharge(Chem.Mol(f)); Chem.SanitizeMol(q); return q
        except Exception as e:
            out['notes'].append(f'Uncharger failed ({type(e).__name__})'); return f
    if len(org) > 1:
        # organic ion pair: if any organic component keeps a permanent positive charge after neutralisation,
        # that component is the one assessed (the counter-ion's neutral parent is a different substance)
        perm = [f for f in org if any(a.GetFormalCharge() > 0 and a.GetTotalNumHs() == 0 and a.GetSymbol() not in METALS
                                      and not any(nb.GetFormalCharge() < 0 for nb in a.GetNeighbors())
                                      for a in _unch(f).GetAtoms())]
        if perm and parent not in perm:
            parent = max(perm, key=lambda f: (_heavy(f), Chem.MolToSmiles(f)))
            out['removed_fragments'] = sorted(Chem.MolToSmiles(f) for f in frags if f is not parent)
            out['notes'].append('organic ion pair: assessed on the permanently charged component')
    p = _unch(parent)
    out['parent_smiles'] = Chem.MolToSmiles(p)
    out['net_charge'] = int(sum(a.GetFormalCharge() for a in p.GetAtoms()))
    if any(a.GetSymbol() in METALS for a in p.GetAtoms()):
        out['species_class'] = 'metal_containing_not_assessed'
        out['notes'].append('metal/metalloid in the parent: ionic and covalent drawings disagree, definedness not assessed')
        return out
    pos, neg = [], []
    for a in p.GetAtoms():
        q = a.GetFormalCharge()
        if q == 0:
            continue
        # charge-separated neutral group: a charged atom bonded to an oppositely charged atom
        if any(nb.GetFormalCharge() * q < 0 for nb in a.GetNeighbors()):
            continue
        (pos if q > 0 else neg).append(a)
    perm_pos = [a for a in pos if a.GetTotalNumHs() == 0]
    perm_neg_elem = [a for a in neg if a.GetSymbol() in PERM_ANION_ELEMENTS]
    out['n_permanent_pos'] = len(perm_pos)
    # Uncharger leaves an O-/S-/N- charged only if it is needed to balance a permanent cation (inner salt)
    other_neg = [a for a in neg if a.GetSymbol() not in PERM_ANION_ELEMENTS]
    out['n_permanent_neg'] = len(perm_neg_elem) + (len(other_neg) if not perm_pos else 0)
    if perm_pos and (other_neg or perm_neg_elem) and out['net_charge'] == 0:
        out['species_class'] = 'permanent_zwitterion'
    elif perm_pos:
        out['species_class'] = 'permanent_cation'
    elif perm_neg_elem or (other_neg and out['net_charge'] < 0):
        out['species_class'] = 'permanent_anion'
    else:
        out['species_class'] = 'neutralisable'
        if pos or neg:
            out['notes'].append('residual protonated/deprotonated site left by Uncharger; treated as neutralisable')
    if out['removed_fragments'] and out['species_class'] == 'neutralisable' and Chem.MolToSmiles(parent) != out['parent_smiles']:
        out['notes'].append('salt or charged drawing; assessed on the neutral parent')
    return out


def neutral_parent(smiles):
    s = species(smiles)
    if s['species_class'] == 'neutralisable':
        if s['removed_fragments'] or s['parent_smiles'] != Chem.MolToSmiles(Chem.MolFromSmiles(smiles)):
            return s['parent_smiles'], 'neutral parent after removing counter-ions ' + str(s['removed_fragments']) + ' and neutralising'
        return s['parent_smiles'], 'already a neutral single species'
    if s['species_class'] == 'unparseable':
        return None, 'unparseable SMILES'
    if s['species_class'] == 'metal_containing_not_assessed':
        return None, 'metal-containing: no neutral parent assigned'
    return None, f"no neutral parent: the organic component is {SPECIES_TEXT[s['species_class']]}"


def pka_site(smiles, kind):
    s = species(smiles)
    if s['parent_smiles'] is None:
        return True, 'unparseable: site not assessed'
    m = Chem.MolFromSmiles(s['parent_smiles'])
    if m is None:
        return True, 'parent not parseable: site not assessed'
    pats = _A if kind == 'acidic' else _B
    hits = [n for n, p in pats if p is not None and m.HasSubstructMatch(p)]
    if hits:
        return True, f'{kind} site(s): ' + ', '.join(hits)
    return False, f'no {kind} ionisable site found by the heuristic SMARTS list (aqueous pKa range); NOT the same as physically undefined'


def definedness(smiles, endpoint):
    req, why = ENDPOINT_REQUIRES.get(endpoint, (None, 'unknown endpoint'))
    s = species(smiles)
    sc = s['species_class']
    if sc == 'unparseable':
        return True, 'unparseable structure: definedness not assessed'
    if req is None:
        return True, f'defined: {why}'
    if req in ('acidic_site', 'basic_site'):
        # permanent cation with no other basic site: no basic pKa (follows from the site test on the parent)
        ok, r = pka_site(smiles, req.split('_')[0])
        return (True, 'defined: ' + r) if ok else (True, 'not applicable (heuristic): ' + r)
    if sc == 'metal_containing_not_assessed':
        return True, 'metal-containing: definedness not assessed (treated as defined; check by hand)'
    gas_ok, neutral_ok = CAPABILITY[sc]
    ok = gas_ok if req == 'gas_phase' else neutral_ok
    if ok:
        extra = ' (assessed on the neutral parent ' + s['parent_smiles'] + '; the salt as drawn is a different, non-volatile species)' \
            if 'salt or charged drawing; assessed on the neutral parent' in s['notes'] else ''
        return True, f'defined: {why}; the species has a neutral form{extra}'
    alt = (' What is measurable instead: the distribution ratio logD at a stated pH, or an ion-pair partition coefficient with a '
           'named counter-ion.' if req == 'neutral_species' else
           ' What is measurable instead: nothing in the gas phase; aqueous-phase quantities (solubility, sorption Kd/Koc, BCF) remain defined.')
    return False, (f"UNDEFINED: {why}, and the organic component is {SPECIES_TEXT[sc]}, which has no "
                   + ('gas-phase form (an ion is non-volatile)' if req == 'gas_phase' else 'uncharged microspecies')
                   + '. This is not missing data.' + alt)


def pka_applicable(smiles, endpoint):
    """Separate third state for pKa: (applicable bool, reason)."""
    if endpoint not in ('pka_acidic', 'pka_basic'):
        return True, 'not a pKa endpoint'
    return pka_site(smiles, endpoint.split('_')[1])



# =====================================================================================================================
# THREE-WAY CATEGORY (PRINCIPAL request, Run 3): A physically undefined / B defined but non-equivalent or not measurable
# by the standard protocol (pooled labels are not comparable) / C defined and measurable (an unlabelled one is a genuine gap).
# A comes from the endpoint DEFINITION (above). B comes from the standard MEASUREMENT PROTOCOL's preconditions:
#  logkow  OECD 107/117/123 measure the neutral species at a buffered pH where it is un-ionised, and exclude
#          surface-active substances -> B if no buffer window exists (strong acid pKa below ~1, strong base pKa above ~12)
#          or if the compound is a surfactant.
#  henry, logkoa  air/water and air/octanol partitioning measured from solution -> for a strong acid or base only the
#          ionised, pH-dependent effective value is observable -> B.
#  boiling_point  needs the liquid to survive to p_vap = 1 atm -> B for structures that typically decompose first
#          (amino-acid-like inner salts, polyols/sugars, neutral parent MW > 600 g/mol, >= 2 strong-acid groups).
#  melting_point  B for amino-acid-like inner salts (reported values are usually decomposition temperatures).
#  koh_gas  smog-chamber/relative-rate methods need measurable vapour -> B for neutral parent MW > 500 g/mol.
#  water_solubility  B for surfactants (above the CMC a micellar 'solubility' is not the molecular solubility);
#          A for a liquid miscible with water (no finite value) - this can only be known from the label table
#          (labels_tox_v2_miscibility.miscible), never from structure.
#  koc, bcf  C for all species. Koc of permanent cations is measurable by batch equilibrium (OECD 106) but is governed
#          by cation exchange, so it should be reported with the sorbent's CEC (caveat attached, still C).
#  pka_*   A for acidic pKa when the neutral parent has no hydrogen (nothing to give). Otherwise, when the heuristic SMARTS
#          find no site in the aqueous window (about pKa -2..14): B (every molecule is acidic/basic at SOME extreme, but the
#          aqueous pKa outside the window is extrapolated, not titrated). Revised after CRITIC's audit: absence of a
#          recognised site was first A, which overstated undefinedness and depended on an incomplete SMARTS list.
# All B rules are HEURISTIC structure screens, listed with their SMARTS in domain_rules.json.
# =====================================================================================================================
from rdkit.Chem import Descriptors as _D
B_SMARTS = {
    'strong_acid': ['[SX4](=O)(=O)[OX2H1]', '[OX2][SX4](=O)(=O)[OX2H1]', 'C(F)(F)C(=O)[OX2H1]', '[PX4](=O)([OX2H1])[OX2H1]'],
    'strong_base': ['[NX3;!$(NC=O)][CX3](=[NX2;!$(N-a);!$(N-C=O);!$(N-S)])[NX3;!$(NC=O)]', '[CX3;!$(C-N-C=O)](=[NX2;H0,H1;!$(N-a);!$(N-C=O);!$(N-S);!$(N-O)])[NX3;H2,H1;!$(NC=O)]'],
    'surfactant_tail': ['[CH2][CH2][CH2][CH2][CH2][CH2][CH2][CH2,CH3]', 'C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)'],
    'surfactant_head': ['[SX4](=O)(=O)[OX2H1,OX1-]', '[CX3](=O)[OX2H1,OX1-]', '[PX4](=O)[OX2H1,OX1-]', '[NX4+]', '[N+][O-]',
                        'OCCOCCOCCO', '[OX2H1][CX4][CX4]([OX2H1])[CX4][OX2H1]'],
    'amino_acid_like': ['[NX3;H2,H1,H0;!$(NC=O);!$(N-a);!$(N-S)].[CX3](=O)[OX2H1]', '[NX3;H2,H1,H0;!$(NC=O);!$(N-a)].[SX4](=O)(=O)[OX2H1]'],
    'polyol_sugar': ['[OX2H1][CX4][CX4]([OX2H1])[CX4]([OX2H1])[CX4][OX2H1]', '[OX2;R][CX4;R]([OX2H1,OX2])[CX4;R][OX2H1]'],
}
_BP = {k: [Chem.MolFromSmarts(x) for x in v] for k, v in B_SMARTS.items()}
LABILE_SMARTS = ['[OX2][OX2]', '[#6]N=N[#6]', '[#6]=[N+]=[N-]', 'N=[N+]=[N-]', '[N+](=O)[O-].[N+](=O)[O-].[N+](=O)[O-]']
_LABILE = [Chem.MolFromSmarts(x) for x in LABILE_SMARTS]


def _hit(m, key):
    return any(m.HasSubstructMatch(p) for p in _BP[key])


@lru_cache(maxsize=200000)
def protocol_flags(smiles):
    s = species(smiles)
    m = Chem.MolFromSmiles(s['parent_smiles']) if s['parent_smiles'] else None
    if m is None:
        return None
    n_strong = sum(len(m.GetSubstructMatches(p)) for p in _BP['strong_acid'][:2] + _BP['strong_acid'][3:])
    return dict(strong_acid=_hit(m, 'strong_acid'), strong_base=_hit(m, 'strong_base'),
                surfactant=_hit(m, 'surfactant_tail') and (_hit(m, 'surfactant_head') or s['species_class'].startswith('permanent')),
                amino_acid_like=_hit(m, 'amino_acid_like') or s['species_class'] == 'permanent_zwitterion',
                polyol=_hit(m, 'polyol_sugar'), mw=_D.MolWt(m), n_strong_acid=n_strong)


def category(smiles, endpoint, miscible=None):
    """-> dict(category in {'A','B','C','not_assessed'}, subtype, display in {'refuse','caveat','normal'}, flags, reason).
    display: 'refuse' = show NO number ("not physically defined for this compound" for A; "defined only for a neutral form that does
    not exist in the environment" for B-unpopulated); 'caveat' = show the number with the reason text prominently; 'normal'.
    miscible: label-table flag if known."""
    d, why = definedness(smiles, endpoint)
    s = species(smiles)
    if s['species_class'] == 'unparseable':
        return dict(category='not_assessed', subtype='unparseable', display='caveat', reason=why)
    if not d:
        return dict(category='A', subtype='permanent_charge:' + s['species_class'], display='refuse', reason=why)
    if s['species_class'] == 'metal_containing_not_assessed' and endpoint.startswith('pka'):
        return dict(category='not_assessed', subtype='metal_containing', display='caveat', reason='metal-containing: ionisable sites not assessed')
    if endpoint == 'pka_acidic':
        pm = Chem.MolFromSmiles(s['parent_smiles']) if s['parent_smiles'] else None
        if pm is not None and sum(a.GetTotalNumHs() for a in pm.GetAtoms()) == 0:
            return dict(category='A', subtype='no_hydrogen', display='refuse', reason='UNDEFINED: an acidic pKa needs a proton to give; the neutral parent has no hydrogen atom')
    if endpoint.startswith('pka') and why.startswith('not applicable'):
        return dict(category='B', subtype='no_site_in_aqueous_window(heuristic)', display='caveat', reason='NOT MEASURABLE BY THE STANDARD (AQUEOUS) PROTOCOL (heuristic): '
                    + why.split(': ', 1)[1] + '. Every molecule has some extreme acidity/basicity, but outside roughly pKa -2..14 '
                    'the aqueous value can only be extrapolated, so such labels are not comparable with titrated values')
    if endpoint == 'water_solubility' and miscible:
        return dict(category='A', subtype='miscible_liquid', display='refuse', reason='UNDEFINED: a liquid miscible with water in all proportions has no finite solubility; a numeric label encodes "miscible", not a measurement')
    req = ENDPOINT_REQUIRES[endpoint][0]
    if s['species_class'] == 'metal_containing_not_assessed' and req is not None:
        return dict(category='not_assessed', subtype='metal_containing', display='caveat', reason=why)
    f = protocol_flags(smiles)
    B = []
    if f:
        if endpoint == 'logkow':
            if f['strong_acid']: B.append(('unpopulated_neutral:strong_acid', 'no buffer pH exists at which a strong acid (pKa below ~1) is un-ionised, so OECD 107/117/123 return a distribution ratio D, not Kow'))
            if f['strong_base']: B.append(('unpopulated_neutral:strong_base', 'no buffer pH exists at which a strong base (amidine/guanidine, pKa above ~12) is un-ionised, so the measured value is D'))
            if f['surfactant']: B.append(('surfactant', 'surface-active: OECD 107/117 are not applicable (emulsions, interfacial accumulation)'))
            if f['amino_acid_like']: B.append(('inner_salt', 'amino-acid-like: zwitterionic at every buffer pH, so the measured value is D at the isoelectric point, not Kow of the uncharged tautomer'))
        if endpoint in ('henry', 'logkoa'):
            if f['amino_acid_like']: B.append(('inner_salt', 'amino-acid-like: zwitterionic in water at every pH; only an effective air partition is observable'))
        if endpoint in ('henry', 'logkoa', 'vapor_pressure', 'boiling_point', 'koh_gas') and (f['strong_acid'] or f['strong_base']):
            B.append(('unpopulated_neutral:strong_acid_or_base', 'defined only for a neutral microspecies that is essentially unpopulated '
                      'at any environmental pH (strong acid pKa below ~1 or strong base pKa above ~12): in the environment the compound exists '
                      'as a non-volatile ion, like a permanent ion. A value measured on the pure free acid/base is a property of a different '
                      'species from the one in the environment. (Extension of BB note Q003, which groups sulfonate/sulfate salts with '
                      'permanent ions; our derivation keeps them separate because a neutral form exists in principle.)'))
        if endpoint == 'boiling_point':
            if f['amino_acid_like']: B.append(('decomposes:inner_salt', 'amino-acid-like inner salt: decomposes before boiling'))
            if f['polyol']: B.append(('decomposes:polyol', 'polyol/sugar: decomposes before boiling at 1 atm'))
            if f['mw'] > 600: B.append(('decomposes:mw>600', f'neutral parent MW {f["mw"]:.0f} g/mol > 600: an atmospheric boiling point is usually not reachable before decomposition'))
            if f['n_strong_acid'] >= 2: B.append(('decomposes:polyacid', '>= 2 strong-acid groups: decomposes before boiling'))
        if endpoint == 'melting_point' and f['amino_acid_like']:
            B.append(('decomposes:inner_salt', 'amino-acid-like inner salt: reported melting points are usually decomposition temperatures'))
        if endpoint == 'koh_gas' and f['mw'] > 500:
            B.append(('low_volatility', f'neutral parent MW {f["mw"]:.0f} g/mol > 500: gas-phase kOH methods need measurable vapour'))
        if endpoint == 'water_solubility' and f['surfactant']:
            B.append(('surfactant', 'surface-active: solubility above the CMC is micellar, not molecular'))
    if B:
        sub = '+'.join(b[0] for b in B)
        disp = 'refuse' if ('unpopulated_neutral' in sub or 'inner_salt' in sub and endpoint in ('logkow', 'henry', 'logkoa')) else 'caveat'
        return dict(category='B', subtype=sub, display=disp, reason='DEFINED BUT NON-EQUIVALENT / NOT MEASURABLE BY THE STANDARD PROTOCOL (heuristic): ' + '; '.join(b[1] for b in B))
    caveat = ''
    flags = []
    if s['removed_fragments'] and endpoint in ('melting_point', 'water_solubility', 'boiling_point', 'vapor_pressure') \
            and s['species_class'] == 'neutralisable':
        flags.append('species_mismatch')
        caveat += (f" SPECIES MISMATCH: the input is a salt/multi-component form; the value is for the neutral parent "
                   f"{s['parent_smiles']}. The salt's own {endpoint.replace('_', ' ')} differs, often by a lot.")
    if endpoint in ('boiling_point', 'vapor_pressure') and f and s['species_class'] == 'neutralisable':
        pm = Chem.MolFromSmiles(s['parent_smiles'])
        if pm is not None and any(pm.HasSubstructMatch(q) for q in _LABILE):
            flags.append('thermally_labile_possible')
            caveat += ' Possible thermal decomposition before boiling (peroxide/azo/diazo/azide/polynitro group); cannot be decided from structure.'
    if endpoint in ('koc', 'bcf') and s['species_class'].startswith('permanent'):
        flags.append('ionic_condition_specific')
        caveat += (' Caveat: for a permanent ion the value is matrix- and pH-dependent (Koc: cation exchange on clay/CEC dominates, '
                   'so f_oc normalisation is weak; BCF: ion trapping); report the test conditions.')
    if False and endpoint == 'koc' and s['species_class'].startswith('permanent'):
        caveat = ' Caveat: sorption of a permanent ion is governed by cation exchange; report Kd with the sorbent CEC and OC (OECD 106 batch equilibrium; HPLC screening OECD 121 is not valid for ions).'
    return dict(category='C', subtype='defined_measurable', display='normal' if not flags else 'caveat', flags=flags, reason='DEFINED AND MEASURABLE: ' + why.replace('defined: ', '') + '.' + caveat)


CAT_TESTS = [('OS(=O)(=O)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)F', 'logkow', 'B'),
             ('NC(N)=N', 'logkow', 'B'), ('CS(=O)(=O)O', 'vapor_pressure', 'B'), ('CS(=O)(=O)[O-].[Na+]', 'henry', 'B'), ('NCC(=O)O', 'boiling_point', 'B'), ('NCC(=O)O', 'logkow', 'B'),
             ('CCCCCCCCCCCCOS(=O)(=O)[O-].[Na+]', 'water_solubility', 'B'), ('CCO', 'water_solubility', 'C'),
             ('C[N+](C)(C)C', 'koc', 'C'), ('C[N+](C)(C)C', 'henry', 'A'), ('CCCCCC', 'pka_acidic', 'B'), ('FC(F)(F)C(F)(F)F', 'pka_acidic', 'A'), ('CN(C)C(=O)C', 'pka_basic', 'C'),
             ('CC(=O)O', 'pka_acidic', 'C'), ('c1ccccc1O', 'logkow', 'C'), ('CC(=O)O', 'logkow', 'C')]


TESTS = [  # (smiles, endpoint, expected defined) - checks that drawing does not change the answer
    ('CCN.Cl', 'henry', True), ('CC[NH3+].[Cl-]', 'henry', True), ('CC[NH3+].[Cl-]', 'logkow', True),
    ('CC(=O)[O-].[Na+]', 'logkow', True), ('CC(=O)[O-].[Na+]', 'henry', True), ('CC(=O)O', 'henry', True),
    ('C[N+](C)(C)C.[Cl-]', 'henry', False), ('C[N+](C)(C)C.[Cl-]', 'logkow', False), ('C[N+](C)(C)C.[Cl-]', 'koc', True),
    ('CCCCCCCCCCCCCCCC[N+](C)(C)C.[Br-]', 'logkow', False), ('C[n+]1ccccc1', 'vapor_pressure', False),
    ('C[N+](C)(C)CC(=O)[O-]', 'logkow', False), ('C[N+](C)(C)CC(=O)O', 'logkow', False),  # betaine, both drawings
    ('O=S(=O)([O-])C(F)(F)C(F)(F)C(F)(F)C(F)(F)F.[K+]', 'logkow', True), ('O=[N+]([O-])c1ccccc1', 'henry', True),
    ('C[N+](C)(C)[O-]', 'henry', True), ('[B-](c1ccccc1)(c1ccccc1)(c1ccccc1)c1ccccc1.[Na+]', 'henry', False),
    ('CC[N+](CC)(CC)CC.CC[N+](CC)(CC)CC.O=C([O-])c1ccccc1C(=O)[O-]', 'henry', False),
    ('CCN(CC)CC', 'henry', True), ('CCCC[Sn](CCCC)(CCCC)Cl', 'henry', True), ('c1ccccc1', 'melting_point', True),
]


def run_tests():
    bad = []
    for s, e, exp in TESTS:
        d, r = definedness(s, e)
        if d != exp:
            bad.append((s, e, exp, d, r))
    return bad


if __name__ == '__main__':
    rules = dict(version='v3', expert_note='BB_EXPERT_NOTE_Q003.md unreadable (Permission denied); derived from first principles',
                 endpoint_requires={k: dict(requires=v[0], definition=v[1]) for k, v in ENDPOINT_REQUIRES.items()},
                 species_capability={k: dict(gas_phase_form=v[0], neutral_microspecies=v[1]) for k, v in CAPABILITY.items()},
                 species_text=SPECIES_TEXT, rule='UNDEFINED := endpoint requires X AND species lacks X; species after Cleanup -> '
                 'largest organic fragment -> Uncharger; metal-containing parents not assessed; pKa site absence is a separate '
                 '"not applicable (heuristic)" state', acid_sites=ACID_SITES, base_sites=BASE_SITES, category_B_smarts=B_SMARTS, thermally_labile_flag_smarts=LABILE_SMARTS,
                 three_way='A undefined by definition / B defined but non-equivalent or not measurable by the standard protocol (heuristic) / C defined and measurable')
    json.dump(rules, open('W-SPACE/domain_rules.json', 'w'), indent=1)
    for s, e, exp in TESTS:
        d, r = definedness(s, e)
        print('OK ' if d == exp else 'FAIL', f'{s:60s} {e:15s} -> {d}  {species(s)["species_class"]}: {r[:110]}')
    for s in ['CCCCCCCCCCCCCCCC[N+](C)(C)C.[Br-]', 'C[N+](C)(C)C', 'CCCCCC', 'OC(=O)C(F)(F)C(F)(F)C(F)(F)F']:
        print(s, 'acidic', pka_site(s, 'acidic'), 'basic', pka_site(s, 'basic'))
    b = run_tests(); print('FAILED TESTS:', len(b))
    nb = 0
    for sm, e, exp in CAT_TESTS:
        c = category(sm, e); ok = c['category'] == exp; nb += (not ok)
        print('OK ' if ok else 'FAIL', sm[:50], e, c['category'], c['subtype'], c['reason'][:100])
    print('FAILED CATEGORY TESTS:', nb)
