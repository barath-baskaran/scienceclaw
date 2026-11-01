"""Q-003 override for W-SPACE domain_rules.definedness (CRITIC, run 3).

BB's expert note ((internal path removed)): "Sulfonate and sulfate salts fall under the
same reasoning as quaternary ammonium cations", i.e. physically UNDEFINED for vapour pressure, boiling
point, Henry, KOA, gas-phase kOH and logKow. domain_rules v3 neutralises them with Uncharger first and
calls them defined. This wrapper applies the note on top of v3 without editing W-SPACE's file.

Usage:  sys.path.insert(0, 'CRITIC'); from q003_override import definedness
        definedness(smiles, endpoint) -> (bool defined, str reason)   # same API as domain_rules
"""
import sys
from rdkit import Chem
sys.path.insert(0, 'W-SPACE')
import domain_rules as _DR

GAS_OR_NEUTRAL = {'vapor_pressure', 'boiling_point', 'henry', 'logkoa', 'koh_gas', 'logkow'}
_SULF = [Chem.MolFromSmarts('[SX4](=O)(=O)[OX2H1,OX1-]')]   # sulfonic acid / sulfonate / sulfate monoester acid or anion


def is_sulfonate_or_sulfate(smiles):
    m = Chem.MolFromSmiles(smiles) if smiles else None
    return bool(m) and any(m.HasSubstructMatch(p) for p in _SULF)


def definedness(smiles, endpoint):
    d, r = _DR.definedness(smiles, endpoint)
    if d and endpoint in GAS_OR_NEUTRAL and is_sulfonate_or_sulfate(smiles):
        return False, ('UNDEFINED (expert note Q-003): a sulfonate/sulfate is a strong-acid anion (conjugate acid '
                       'pKa < ~0) with no populated neutral species in water; like a quaternary ammonium cation it '
                       'does not volatilise and has no neutral-species partition coefficient. This is not missing data.')
    return d, r


if __name__ == '__main__':
    for s in ['O=S(=O)([O-])C(F)(F)C(F)(F)C(F)(F)C(F)(F)F.[K+]', 'CCCCCCCCCCCCOS(=O)(=O)[O-].[Na+]',
              'CCCCCCCCCCCCc1ccc(S(=O)(=O)O)cc1', 'CS(=O)(=O)C', 'COS(=O)(=O)OC', 'CCO']:
        print(s, {e: definedness(s, e)[0] for e in ('logkow', 'vapor_pressure', 'koc', 'water_solubility')})
