#!/usr/bin/env python
"""Optional LIVE mode for the dashboard (the page also works offline from file:// with the
pre-computed predictions embedded in it, or with a predictions JSON loaded from disk).

  python serve.py [--port 8765] [--epi-live]
  then open http://127.0.0.1:8765/   (binds to localhost only)

API (used by index.html when served from here):
  GET  /api/models                 -> frozen models discovered
  POST /api/predict  {"smiles": "...", "smiles_list": [...], "spectrum": {...}}  -> {"job": id}
  GET  /api/job/<id>               -> {"status", "log":[...], "elapsed_s", "result"}
Jobs run one at a time (physics relaxations are seconds per molecule); the page polls and shows
every stage with its elapsed time, so the wait is visible, not hidden.
"""
import argparse, json, os, sys, threading, time, uuid
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import wtool_backend as B

DASH = os.path.join(os.path.dirname(HERE), 'dashboard')
JOBS, LOCK = {}, threading.Lock()
EPI_LIVE = False


def run_job(jid, smiles_list, spectrum, physics=False):
    j = JOBS[jid]
    t0 = time.time()
    def say(s):
        j['log'].append(dict(t=round(time.time() - t0, 2), msg=s))
    with LOCK:
        j['status'] = 'running'
        try:
            models = B.discover_models()
            recs = []
            for i, s in enumerate(smiles_list):
                t = time.time()
                r = B.predict_record(s, spectrum, models, EPI_LIVE, physics=physics, progress=lambda m: say(f'[{i+1}/{len(smiles_list)}] {m}'))
                r['seconds_total'] = round(time.time() - t, 2)
                recs.append(r)
            j['result'] = dict(schema='wtool_predictions/v3', created_utc=B.now(),
                               models=[{k: v for k, v in m.items() if k != 'meta'} for m in models], records=recs)
            j['status'] = 'done'
        except Exception as e:
            j['status'] = 'error'; say(repr(e)[:300])
        j['elapsed_s'] = round(time.time() - t0, 2)


class H(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=DASH, **k)

    def _json(self, obj, code=200):
        b = json.dumps(obj, default=str).encode()
        self.send_response(code); self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(b))); self.end_headers(); self.wfile.write(b)

    def do_GET(self):
        if self.path == '/api/models':
            return self._json([{k: v for k, v in m.items() if k != 'meta'} for m in B.discover_models()])
        if self.path.startswith('/api/job/'):
            j = JOBS.get(self.path.rsplit('/', 1)[-1])
            if not j:
                return self._json({'error': 'no such job'}, 404)
            out = dict(j); out['elapsed_s'] = j.get('elapsed_s') or round(time.time() - j['t0'], 2)
            return self._json(out)
        return super().do_GET()

    def do_POST(self):
        if self.path != '/api/predict':
            return self._json({'error': 'unknown'}, 404)
        n = int(self.headers.get('Content-Length', 0))
        try:
            body = json.loads(self.rfile.read(n) or b'{}')
        except Exception:
            return self._json({'error': 'bad json'}, 400)
        sl = body.get('smiles_list') or ([body['smiles']] if body.get('smiles') else [None])
        sl = sl[:500]
        if sl == [None] and not body.get('spectrum'):
            return self._json({'error': 'need smiles or spectrum'}, 400)
        jid = uuid.uuid4().hex[:10]
        JOBS[jid] = dict(status='queued', log=[], t0=time.time(), n=len(sl))
        threading.Thread(target=run_job, args=(jid, sl, body.get('spectrum'), bool(body.get('physics')) and len(sl) == 1), daemon=True).start()
        return self._json({'job': jid})


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--port', type=int, default=8765)
    ap.add_argument('--no-epi', action='store_true', help='do not contact the EPI Suite web API (cache only)'); a = ap.parse_args()
    EPI_LIVE = not a.no_epi
    print(f'serving {DASH} on http://127.0.0.1:{a.port}/', flush=True)
    ThreadingHTTPServer(('127.0.0.1', a.port), H).serve_forever()
