"""Automated checks of the built dashboard in a real Chromium engine (QtWebEngine offscreen, via tool/shoot.py).
For every embedded example (structure and spectrum): renders it, then checks that EVERY endpoint row carries the
required fields (value + interval + 'nominal' next to empirical coverage + domain tag + EPI cell or explicit
'no EPI comparator'), or a refusal ('not physically defined' / 'no ionisable site') with a reason and NO number.
Also: JS console errors, horizontal overflow at 1280 px and 390 px (phone), WCAG text contrast (AA 4.5:1), and
an offline 'new structure' attempt must produce a loud explanation. Output: shots/check_report.json (+ PNGs).
"""
import json, os, subprocess, sys
D = os.path.dirname(os.path.abspath(__file__)); W = os.path.dirname(D)
page = sys.argv[1] if len(sys.argv) > 1 else os.path.join(D, 'index.html')
data = json.load(open(os.path.join(D, 'data_v3.json')))
CHECK_ROWS = r'''(function(){var out=[];document.querySelectorAll('section:not(.hid) table.res tbody tr.main').forEach(function(tr){var t=tr.innerText;var name=(tr.querySelector('td.prop b')||{}).innerText;
 var und=!!tr.querySelector('td.undef'), nomodel=/no model for this property/i.test(t);
 var hasNum=/-?\d+\.\d\d/.test((tr.children[1]||{}).innerText||'');
 var cls=/PR-AUC/.test(t)&&/base rate/.test(t);var ok= und ? (/Why/.test(t) && !hasNum) : nomodel ? true : cls ? /probability/.test(t) : (tr.children.length>=5 && /nominal/.test(t) && /to/.test((tr.children[2]||{}).innerText||'') && /familiar|new to the model|somewhat new|unknown|not assessed/.test(t) && (tr.children.length<6 || ((tr.children[5]||{}).innerText||'').trim().length>0));
 out.push({name:name,ok:ok,undefined:und,nomodel:nomodel,text:ok?'':t.slice(0,300)});});return JSON.stringify(out);})()'''
CONTRAST = r'''(function(){function rgb(s){var m=s.match(/[\d.]+/g);return m?m.map(Number):[0,0,0,1];}
function lum(c){var a=c.slice(0,3).map(function(v){v/=255;return v<=0.03928?v/12.92:Math.pow((v+0.055)/1.055,2.4);});return 0.2126*a[0]+0.7152*a[1]+0.0722*a[2];}
function bg(el){while(el){var c=rgb(getComputedStyle(el).backgroundColor);if(c.length<4||c[3]>0.5)return c;el=el.parentElement;}return [255,255,255,1];}
var bad=[],n=0,minr=99;document.querySelectorAll('body *').forEach(function(el){if(!el.childNodes.length)return;var txt=Array.prototype.some.call(el.childNodes,function(c){return c.nodeType===3&&c.textContent.trim().length>1;});
 if(!txt||el.offsetParent===null)return;var cs=getComputedStyle(el);var a=lum(rgb(cs.color)),b=lum(bg(el));var r=(Math.max(a,b)+0.05)/(Math.min(a,b)+0.05);n++;minr=Math.min(minr,r);
 var big=parseFloat(cs.fontSize)>=18.7||(parseFloat(cs.fontSize)>=14&&+cs.fontWeight>=700);if(r<(big?3:4.5))bad.push({t:el.innerText.slice(0,40),r:Math.round(r*100)/100,color:cs.color,fs:cs.fontSize});});
 return JSON.stringify({n:n,min:Math.round(minr*100)/100,fails:bad.slice(0,15),n_fail:bad.length});})()'''
OVER = "JSON.stringify({sw:document.documentElement.scrollWidth,cw:document.documentElement.clientWidth,minfont:Math.min.apply(null,Array.prototype.map.call(document.querySelectorAll('body *'),function(e){return e.offsetParent?parseFloat(getComputedStyle(e).fontSize):99;}))})"
steps = []
for i, e in enumerate(data['examples']):
    steps += [{'js': f"document.getElementById('m-struct').click();document.querySelectorAll('#exchips .chip')[{i}].click()", 'wait_ms': 700,
               'eval': CHECK_ROWS, 'name': f'rows_ex{i}', 'shot': f'ex{i}', 'full': True}]
for i, e in enumerate(data['spec_examples']):
    steps += [{'js': f"document.getElementById('m-spec').click();document.querySelectorAll('#specchips .chip')[{i}].click()", 'wait_ms': 700,
               'eval': CHECK_ROWS, 'name': f'rows_spec{i}', 'shot': f'spec{i}', 'full': True}]
steps += [{'js': "document.getElementById('m-struct').click();document.querySelectorAll('#exchips .chip')[0].click();document.querySelectorAll('tr.main[data-det]').forEach(function(t){t.click();})", 'wait_ms': 600, 'eval': CONTRAST, 'name': 'contrast_expanded'},
          {'eval': OVER, 'name': 'overflow_1280'},
          {'js': "document.getElementById('m-good').click()", 'wait_ms': 400, 'eval': CONTRAST, 'name': 'contrast_good', 'shot': 'good', 'full': True},
          {'js': "document.getElementById('m-struct').click();document.getElementById('smi').value='CCOC(=O)c1ccc(OC(F)(F)F)cc1';document.getElementById('go').click()", 'wait_ms': 400,
           'eval': "document.getElementById('msg').innerText", 'name': 'offline_new_structure', 'shot': 'offline_new'},
          {'js': "document.getElementById('smi').value='';document.getElementById('go').click()", 'wait_ms': 300, 'eval': "document.getElementById('msg').innerText", 'name': 'empty_input'},
          {'js': "document.getElementById('m-spec').click();document.getElementById('u_peaks').value='91.05 100';document.getElementById('u_go').click()", 'wait_ms': 300, 'eval': "document.getElementById('u_msg').innerText", 'name': 'spec_missing_meta'}]
sp = os.path.join(W, 'shots'); os.makedirs(sp, exist_ok=True)
json.dump(steps, open('/tmp/check_steps.json', 'w'))
py = '<TEAM_ROOT>/envs/swarm/bin/python'
subprocess.run([py, os.path.join(W, 'tool', 'shoot.py'), page, os.path.join(sp, 'chk'), '/tmp/check_steps.json'], capture_output=True, timeout=500)
L = json.load(open(os.path.join(sp, 'chk_log.json')))
# phone width
json.dump([{'js': "document.querySelectorAll('#exchips .chip')[0].click()", 'wait_ms': 700, 'eval': OVER, 'name': 'overflow_390', 'shot': 'phone', 'full': True}], open('/tmp/check_phone.json', 'w'))
subprocess.run([py, os.path.join(W, 'tool', 'shoot.py'), page, os.path.join(sp, 'phone'), '/tmp/check_phone.json', '--w', '390', '--h', '800'], capture_output=True, timeout=200)
L2 = json.load(open(os.path.join(sp, 'phone_log.json')))
rep = dict(page=page, console_errors=[c for c in L['console'] if 'Error' in c['level']], rows={}, other={})
nbad = 0
for k, v in L['evals'].items():
    if k.startswith('rows_'):
        rows = json.loads(v) if v else []
        bad = [r for r in rows if not r['ok']]; nbad += len(bad)
        rep['rows'][k] = dict(n=len(rows), n_undefined=sum(r['undefined'] for r in rows), n_bad=len(bad), bad=bad)
    else:
        rep['other'][k] = json.loads(v) if isinstance(v, str) and v.startswith('{') else v
rep['other']['overflow_390'] = json.loads(L2['evals'].get('overflow_390') or '{}')
rep['summary'] = dict(n_row_checks=sum(r['n'] for r in rep['rows'].values()), n_bad_rows=nbad, n_console_errors=len(rep['console_errors']))
json.dump(rep, open(os.path.join(sp, 'check_report.json'), 'w'), indent=1)
print(json.dumps(rep['summary']), json.dumps({k: (v if not isinstance(v, dict) else {kk: vv for kk, vv in v.items() if kk != 'fails'}) for k, v in rep['other'].items()})[:1500])
for k, v in rep['rows'].items():
    if v['n_bad']:
        print(k, v['bad'][:2])
