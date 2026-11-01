#!/usr/bin/env bash
# Text + PNG review pack of the built dashboard (for reviewers who cannot open a browser): shots/review_pack.txt
cd "$(dirname "$0")/.."
python tool/shoot.py dashboard/index.html shots/pack tool/steps_review_pack.json >/dev/null 2>&1
python -c "
import json; L=json.load(open('shots/pack_log.json'))
open('shots/review_pack.txt','w').write('\n\n'.join('='*20+' '+k+' '+'='*20+'\n'+str(v)[:9000] for k,v in L['evals'].items()))"
