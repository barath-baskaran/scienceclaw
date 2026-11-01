"""Minimal 2D structure depiction to SVG without RDKit's drawing module.

RDKit's rdMolDraw2D needs libXrender, which is not installed on the VM (system library; no apt).
This uses rdDepictor 2D coordinates and draws the molecule itself: bonds as lines (double/triple drawn
offset toward the ring centre or symmetric), heteroatoms and charged atoms as text labels with their
implicit H count and formal charge, wedges ignored (stereo is written in the SMILES line instead).
Colours: heteroatom text uses Okabe-Ito-ish dark tones but the element symbol is always printed, so
colour carries no information on its own.
"""
import math
from rdkit import Chem
from rdkit.Chem import rdDepictor

COL = {'O': '#B03A00', 'N': '#0050A0', 'S': '#7A6000', 'P': '#8A3C8A', 'F': '#2E6B30', 'Cl': '#2E6B30',
       'Br': '#7A2E1A', 'I': '#5A2A7A'}


def _fmt_charge(c):
    if c == 0:
        return ''
    s = '+' if c > 0 else '−'
    return (str(abs(c)) if abs(c) > 1 else '') + s


def svg(smiles_or_mol, width=320, height=220, pad=22):
    m = Chem.MolFromSmiles(smiles_or_mol) if isinstance(smiles_or_mol, str) else Chem.Mol(smiles_or_mol)
    if m is None:
        return None
    Chem.Kekulize(m, clearAromaticFlags=True)
    rdDepictor.SetPreferCoordGen(True) if hasattr(rdDepictor, 'SetPreferCoordGen') else None
    rdDepictor.Compute2DCoords(m)
    conf = m.GetConformer()
    xy = [(conf.GetAtomPosition(i).x, -conf.GetAtomPosition(i).y) for i in range(m.GetNumAtoms())]
    if not xy:
        return None
    xs, ys = [p[0] for p in xy], [p[1] for p in xy]
    w0, h0 = max(xs) - min(xs) or 1, max(ys) - min(ys) or 1
    sc = min((width - 2 * pad) / w0, (height - 2 * pad) / h0, 40)
    ox = (width - sc * w0) / 2 - sc * min(xs)
    oy = (height - sc * h0) / 2 - sc * min(ys)
    P = [(ox + sc * x, oy + sc * y) for x, y in xy]
    ri = m.GetRingInfo()
    labelled = set()
    for a in m.GetAtoms():
        if a.GetSymbol() != 'C' or a.GetFormalCharge() != 0 or a.GetDegree() == 0 or a.GetIsotope():
            labelled.add(a.GetIdx())
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
           f'role="img" aria-label="2D structure of {Chem.MolToSmiles(Chem.RemoveHs(m)) if m else ""}">',
           '<g stroke="currentColor" stroke-width="1.6" stroke-linecap="round">']
    fs = max(10, min(15, sc * 0.42))
    shrink = fs * 0.62

    def seg(i, j, off=0.0, frac=0.0):
        (x1, y1), (x2, y2) = P[i], P[j]
        dx, dy = x2 - x1, y2 - y1
        L = math.hypot(dx, dy) or 1
        ux, uy = dx / L, dy / L
        nx, ny = -uy, ux
        a = shrink if i in labelled else 0
        b = shrink if j in labelled else 0
        a, b = a + frac * L, b + frac * L
        return (x1 + ux * a + nx * off, y1 + uy * a + ny * off, x2 - ux * b + nx * off, y2 - uy * b + ny * off)

    for bd in m.GetBonds():
        i, j = bd.GetBeginAtomIdx(), bd.GetEndAtomIdx()
        o = bd.GetBondTypeAsDouble()
        lines = []
        if o == 2:
            # offset toward ring centre if in a ring, else symmetric
            rings = [r for r in ri.AtomRings() if i in r and j in r]
            if rings:
                r = rings[0]
                cx = sum(P[k][0] for k in r) / len(r); cy = sum(P[k][1] for k in r) / len(r)
                (x1, y1), (x2, y2) = P[i], P[j]
                nx, ny = -(y2 - y1), (x2 - x1)
                side = 1 if (cx - x1) * nx + (cy - y1) * ny > 0 else -1
                d = side * sc * 0.18
                lines = [seg(i, j), seg(i, j, d, 0.12)]
            else:
                d = sc * 0.09
                lines = [seg(i, j, d), seg(i, j, -d)]
        elif o == 3:
            d = sc * 0.14
            lines = [seg(i, j), seg(i, j, d), seg(i, j, -d)]
        else:
            lines = [seg(i, j)]
        for x1, y1, x2, y2 in lines:
            out.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}"/>')
    out.append('</g><g font-family="Helvetica,Arial,sans-serif" font-weight="600" text-anchor="middle" dominant-baseline="central">')
    for a in m.GetAtoms():
        k = a.GetIdx()
        if k not in labelled:
            continue
        x, y = P[k]
        h = a.GetTotalNumHs()
        lab = a.GetSymbol() + (('H' + (str(h) if h > 1 else '')) if h and a.GetSymbol() != 'C' or (h and a.GetDegree() == 0) else '')
        if a.GetIsotope():
            lab = f'{a.GetIsotope()}{lab}'
        ch = _fmt_charge(a.GetFormalCharge())
        col = COL.get(a.GetSymbol(), 'currentColor')
        out.append(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{fs:.1f}" fill="{col}">{lab}'
                   + (f'<tspan dy="-{fs*0.45:.1f}" font-size="{fs*0.75:.1f}">{ch}</tspan>' if ch else '') + '</text>')
    out.append('</g></svg>')
    return ''.join(out)


if __name__ == '__main__':
    import sys
    for s in sys.argv[1:] or ['CC(C)(C)c1ccc(OCC(F)(F)C(F)F)cc1', 'C[N+](C)(C)CCO.[Cl-]', 'OC(=O)C#N']:
        print(len(svg(s)))
    open('/tmp/depict_test.svg', 'w').write(svg('CC(C)(C)c1ccc(OCC(F)(F)C(F)F)cc1'))
