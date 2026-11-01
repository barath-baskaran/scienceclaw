"""Colour-vision-deficiency check of the dashboard palette and screenshots (W-TOOL).
Machado et al. 2009 simulation matrices (severity 1.0) for protanopia, deuteranopia, tritanopia applied in linear RGB.
1) Pairwise CIELAB dE76 between every pair of meaning-carrying colours, normal and simulated. dE < 10 = hard to tell
   apart by colour alone -> must be (and is) separated by shape/word: reported per pair.
2) Writes simulated versions of a screenshot (shots/cvd_<type>_<name>.png) for visual review.
Output: shots/cvd_report.json
"""
import json, sys, itertools, os
import numpy as np
from PIL import Image
M = {'protanopia': [[0.152286, 1.052583, -0.204868], [0.114503, 0.786281, 0.099216], [-0.003882, -0.048116, 1.051998]],
     'deuteranopia': [[0.367322, 0.860646, -0.227968], [0.280085, 0.672501, 0.047413], [-0.011820, 0.042940, 0.968881]],
     'tritanopia': [[1.255528, -0.076749, -0.178779], [-0.078411, 0.930809, 0.147602], [0.004733, 0.691367, 0.303900]]}
PAL = {'familiar (in) text': '#005a8c', 'somewhat new (edge) text': '#8a6100', 'new (out) text': '#b34700', 'undefined text': '#444444',
       'structure share': '#0072B2', 'physics share': '#E69F00', 'spectrum share': '#CC79A7', 'measured mark': '#b34700', 'interval box': '#cfe3f1', 'familiar tag background': '#e3f0f8', 'somewhat new tag background': '#fdf1d6', 'new tag background (filled, white text)': '#a33a00'}
SHAPE = {'familiar (in) text': '● + word', 'somewhat new (edge) text': '▲ + word', 'new (out) text': '✖ + word', 'undefined text': '⊘ + dashed border + word',
         'structure share': 'solid fill + label', 'physics share': 'diagonal hatch + label', 'spectrum share': 'dot pattern + label', 'measured mark': '× shape', 'interval box': 'box shape', 'familiar tag background': '●', 'somewhat new tag background': '▲', 'new tag background (filled, white text)': '✖'}
def lin(c): c = c / 255.0; return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
def delin(c): return np.clip(np.where(c <= 0.0031308, 12.92 * c, 1.055 * np.power(np.clip(c, 0, None), 1 / 2.4) - 0.055), 0, 1) * 255
def hex2(h): return np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)], float)
def lab(rgb):
    l = lin(rgb); X = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]]) @ l
    X = X / np.array([0.95047, 1.0, 1.08883]); f = np.where(X > 0.008856, np.cbrt(X), 7.787 * X + 16 / 116)
    return np.array([116 * f[1] - 16, 500 * (f[0] - f[1]), 200 * (f[1] - f[2])])
def sim(rgb, t): return delin(np.array(M[t]) @ lin(rgb))
rep = {'pairs': {}, 'note': 'dE76 in CIELAB; <10 = confusable by colour alone. Every meaning also has a shape/word (column redundancy).'}
groups = [['familiar (in) text', 'somewhat new (edge) text', 'new (out) text', 'undefined text'], ['structure share', 'physics share', 'spectrum share'], ['familiar tag background', 'somewhat new tag background', 'new tag background (filled, white text)']]
for g in groups:
    for a, b in itertools.combinations(g, 2):
        r = {'normal': float(np.linalg.norm(lab(hex2(PAL[a])) - lab(hex2(PAL[b]))))}
        for t in M:
            r[t] = float(np.linalg.norm(lab(sim(hex2(PAL[a]), t)) - lab(sim(hex2(PAL[b]), t))))
        r['redundant_cue'] = f'{SHAPE[a]} vs {SHAPE[b]}'
        rep['pairs'][f'{a} | {b}'] = {k: (round(v, 1) if isinstance(v, float) else v) for k, v in r.items()}
for shot in sys.argv[1:]:
    im = np.asarray(Image.open(shot).convert('RGB')).astype(float)
    for t in M:
        out = delin(np.einsum('ij,hwj->hwi', np.array(M[t]), lin(im))).astype(np.uint8)
        fn = os.path.join(os.path.dirname(shot), f'cvd_{t}_{os.path.basename(shot)}'); Image.fromarray(out).save(fn)
json.dump(rep, open('W-TOOL/shots/cvd_report.json', 'w'), indent=1)
for k, v in rep['pairs'].items(): print(k, v)
