"""Automated screen recording of the dashboard demo (W-TOOL). Follows DEMO_SCRIPT.md.

Needs the local tool running (bash start_dashboard.sh -> 127.0.0.1:8765). Drives a real Chromium engine
(QtWebEngine offscreen), grabs a frame every FRAME_MS, types SMILES character by character, and encodes
an H.264 mp4 with the ffmpeg binary bundled in imageio-ffmpeg. The physics wait is recorded at 1 frame / 2 s and
played back faster (a caption says so). Final scene: the live swarm view (STATUS.txt + board notes tail).
  python record_demo.py OUT.mp4 [URL]
"""
import os, sys, time, json, subprocess, shutil, html
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('QTWEBENGINE_CHROMIUM_FLAGS', '--no-sandbox --disable-gpu --disable-software-rasterizer')
from PyQt6.QtCore import QUrl, QTimer
from PyQt6.QtWidgets import QApplication
from PyQt6.QtWebEngineWidgets import QWebEngineView
import imageio_ffmpeg

OUT = sys.argv[1]; URL = sys.argv[2] if len(sys.argv) > 2 else 'http://127.0.0.1:8765/'
W, H, FPS = 1280, 800, 4
FR = '/tmp/wtool_demo_frames'; shutil.rmtree(FR, ignore_errors=True); os.makedirs(FR)
app = QApplication(sys.argv); v = QWebEngineView(); v.resize(W, H); v.show(); p = v.page()
N = [0]
def frame(k=1):
    img = v.grab()
    for _ in range(k):
        img.save(f'{FR}/f{N[0]:05d}.png'); N[0] += 1
def js(code): p.runJavaScript(code)
CAP = ("(function(t){var d=document.getElementById('demo_cap');if(!d){d=document.createElement('div');d.id='demo_cap';"
       "d.style.cssText='position:fixed;left:0;right:0;bottom:0;background:rgba(0,0,0,.82);color:#fff;font:600 18px system-ui;padding:10px 16px;z-index:99';document.body.appendChild(d);}"
       "d.textContent=t;d.style.display=t?'block':'none';})")
SMI = 'CCOC(=O)c1ccc(OC(F)(F)F)cc1'
# timeline: (action, seconds_to_hold_or_param)
T = []
def cap(t): T.append(('js', CAP + '(' + json.dumps(t) + ')'))
def hold(s): T.append(('hold', s))
cap('A structure nobody has measured: ethyl 4-(trifluoromethoxy)benzoate (not in any of our label sets)'); hold(3)
T.append(('js', "window.scrollTo(0,0);document.getElementById('smi').focus()"))
for i in range(1, len(SMI) + 1):
    T.append(('js', f"document.getElementById('smi').value={json.dumps(SMI[:i])}")); T.append(('hold', 0.12))
hold(1)
T.append(('js', "document.getElementById('usephys').checked=true")); cap('Tick: also compute quantum-chemistry (AIMNet2) descriptors on this laptop'); hold(2.5)
T.append(('js', "document.getElementById('go').click()")); cap('Running: 3D structure, AIMNet2 relaxation on CPU, then the frozen models (this wait is sped up 4x in the video)')
T.append(('wait_done', 'go')); T.append(('probe', 'live'))
cap('Every property: estimate, likely range, how often such ranges held in testing, novelty, and EPI Suite'); T.append(('js', "document.getElementById('out').scrollIntoView()")); hold(5)
T.append(('scroll', 400)); hold(4)
T.append(('js', "document.querySelector('#out tr.main[data-det]').click();document.querySelector('#out tr.main[data-det]').scrollIntoView()"))
cap('Click a row: what drove the estimate, how good the model is on similar test chemicals, everyday units'); hold(6)
T.append(('js', "window.scrollTo(0,0);document.getElementById('usephys').checked=false;Array.prototype.filter.call(document.querySelectorAll('#exchips .chip'),function(b){return /Quaternary/.test(b.textContent);})[0].click()")); T.append(('wait_done', 'go')); T.append(('probe', 'quat'))
T.append(('js', "document.getElementById('out').scrollIntoView()")); cap('A permanently charged quaternary ammonium salt: the tool REFUSES properties that do not exist (no number, a reason)'); hold(4)
T.append(('scroll', 350)); hold(5)
T.append(('js', "window.scrollTo(0,0);document.getElementById('m-spec').click();document.querySelectorAll('#specchips .chip')[0].click()")); T.append(('wait_done', 'u_go')); T.append(('probe', 'spec'))
cap('Spectrum only: an MS/MS spectrum of a test chemical, structure hidden from the model'); hold(4)
T.append(('scroll', 500)); hold(4); T.append(('scroll', 500)); hold(4)
T.append(('js', "window.scrollTo(0,0);document.getElementById('m-good').click()"))
cap('How good is it? Leak-free test error as % of a naive guess, vs EPI Suite on the same chemicals'); hold(5)
T.append(('scroll', 500)); hold(4)
T.append(('status', None)); hold(7)
cap(''); hold(0.5)

idx = [0]; t_wait = [0]; PROBES = {}
def step():
    if idx[0] >= len(T):
        return finish()
    a, x = T[idx[0]]; idx[0] += 1
    if a == 'js':
        js(x); QTimer.singleShot(60, step)
    elif a == 'hold':
        k = max(1, int(round(x * FPS))); frame(k); QTimer.singleShot(int(1000 * x / 3), step)
    elif a == 'scroll':
        js(f'window.scrollBy(0,{x})'); QTimer.singleShot(250, step)
    elif a == 'wait_done':
        def poll():
            p.runJavaScript(f"document.getElementById('{x}').disabled", lambda dis: (frame(2), QTimer.singleShot(2000, poll)) if dis and t_wait[0] < 240 else (QTimer.singleShot(300, step)))
            t_wait[0] += 2
        t_wait[0] = 0 if False else t_wait[0]
        QTimer.singleShot(1500, poll)
    elif a == 'probe':
        p.runJavaScript("(document.getElementById('out').innerText+' || '+document.getElementById('u_out').innerText).slice(0,400)",
                        lambda t, k=x: (PROBES.__setitem__(k, t), QTimer.singleShot(50, step)))
    elif a == 'status':
        st = open('(internal path removed)').read()
        page = '<html><body style="background:#111;color:#e8e8e8;font:14px ui-monospace,monospace;padding:20px"><h2 style="font-family:system-ui">Live swarm view (STATUS.txt)</h2><pre>' + html.escape(st) + '</pre></body></html>'
        v.setHtml(page); QTimer.singleShot(1500, step)
def finish():
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run([ff, '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', f'{FR}/f%05d.png', '-vf', 'scale=1280:-2', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', OUT], check=True)
    json.dump(PROBES, open(OUT + '.probes.json', 'w'), indent=1)
    print('wrote', OUT, N[0], 'frames', f'{N[0]/FPS:.0f} s', {k: len(v or '') for k, v in PROBES.items()}); app.quit()
v.loadFinished.connect(lambda ok: QTimer.singleShot(1500, step))
v.load(QUrl(URL))
QTimer.singleShot(600000, app.quit)
app.exec()
