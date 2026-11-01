# Demo script: recording the dashboard (about 2.5 minutes)

This is for a human recording on a laptop, and for the automated recording `tool/record_demo.py`.
Every click is listed together with what should appear on screen. If something different appears, stop and note it, because that is a bug.

## Before you record
1. Copy `W-TOOL/` [not redistributed; VM-internal] to the laptop. Python needs RDKit, LightGBM, pandas and torch (for physics), plus the swarm model folders listed in `tool/models_registry.json`. The simplest option is to record on the VM itself, where everything is already in place.
2. Start the local tool: `bash start_dashboard.sh  [not redistributed; VM-internal]`. It listens on 127.0.0.1:8765 and is not reachable from outside.
3. Open `http://127.0.0.1:8765/` in a browser window of about 1280×900.
4. **Check:** a blue box reading "● Connected to the local tool." appears under the two big buttons.
   - If you see "▲ Viewing mode (opened as a file)", you opened the file and not the server URL.

## Scene 1: a structure nobody has measured (about 90 s)
1. Say: "This is a chemical that is in none of our training or test data."
2. Click into the SMILES box and paste `CCOC(=O)c1ccc(OC(F)(F)F)cc1` (ethyl 4-(trifluoromethoxy)benzoate). Its InChIKey `HSCMRGOOJDROHT-UHFFFAOYSA-N` is not in labels_v2.
3. Tick **"Also compute quantum-chemistry (AIMNet2) descriptors"**, then click **Estimate properties**.
4. **Expected:** a log box counts up while the CPU relaxation runs: "physics: ETKDG+MMFF -> AIMNet2 relaxation … running — N s elapsed". It finishes in about 60–80 s on the VM.
   - Cut or speed up this wait in the edit.
5. **Expected result, top:** the structure drawing; the formula C10H9F3O3 · 234.17 g/mol; "Quantum chemistry: physics computed at inference: computed (… s, converged)" with the CPU/GPU parity line.
6. **Expected table "Environmental fate":** 12 rows. Each row shows:
   - an estimate with units, and an everyday-unit line, e.g. "≈ 5.1 mg/L";
   - a likely range with a bar;
   - "NN% of n test chemicals / nominal 90%";
   - a novelty tag: ● familiar, ▲ somewhat new or ✖ new to the model;
   - the EPI Suite value with its module.
   - pKa rows say "no EPI comparator (EPI Suite has no pKa module)".
7. Click the **Octanol–water partition** row. **Expected:**
   - "What drove this estimate": a bar showing the structure / quantum chemistry / spectrum shares, and up to 5 named contributions such as "▲ raises by 0.31: Crippen logP".
   - "How good is this model on test chemicals": NN% of the naive error, then the same for chemicals as new as this one.
   - "In everyday units".
8. Point at the **Consistency check** box: the Henry constant implied by the vapour pressure and water solubility, compared with the one estimated directly.

## Scene 2: the tool refuses when a property does not exist (about 30 s)
1. Click the example chip **"Quaternary ammonium salt"**. Offline, this works without the server too.
2. **Expected:** the logKow, vapour pressure, Henry, boiling point, logKoa and kOH rows show **"⊘ Not physically defined for this compound"**, with no number and a "Why:" sentence (permanent cation, no neutral form or gas phase). Koc and BCF do show numbers, with "▲ Depends strongly on test conditions for a permanent ion".
3. Say: "A wide interval would claim that the quantity exists. Here it does not exist, so the tool says so."

## Scene 3: spectrum only, no structure (about 30 s)
1. Click **"I only have an MS/MS spectrum"**, then click the first example spectrum chip.
2. **Expected:** the form fills in (ion mode, adduct, precursor m/z, collision energy, instrument, peaks) and a stick plot appears with ▲ marking the precursor. The results table uses "spectral match" for novelty. Below it, **How good is it?** shows the spectrum-only error next to the structure error.
3. Clear the "Ion mode" select and click **Estimate from spectrum**. **Expected:** a red box reading "Missing or inconsistent: ion mode…". The tool never guesses metadata.

## Scene 4: how good is it (about 20 s)
1. Click **"How good is it? (test results)"**.
2. **Expected:** a table per property: this tool (structure only), + quantum chemistry, and EPI Suite, each as error in % of the naive guess, overall and by novelty band (nn_sim <0.3 / 0.3–0.5 / 0.5–0.7 / ≥0.7), with "range held" given as empirical (nominal).

## Also record: the live swarm view
Show `(internal path removed)` (`watch -n 5 cat (internal path removed)`) and the board for about 15 s: agents, turns, spend, and the hypothesis market.

## Fallback without the server
Open `dashboard/index.html` directly. The examples, the spectrum examples and "How good is it?" all work.
Typing a new SMILES shows a red box explaining how to start the tool. Show that box too: it is the intended behaviour.
