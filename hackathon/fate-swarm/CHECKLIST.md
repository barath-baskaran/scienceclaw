# Pre-push checklist (a human runs this)

Run the automated scan first; it is necessary but not sufficient.

```bash
python tools/scan_repo.py .
```

The scan cannot detect paraphrase, so the remaining items are human judgement.

## Blocking

- [ ] `tools/scan_repo.py` . exits 0.
- [ ] `tools/link_gate.py` . --report tools/link_gate_report.tsv exits 0 (every markdown link, image and back-ticked
      path resolves inside the repo, or carries a VM-internal / `[not redistributed` note right after it). scan_repo.py
      also runs this gate; it is listed separately so a failure is impossible to miss. Last run: see tools/link_gate_report.txt.
- [ ] No file derived from CASMI competition data, in any form, anywhere in the tree or the git history.
- [ ] No held-out validation-set compounds, labels or predictions.
- [ ] No private or paywalled literature: no PDFs, no extracted text, no copied tables or figures.
      Literature is cited by DOI and page only.
- [ ] No internal-only documents: the PI briefing, any expert-answer log, run notes, the spend ledger,
      agent transcripts.
- [ ] No credentials or API keys, including in the git history.
- [ ] No internal absolute paths, hostnames or usernames in any file, including inside notebooks,
      JSON and CSV.
- [ ] Nothing that is not meant to be public, in any file, commit message, branch name, tag or
      release note. The public description is "Plata lab hackathon work on environmental fate and
      toxicity".
- [ ] A licence file is present, and redistribution of every table in `data/` is permitted under the
      source licences (CompTox, ChEMBL CC BY-SA 3.0, NMRexp CC BY 4.0).

## Correctness, before anyone reads the numbers

- [ ] `paper/whitepaper.pdf` is newer than `paper/whitepaper.md` and renders every figure. The shipped
      PDF is produced by the author's build script `build_v8.py  [not redistributed; VM-internal]`  [not redistributed; VM-internal] (markdown + xhtml2pdf) from the paper source `whitepaper_v8.md  [not redistributed; VM-internal]`  [not redistributed; VM-internal];
      `paper/build_whitepaper.py` is the earlier generator that assembled the v5 body and is shipped for
      provenance, not as the build entry point. It must not be re-run to regenerate the paper.
- [ ] The two DISPUTED passages (grep `DISPUTED` in `paper/whitepaper.md`, expect 2) are still marked.
      They are deliberately unresolved: the extent of the EPI home-turf caveat, and whether melting
      point counts as a spectrum-only success. Settling either needs a human, not an edit.
- [ ] Every number quoted in `README.md` appears in a file under `data/` or `paper/`.
- [ ] Every interval coverage printed anywhere carries its empirical value, not only the nominal level.
- [ ] Leak-free numbers appear before full-test numbers in the README, the paper and the dashboard.
- [ ] The rare-positive hazard tasks report precision, recall or PR-AUC against the base rate - never
      accuracy as a measure of skill.

## Usability

- [ ] `dashboard/index.html` opens in a browser with the network disabled and renders a prediction.
- [ ] No video is in this repo. This used to say the demo recording was "NOT in this repo by design";
      that was false. The recording had in fact been copied into `dashboard/docs/` (file since removed; not redistributed)
      three minutes before this checklist was last edited, and its last eight seconds (00:59 to the end
      of 00:66.8) were a full-screen internal status console: per-agent spend, internal absolute paths
      and team notes naming a user. It was removed on 2026-11-01. The untrimmed original is kept
      outside the repo on the build machine, under the team results area, with a provenance note; it
      was not destroyed, so a trimmed version can still be cut from it.
      `tools/scan_repo.py` now FAILS on any video, and on any image not on its reviewed allowlist, so
      this box is machine-checked rather than taken on trust. Before any recording is added back: trim
      it to the first 58 seconds, watch it once in full for window titles, file paths, usernames and any
      held-out compound, and then add it to the allowlist deliberately.
- [ ] Someone outside the team can follow `README.md` -> "Reproduce a number" and get the same number.
- [ ] `dashboard/index.html` is the file the README points at (W-TOOL ships it one level deeper in its
      own tree; the build script flattens it, so check it did).

## Known non-blocking scan hits, already reviewed

The scan reports the word "lockbox" in `paper/whitepaper.md` and `paper/build_whitepaper.py`. Those are
the method section describing how held-out validation compounds were removed from any external label
table before training. No held-out compound, label or prediction is in the repository; the word
describes the mechanism. Re-read those two lines and then tick this box.

- [ ] The remaining scan hits are only the two method-section mentions described above.
