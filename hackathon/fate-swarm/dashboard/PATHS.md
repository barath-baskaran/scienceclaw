# File locations the dashboard code expects, and how to change them

The dashboard page (`dashboard/index.html`) is self-contained and needs nothing else.

The live backend (the local server that makes new predictions) reads the frozen models and data from
the folder layout of the machine the agents worked on (the "VM"). Those folders are not in this
repository:

- models: listed in `tool/models_registry.json` (W-MODEL/frozen_v5, W-SPECTRA/spectrum_only_v31, W-TOX/r3/model_frozen_v3); physics `W-PHYSICS/compute_physics.py  [not redistributed; VM-internal]`; AIMNet2 checkpoint `$AIMNET2_CKPT`  (paths here are VM-internal, not in this repo)
- rules for whether a property is physically defined: `analysis/domain_rules.py` (`WSPACE_DIR` in `tool/wtool_postproc.py`)  (paths here are VM-internal, not in this repo)
- labels (measured values): `data/labels_v2.parquet  [not redistributed; VM-internal]` (VM-internal); EPI Suite caches: `EPI_CACHES` in `tool/wtool_backend.py`  (paths here are VM-internal, not in this repo)

To run elsewhere, copy those folders and edit `WORK`, `SEED`, `EPI_CACHES`, `WSPACE_DIR` and the paths in the registry.

## Path placeholders (run 4)

In the copied files, absolute paths on the VM were replaced by the literal text `<TEAM_ROOT>`, and the prefix of the
agents' working folders by agents/work (`W-TOOL/sync_repo_r4.py  [not redistributed; VM-internal]`, VM-internal). In the page they appear only in
"Sources:" captions. Before running a script, replace `<TEAM_ROOT>` with your own data folder.

The acceptance run, on 4 structures absent from labels_v2 and from CompTox, is in
`dashboard/acceptance/accept_report.md`.
