#!/usr/bin/env bash
# start|stop the local dashboard server for tests/recording (127.0.0.1 only), tracked by a pidfile.
cd "$(dirname "$0")/.."
PIDF=tool/serve.pid
case "$1" in
 start) nohup bash start_dashboard.sh > tool/serve.log 2>&1 & echo $! > $PIDF; sleep 4; echo started $(cat $PIDF);;
 stop) [ -f $PIDF ] && kill $(cat $PIDF) 2>/dev/null; sleep 1; pkill -u "$(id -u)" -f "W-TOOL/tool/serve.py" 2>/dev/null; rm -f $PIDF; echo stopped;;
esac
