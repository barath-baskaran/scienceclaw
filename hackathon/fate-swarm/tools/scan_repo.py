"""Pre-push safety scan for the public repo draft. Prints every hit; exit code 1 if any BLOCKING hit.
Usage: python scan_repo.py <repo_dir>
Checks (blocking unless noted):
  - CASMI-derived content (any file path or text mentioning casmi)
  - absolute paths / usernames / hostnames (/srv/, /home/, /Users/, /opt/, known VM usernames)
  - key-like strings (sk-..., api_key=..., x-api-key values, AWS/GitHub token shapes, BEGIN PRIVATE KEY)
  - internal-only material: exec summary, expert-answer logs, board notes, transcripts, ledger
  - lockbox / hidden-set files
  - private literature: PDFs, and long verbatim-looking passages are NOT detectable here -> human check
  - every markdown link/image and back-ticked path resolves inside the repo or is annotated VM-internal (tools/link_gate.py)
  - files > 50 MB (GitHub hard limit 100 MB; warn at 50 MB) [warning]
  - any video file at all, and any image file not in the reviewed MEDIA_OK allowlist. Text checks
    cannot see into pixels, so media is blocked until a human has looked at it (see MEDIA_OK).
"""
import os, re, sys, pathlib
root = pathlib.Path(sys.argv[1]).resolve()
TEXT_EXT = {".py", ".md", ".txt", ".json", ".csv", ".html", ".js", ".css", ".yaml", ".yml", ".toml", ".cfg", ".sh", ".tsv", ".R", ".ipynb"}
PAT = [
    ("casmi", re.compile(r"casmi", re.I), True),
    ("abs_path", re.compile(r"(/srv/|/home/|/Users/|/opt/|/var/lib/|/root/)"), True),
    # account names to block are supplied at run time (comma-separated, base64-encoded) in the
    # SCAN_REPO_USERNAMES_B64 environment variable, so this public file does not carry them
    ("username", re.compile(r"(/home/[A-Za-z0-9._-]+|\buser\d+\b" + "".join(r"|\b" + re.escape(n) + r"\d*\b" for n in __import__("base64").b64decode(os.environ.get("SCAN_REPO_USERNAMES_B64", "")).decode().split(",") if n) + ")", re.I), True),
    ("key_sk", re.compile(r"\bsk-[A-Za-z0-9_\-]{16,}"), True),
    ("key_assign", re.compile(r"(api[_-]?key|secret|password|token)\s*[:=]\s*['\"][A-Za-z0-9_\-]{12,}['\"]", re.I), True),
    ("key_github", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}"), True),
    ("key_aws", re.compile(r"\bAKIA[0-9A-Z]{16}\b"), True),
    ("private_key", re.compile(r"BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY"), True),
    ("internal", re.compile(r"(exec_summary_internal|INTERNAL ONLY|answers\.jsonl|transcript_|ledger_run|notes_run|key_pool|env_keys)", re.I), True),
    ("lockbox", re.compile(r"(lockbox|hidden[_ ]set|rows_out_lockbox)", re.I), False),
    ("swarm_word_path", re.compile(r"swarm/(work|board|live)"), True),
]
# run 5: the gates own reports are deliberately NOT exempt. A gate that cannot read its own output
# is not a gate - tools/scan_repo_report_r4.txt sat in this repo quoting 32 internal absolute paths
# and was never once opened. If a report quotes something blocking, the report must not ship either:
# delete it, or write it outside the published tree.
BAD_NAMES = re.compile(r"(casmi|internal|lockbox|hidden|answers|transcript|ledger|\.pdf$|\.env|key_pool)", re.I)
VIDEO_EXT = {".mp4", ".mov", ".webm", ".avi", ".mkv", ".m4v", ".wmv", ".flv", ".gif"}
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".svg", ".webp", ".bmp", ".tif", ".tiff", ".ico"}
# Media allowlist. THIS SCANNER READS TEXT ONLY - it cannot see what is rendered into pixels, and
# everything it missed on 2026-11-01 was media: an internal status console (per-agent spend, paths,
# team notes) in the last 8 s of dashboard/docs/demo_v3.mp4, an internal absolute path baked into
# all 9 dashboard screenshots, and a per-agent USD ledger plotted in paper/figures/figS4_swarm_spend.png.
# Text-clean therefore never meant clean. So media BLOCKS by default and a human has to put each
# file here after actually looking at it. One entry per repo-relative path:
#     "paper/figures/fig1_headline.png": "AB 2026-11-01 opened at full size; axes+legend only",
# Rules: look at the whole image, not a thumbnail - a path in a footer is small but legible.
#        Never allowlist a video. A recording cannot be reviewed once and trusted; if one must ship,
#        trim it, watch all of it, and add it here as the deliberate exception that it is.
#        figS4_swarm_spend.png must NOT be allowlisted: it is a per-agent spend chart.
MEDIA_OK = {
}
ALLOWED_PDF = {"whitepaper.pdf", "review_summary.pdf"}
# Files that legitimately contain the forbidden words because they are *about* them:
# this scanner, and the human checklist that tells the reviewer what to look for.
SELF_SKIP = {'scan_repo.py', 'CHECKLIST.md'}
hits, block = [], False
for p in sorted(root.rglob("*")):
    if p.is_dir(): continue
    rel = p.relative_to(root)
    if ".git" in rel.parts: continue
    if p.name in SELF_SKIP: continue
    sz = p.stat().st_size
    if sz > 50e6: hits.append(("WARN size>50MB", str(rel), f"{sz/1e6:.0f} MB"))
    if BAD_NAMES.search(str(rel)) and p.name not in ALLOWED_PDF:
        hits.append(("BLOCK filename", str(rel), "")); block = True
    if p.suffix.lower() in VIDEO_EXT:
        hits.append(("BLOCK video", str(rel), "no video ships from this repo; see MEDIA_OK")); block = True
    elif p.suffix.lower() in IMAGE_EXT and str(rel) not in MEDIA_OK:
        hits.append(("BLOCK image_unreviewed", str(rel), "not in MEDIA_OK: a human must look at it first")); block = True
    if p.suffix in TEXT_EXT and sz < 30e6:
        try: txt = p.read_text(errors="ignore")
        except Exception: continue
        for name, rx, is_block in PAT:
            for m in list(rx.finditer(txt))[:3]:
                line = txt.count("\n", 0, m.start()) + 1
                ctx = txt[max(0, m.start() - 40): m.end() + 40].replace("\n", " ")
                hits.append(("BLOCK " + name if is_block else "CHECK " + name, f"{rel}:{line}", ctx)); block |= is_block
# Link-resolution gate (W-TOOL, run 4): every md link/image and back-ticked path must resolve inside the repo
# or carry a VM-internal annotation on the same line. Details and rules: tools/link_gate.py.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import link_gate
for st, loc, kind, tgt in link_gate.scan(root):
    if st.startswith('UNRESOLVED'):
        hits.append(("BLOCK link_unresolved", loc, f"{kind}: {tgt}")); block = True
    elif st.startswith('warn'):
        hits.append(("WARN link_basename_only", loc, f"{kind}: {tgt}"))
tot = sum(p.stat().st_size for p in root.rglob("*") if p.is_file() and ".git" not in p.parts)
for h in hits: print(" | ".join(h))
print(f"\nfiles: {sum(1 for p in root.rglob('*') if p.is_file())}, total size {tot/1e6:.1f} MB, hits {len(hits)}, blocking: {block}")
sys.exit(1 if block else 0)
