"""Link-resolution gate for the public repo (W-TOOL, for PRINCIPAL D2).

Every markdown link/image target `[..](path)` / `![..](path)` and every back-ticked path-like token in a
.md file must either
  (a) resolve to a file or directory inside the repo - tried relative to the .md file's own folder, then to
      the repo root (glob characters allowed: the pattern must match at least one file), or
  (a2) [warning only] be a bare file name (no '/') that exists somewhere else in the repo, or
  (b) be explicitly annotated as VM-internal: within 80 characters AFTER the token (run 4: per token, not per line), the text contains "VM-internal" or "vm-internal"
      (case-insensitive), or "[not redistributed" (the existing whitepaper convention).
URLs (http/https/mailto/doi:) and in-page anchors (#...) are not checked.
A back-ticked token counts as a path if it has no spaces, no '(' '=' '<' '>' or quotes, and either contains a '/'
or ends in a file extension from EXT. ':line' and '#anchor' suffixes are stripped before resolving.

Usage:  python link_gate.py <repo_dir> [--report out.tsv]   (exit 1 if any unresolved, un-annotated link)
Also called from scan_repo.py, where an unresolved link is a BLOCKING hit ("BLOCK link_unresolved").
"""
import glob, os, re, sys, pathlib

EXT = ('py', 'md', 'json', 'jsonl', 'csv', 'tsv', 'parquet', 'png', 'svg', 'jpg', 'pdf', 'html', 'js', 'sh', 'txt',
       'mp4', 'extxyz', 'sqlite', 'txt', 'yaml', 'yml', 'log', 'pt', 'pkl', 'joblib', 'npz', 'npy', 'zip', 'gz')
MDLINK = re.compile(r'!?\[[^\]]*\]\(\s*<?([^)\s>]+)>?(?:\s+"[^"]*")?\s*\)')
TICK = re.compile(r'`([^`\n]+)`')
EXT_RE = re.compile(r'\.(' + '|'.join(EXT) + r')$', re.I)
ANNOT_WINDOW = 80
ANNOT = re.compile(r'(vm-internal|\[not redistributed)', re.I)


def is_pathlike(t):
    if not t or ' ' in t or any(c in t for c in '(=<>"\',;{}|$') or t.startswith(('-', 'http', 'www.')):
        return False
    if re.fullmatch(r'[\d.eE+\-%/]+', t):          # numbers, ratios like 6/9
        return False
    core = re.sub(r'(:\d+(-\d+)?|#.*)$', '', t)
    return ('/' in core and re.search(r'[A-Za-z]', core) is not None and not core.endswith('/s')) or bool(EXT_RE.search(core))


def clean(t):
    t = re.sub(r'#.*$', '', t)
    t = re.sub(r':\d+(-\d+)?$', '', t)
    return t.rstrip('.,')


def resolves(t, mddir, root):
    for base in (mddir, root):
        cand = (base / t)
        if any(c in t for c in '*?['):
            if glob.glob(str(cand)):
                return True
        elif cand.exists():
            try:
                cand.resolve().relative_to(root)       # must stay inside the repo
                return True
            except ValueError:
                pass
    return False


def scan(root):
    root = pathlib.Path(root).resolve()
    out = []   # (status, file:line, kind, target)
    names = {p.name for p in root.rglob('*') if '.git' not in p.parts}
    for md in sorted(root.rglob('*.md')):
        if '.git' in md.parts:
            continue
        rel = md.relative_to(root)
        infence = False
        for i, line in enumerate(md.read_text(errors='ignore').splitlines(), 1):
            if line.strip().startswith('```'):
                infence = not infence
                continue
            if infence:
                continue
            targets = [('link', m.group(1), m.end()) for m in MDLINK.finditer(line)]
            targets += [('tick', m.group(1).strip(), m.end()) for m in TICK.finditer(line) if is_pathlike(m.group(1).strip())]
            for kind, t, end in targets:
                # run 4: the VM-internal annotation exempts only the token it follows (within ANNOT_WINDOW chars),
                # not every path on the line
                annotated = bool(ANNOT.search(line[end:end + ANNOT_WINDOW]))
                if kind == 'link' and (t.startswith(('http://', 'https://', 'mailto:', 'doi:')) or t.startswith('#')
                                       or not re.search(r'[./]', t) or any(c in t for c in '()=[]')):
                    continue   # URLs, anchors, and SMILES fragments that look like [x](y)
                c = clean(t)
                if not c:
                    continue
                if c.startswith('/'):
                    st = 'annotated' if annotated else 'UNRESOLVED_ABSPATH'
                elif resolves(c, md.parent, root):
                    st = 'ok'
                elif annotated:
                    st = 'annotated'
                elif '/' not in c.rstrip('/') and c.rstrip('/') in names:
                    st = 'warn_basename_elsewhere'   # bare file name that exists elsewhere in the repo: findable, not blocking
                else:
                    st = 'UNRESOLVED'
                out.append((st, f'{rel}:{i}', kind, t))
    return out


if __name__ == '__main__':
    root = sys.argv[1]
    res = scan(root)
    bad = [r for r in res if r[0].startswith('UNRESOLVED')]
    rep = sys.argv[sys.argv.index('--report') + 1] if '--report' in sys.argv else None
    lines = ['status\tlocation\tkind\ttarget'] + ['\t'.join(r) for r in res]
    if rep:
        open(rep, 'w').write('\n'.join(lines) + '\n')
    for r in bad:
        print('\t'.join(r))
    from collections import Counter
    print(f'\nlinks checked: {len(res)}  ' + '  '.join(f'{k}={v}' for k, v in sorted(Counter(r[0] for r in res).items())))
    sys.exit(1 if bad else 0)
