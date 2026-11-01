# Paths this code assumes (VM layout), and how to change them
The dashboard page (`dashboard/index.html`) is self-contained and needs nothing.
The live backend reads frozen models and data from the swarm VM layout:
- models: `tool/models_registry.json` (W-MODEL/frozen_v5, W-SPECTRA/spectrum_only_v31, W-TOX/r3/model_frozen_v3), physics `W-PHYSICS/compute_physics.py  [not redistributed; VM-internal]`, AIMNet2 checkpoint `$AIMNET2_CKPT`  (paths here are VM-internal, not in this repo)
- definedness rules: `analysis/domain_rules.py` (`WSPACE_DIR` in `tool/wtool_postproc.py`)  (paths here are VM-internal, not in this repo)
- labels: `data/labels_v2.parquet  [not redistributed; VM-internal]` (VM-internal); EPI caches: `EPI_CACHES` in `tool/wtool_backend.py`  (paths here are VM-internal, not in this repo)
To run elsewhere, copy those folders and edit `WORK`, `SEED`, `EPI_CACHES`, `WSPACE_DIR` and the registry paths.

## Path placeholders (run 4)
VM absolute paths in the copied files were replaced by the literal `<TEAM_ROOT>`, and the swarm work-folder prefix by agents/work
(`W-TOOL/sync_repo_r4.py  [not redistributed; VM-internal]`, VM-internal). In the page they appear only in "Sources:" captions. Before running a script,
replace `<TEAM_ROOT>` with your data root. Acceptance run on 4 structures absent from labels_v2 and from CompTox:
`dashboard/acceptance/accept_report.md`.
