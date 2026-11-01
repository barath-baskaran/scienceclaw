"""Re-embed good_v3.json + current v3/*.js into index.html WITHOUT re-running the models (W-TOOL run 4).
Same assembly as build_v3.py; example predictions in data_v3.json are unchanged."""
import json, os
D = os.path.dirname(os.path.abspath(__file__))
DATA = json.load(open(os.path.join(D, 'data_v3.json')))
DATA['good'] = json.load(open(os.path.join(D, 'good_v3.json')))
def clean(o):
    if isinstance(o, float): return o if o == o and abs(o) != float('inf') else None
    if isinstance(o, dict): return {k: clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)): return [clean(v) for v in o]
    return o
DATA = clean(DATA)
DATA['build']['version'] = 'W-TOOL dashboard v3 (run 4 re-embed: CIs + gated WS naive)'
js = ''.join(open(os.path.join(D, 'v3', f)).read() + '\n' for f in ['a_core.js', 'b_render.js', 'c_ui.js', 'd_init.js'])
data_js = 'window.__DATA__=' + json.dumps(DATA, default=str, allow_nan=False).replace('</', '<\\/') + ';'
html = open(os.path.join(D, 'v3_head.html')).read() + '<script>' + data_js + '</script>\n<script>\n' + js + '</script>\n</body></html>\n'
assert 'http://' not in js.replace('http://127.0.0.1', '') and 'https://' not in js
open(os.path.join(D, 'index.html'), 'w').write(html)
json.dump(DATA, open(os.path.join(D, 'data_v3.json'), 'w'), default=str, indent=0)
print('wrote index.html', len(html))
