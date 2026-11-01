#!/usr/bin/env bash
# Start the fate & hazard dashboard on THIS computer only (binds 127.0.0.1; nothing is reachable from outside).
# Then open http://127.0.0.1:8765 in a browser. Ctrl-C stops it.
# Offline: works without internet; only the EPI Suite comparison needs internet (skipped with --no-epi or when unreachable).
HERE="$(cd "$(dirname "$0")" && pwd)"
PY="${PYTHON:-python}"
[ -x "$PY" ] || PY=python3
export AIMNET2_CKPT="${AIMNET2_CKPT:-(internal path removed)}"
echo "Dashboard: http://127.0.0.1:${PORT:-8765}/   (Ctrl-C to stop)"
exec "$PY" "$HERE/tool/serve.py" --port "${PORT:-8765}" "$@"
