# Pre-push checklist

A person works through this list before anything in this folder is pushed to the public repository.

Start with the automated scan. Passing it is required, but it is not enough on its own: the scan
looks for exact strings and cannot recognise a paraphrase, so the rest of the list needs human judgement.

```bash
python tools/scan_repo.py .
```

Terms used below:

- **VM-internal** or **`[not redistributed`**: a file that stayed on the machine the agents worked on
  during the hackathon and is not in this repository. Documents put one of these notes right after
  such a file name, so a reader knows not to look for it here.
- **Held-out validation set**: compounds a person set aside before any model was trained, so the
  models could later be tested on chemicals they had never seen. None of them may appear in this folder.
- **W-TOOL**, **W-MODEL** and similar names are the agents' working folders, which are not part of this
  repository.

## Blocking (do not push until every box is ticked)

- [ ] `tools/scan_repo.py` . exits 0.
- [ ] `tools/link_gate.py` . --report tools/link_gate_report.tsv exits 0. This means every markdown link,
      image and back-ticked file path either points to a file inside the repository or has a VM-internal /
      `[not redistributed` note right after it. scan_repo.py runs this check too; it is listed on its own
      so that a failure cannot be missed. The result of the last run is in tools/link_gate_report.txt.
- [ ] No file derived from CASMI competition data (a mass-spectrometry identification challenge), in any
      form, anywhere in the files or the git history.
- [ ] No compounds, labels or predictions from the held-out validation set.
- [ ] No private or paywalled literature: no PDFs, no extracted text, no copied tables or figures.
      Papers are cited by DOI and page only.
- [ ] No internal-only documents: the PI briefing, any log of expert answers, run notes, the spend
      ledger, agent transcripts.
- [ ] No credentials or API keys, including in the git history.
- [ ] No internal absolute paths, hostnames or usernames in any file, including inside notebooks,
      JSON and CSV files.
- [ ] Nothing that is not meant to be public, in any file, commit message, branch name, tag or
      release note. The public description is "Plata lab hackathon work on environmental fate and
      toxicity".
- [ ] A licence file is present, and the source licences allow every table in `data/` to be
      redistributed (CompTox, ChEMBL CC BY-SA 3.0, NMRexp CC BY 4.0).

## Correctness (check before anyone reads the numbers)

- [ ] `paper/whitepaper.pdf` is newer than `paper/whitepaper.md` and shows every figure.
      The published PDF is made by the author's build script `build_v8.py  [not redistributed; VM-internal]`
      (markdown converted with xhtml2pdf) from the paper source `whitepaper_v8.md  [not redistributed; VM-internal]`.
      `paper/build_whitepaper.py` is the earlier generator that put together the v5 text. It is included
      to show where the text came from, not as the way to build the paper, and it must not be re-run to
      regenerate the paper.
- [ ] The two passages marked DISPUTED are still marked (search `paper/whitepaper.md` for `DISPUTED`;
      expect 2). They are left unresolved on purpose: one is how far the EPI Suite "home-turf" caveat
      reaches, the other is whether melting point counts as a success for the spectrum-only model.
      Settling either needs a person to decide, not an edit.
- [ ] Every number quoted in `README.md` appears in a file under `data/` or `paper/`.
- [ ] Wherever an interval's coverage is printed, the empirical value (how often the interval actually
      contained the measured value on test compounds) is given, not only the nominal level it was built for.
- [ ] Leak-free numbers come before full-test-set numbers in the README, the paper and the dashboard.
      (Leak-free test compounds are those with no close structural analogue in the training data.)
- [ ] The hazard tasks with rare positives are scored with precision, recall or PR-AUC (the area under
      the precision-recall curve) compared with the base rate of positives, and never with accuracy as a
      measure of skill.

## Usability

- [ ] `dashboard/index.html` opens in a browser with the network switched off and shows a prediction.
- [ ] No video is in this repository. An earlier version of this item said the demo recording was "NOT
      in this repo by design". That was false. The recording had been copied into `dashboard/docs/`
      (file since removed; not redistributed) three minutes before this checklist was last edited, and
      its last eight seconds (00:59 to the end of 00:66.8) showed a full-screen internal status console
      with per-agent spend, internal absolute paths and team notes naming a user. It was removed on
      2026-11-01. The untrimmed original is kept outside the repository on the build machine, in the
      team results area, with a note on where it came from. It was not destroyed, so a trimmed version
      can still be cut from it.
      `tools/scan_repo.py` now FAILS on any video, and on any image that is not on its reviewed
      allowlist, so this box is checked by the machine rather than taken on trust. Before any recording
      is added back: trim it to the first 58 seconds, watch it once all the way through for window
      titles, file paths, usernames and any held-out compound, and only then add it to the allowlist.
- [ ] Someone outside the team can follow `README.md` -> "Reproduce a number" and get the same number.
- [ ] `dashboard/index.html` is the file the README points to. (The dashboard agent, W-TOOL, keeps the
      page one folder deeper in its own working tree; the build script moves it up a level, so check
      that it did.)

## Scan hits already reviewed (these do not block the push)

The scan flags the word "lockbox" in `paper/whitepaper.md` and `paper/build_whitepaper.py`. In both
places it is the method section explaining how the held-out validation compounds were removed from every
outside label table before training. No held-out compound, label or prediction is in the repository; the
word only names the procedure. Re-read those two lines, then tick this box.

- [ ] The only remaining scan hits are the two method-section mentions described above.
