"""Headless browser driver (QtWebEngine = Chromium, offscreen) for the dashboard.

  python shoot.py PAGE.html OUT_PREFIX script.json [--w 1280 --h 900]
script.json: list of steps {"js": "...", "wait_ms": 800, "shot": "name", "full": true, "eval": "expr"}.
Each 'shot' saves OUT_PREFIX_name.png (full=true: grows the viewport to the page height). 'eval' results and
JS console messages (errors included) are written to OUT_PREFIX_log.json. Used for: layout checks, usability
review screenshots, colour-blind simulation input, and the demo frame sequence.
"""
import json, os, sys
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('QTWEBENGINE_CHROMIUM_FLAGS', '--no-sandbox --disable-gpu --disable-software-rasterizer')
os.environ.setdefault('QTWEBENGINE_DISABLE_SANDBOX', '1')
from PyQt6.QtCore import QUrl, QTimer, QSize
from PyQt6.QtWidgets import QApplication
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage

page_path, prefix, script = sys.argv[1], sys.argv[2], json.load(open(sys.argv[3]))
W = int(sys.argv[sys.argv.index('--w') + 1]) if '--w' in sys.argv else 1280
H = int(sys.argv[sys.argv.index('--h') + 1]) if '--h' in sys.argv else 900
LOG = dict(console=[], evals={}, shots=[])


class Page(QWebEnginePage):
    def javaScriptConsoleMessage(self, level, msg, line, src):
        LOG['console'].append(dict(level=str(level), msg=msg, line=line, src=src[-60:]))


app = QApplication(sys.argv)
v = QWebEngineView(); p = Page(v); v.setPage(p); v.resize(W, H); v.show()
steps = list(script)


def run_next():
    if not steps:
        json.dump(LOG, open(prefix + '_log.json', 'w'), indent=1); app.quit(); return
    st = steps.pop(0)
    def after_js(_=None):
        def do_eval():
            if 'eval' in st:
                p.runJavaScript(st['eval'], lambda r: (LOG['evals'].__setitem__(st.get('name', st['eval'][:40]), r), shot()))
            else:
                shot()
        QTimer.singleShot(int(st.get('wait_ms', 600)), do_eval)
    def shot():
        if 'shot' not in st:
            return run_next()
        if st.get('full'):
            p.runJavaScript('Math.max(document.body.scrollHeight, document.documentElement.scrollHeight)', lambda hh: grow(hh))
        else:
            save()
    def grow(hh):
        v.resize(W, min(int(hh or H) + 20, 12000)); QTimer.singleShot(700, save)
    def save():
        fn = f"{prefix}_{st['shot']}.png"; v.grab().save(fn); LOG['shots'].append(fn)
        if st.get('full'):
            v.resize(W, H)
        QTimer.singleShot(300, run_next)
    if 'js' in st:
        p.runJavaScript(st['js'], after_js)
    else:
        after_js()


def loaded(ok):
    LOG['loaded'] = ok
    QTimer.singleShot(1200, run_next)


v.loadFinished.connect(loaded)
v.load(QUrl.fromLocalFile(os.path.abspath(page_path)) if not page_path.startswith('http') else QUrl(page_path))
QTimer.singleShot(240000, lambda: (json.dump(LOG, open(prefix + '_log.json', 'w'), indent=1), app.quit()))
app.exec()
