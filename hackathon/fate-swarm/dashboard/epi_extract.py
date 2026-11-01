"""Canonical EPI Suite value extraction (W-TOOL, run 3). One function, used by both the canonical
comparator table (build_epi_canonical.py) and the dashboard backend, so the two cannot drift.

Extracts EPI *estimated* values only, converted to labels_v2 units, with an explicit unit check:
if EPI reports a unit we do not expect the value is None (never silently converted).
  logkow            log10 (unitless)          KOWWIN
  water_solubility  log10 mol/L               WSKOWWIN (model.waterSolubility, mg/L) / 1000 / MW
  vapor_pressure    log10 mmHg                MPBPVP (units must be mmHg)
  henry             log10 atm m3/mol          HENRYWIN (units must contain atm)
  melting_point     degC                      MPBPVP (units must be celsius)
  boiling_point     degC                      MPBPVP (units must be celsius)
  koc               log10 L/kg                KOCWIN logKoc
  logkoa            log10 (unitless)          KOAWIN
  koh_gas           log10 cm3/(molecule s)    AOPWIN
  bcf               log10 L/kg wet-wt         BCFBAF regression
  pka_acidic/basic  -- EPI has no pKa module (reported as 'no EPI comparator', never blank)
Same logic as W-LADDER/epi_v2.py (which it was cross-checked against: build_epi_canonical.py reports agreement).
"""
import math

EPI_ENDPOINTS = ['logkow', 'water_solubility', 'vapor_pressure', 'henry', 'melting_point', 'boiling_point',
                 'koc', 'logkoa', 'koh_gas', 'bcf']
EPI_MODULE = dict(logkow='KOWWIN', water_solubility='WSKOWWIN', vapor_pressure='MPBPVP', henry='HENRYWIN',
                  melting_point='MPBPVP', boiling_point='MPBPVP', koc='KOCWIN', logkoa='KOAWIN',
                  koh_gas='AOPWIN', bcf='BCFBAF (regression)')
EPI_UNITS = dict(logkow='log10', water_solubility='log10 mol/L', vapor_pressure='log10 mmHg',
                 henry='log10 atm m3/mol', melting_point='degC', boiling_point='degC', koc='log10 L/kg',
                 logkoa='log10', koh_gas='log10 cm3/(molecule s)', bcf='log10 L/kg wet-wt')
NO_EPI = {'pka_acidic': 'EPI Suite has no pKa module - no EPI comparator',
          'pka_basic': 'EPI Suite has no pKa module - no EPI comparator'}


def _lg(x):
    x = float(x)
    return math.log10(x) if x > 0 else None


def _has_exp(blk):
    try:
        return bool(blk.get('experimentalValues'))
    except Exception:
        return None


def extract(d):
    """dict endpoint -> (value_in_label_units or None, has_experimental_flag)"""
    o = {}

    def safe(k, f, blk):
        try:
            v = f()
            v = None if v is None else float(v)
        except Exception:
            v = None
        try:
            he = _has_exp(d[blk])
        except Exception:
            he = None
        o[k] = (v, he)
    e = lambda k: d[k]['estimatedValue']
    safe('logkow', lambda: e('logKow')['value'], 'logKow')
    safe('melting_point', lambda: e('meltingPoint')['value'] if e('meltingPoint')['units'] == 'celsius' else None, 'meltingPoint')
    safe('boiling_point', lambda: e('boilingPoint')['value'] if e('boilingPoint')['units'] == 'celsius' else None, 'boilingPoint')
    safe('vapor_pressure', lambda: _lg(e('vaporPressure')['value']) if e('vaporPressure')['units'] == 'mmHg' else None, 'vaporPressure')
    safe('water_solubility', lambda: _lg(d['waterSolubilityFromLogKow']['estimatedValue']['model']['waterSolubility'] / 1000.0
                                         / d['chemicalProperties']['molecularWeight']), 'waterSolubilityFromLogKow')
    safe('henry', lambda: _lg(e('henrysLawConstant')['value']) if 'atm' in str(e('henrysLawConstant').get('units', '')).lower() else None, 'henrysLawConstant')
    safe('koc', lambda: e('logKoc')['value'], 'logKoc')
    safe('logkoa', lambda: e('logKoa')['value'], 'logKoa')
    safe('koh_gas', lambda: _lg(d['atmosphericHalfLife']['estimatedHydroxylRadicalReactionRateConstant']['value']), 'atmosphericHalfLife')
    safe('bcf', lambda: d['bioconcentration']['logBioconcentrationFactor'], 'bioconcentration')
    return o
