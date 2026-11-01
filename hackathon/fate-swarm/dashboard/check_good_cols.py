"""Static check (CRITIC review): 'How good is it?' table thead and tbody rows in goodHtml() must have equal column counts.
Counts <th> in the thead literal and <td> in the row literal; the bins.map() term contributes len(bins) to each."""
import re, sys, json
NB = len(json.load(open('good_v3.json')).get('bins', ['<0.3','0.3-0.5','0.5-0.7','>=0.7'])) if isinstance(json.load(open('good_v3.json')).get('bins'), list) else 4
bad = 0
for f in sys.argv[1:] or ['v3/d_init.js', 'index.html']:
    s = open(f, encoding='utf-8').read()
    th = re.search(r"<table class=\"sk\"><thead><tr><th>Property</th>(.*?)</tr></thead>", s).group(0)
    row = re.search(r"h\+='<tr><td>'\+\(i===0.*?</td></tr>';", s, re.S).group(0)
    nth = th.count('<th>') + (NB - 1 if 'bins.map' in th else 0)
    ntd = row.count("<td>") + (NB - 1 if 'bins.map' in row else 0)
    print(f, 'thead', nth, 'tbody', ntd, 'OK' if nth == ntd else 'MISMATCH'); bad += nth != ntd
sys.exit(bad)
