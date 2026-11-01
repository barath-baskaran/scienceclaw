# Demo script: recording the dashboard (about 2.5 minutes)

This script is for a person recording the dashboard on a laptop, and it is also what the automated
recorder `tool/record_demo.py` follows. Each click is listed with what should appear on screen. If
something different appears, stop and write it down: that is a bug.

Recording a live prediction needs the trained models and the local server, which are not in this
repository (see the main `README.md`). Names marked `[not redistributed; VM-internal]` stayed on the
machine the agents worked on. The section "Fallback without the server" at the end works with this
repository alone.

## Before you record
1. Copy `W-TOOL/` [not redistributed; VM-internal] (the dashboard agent's working folder) to the laptop. Python needs RDKit, LightGBM, pandas and torch (for physics), plus the model folders listed in `tool/models_registry.json`. The simplest option is to record on the VM itself, where everything is already in place.
2. Start the local tool: `bash start_dashboard.sh  [not redistributed; VM-internal]`. It listens on 127.0.0.1:8765, which only your own machine can reach.
3. Open `http://127.0.0.1:8765/` in a browser window of about 1280×900.
4. **Check:** a blue box reading "● Connected to the local tool." appears under the two big buttons.
   - If you see "▲ Viewing mode (opened as a file)", you opened the file rather than the server address.

## Scene 1: a structure nobody has measured (about 90 s)
1. Say: "This is a chemical that is in none of our training or test data."
2. Click into the SMILES box and paste `CCOC(=O)c1ccc(OC(F)(F)F)cc1` (ethyl 4-(trifluoromethoxy)benzoate). Its InChIKey (a standard structure identifier) `HSCMRGOOJDROHT-UHFFFAOYSA-N` is not in labels_v2, the table of measured values the models were trained and tested on.
3. Tick **"Also compute quantum-chemistry (AIMNet2) descriptors"**, then click **Estimate properties**. (AIMNet2 is a neural-network model that approximates quantum-chemical calculations; the tool uses it to compute physics descriptors for a new structure.)
4. **Expected:** a log box counts up while the CPU calculation runs: "physics: ETKDG+MMFF -> AIMNet2 relaxation … running — N s elapsed". (ETKDG+MMFF generates a first three-dimensional shape for the molecule; AIMNet2 then refines it.) It finishes in about 60–80 s on the VM.
   - Cut or speed up this wait when editing.
5. **Expected result, top:** the structure drawing; the formula C10H9F3O3 · 234.17 g/mol; "Quantum chemistry: physics computed at inference: computed (… s, converged)" with the line comparing the CPU result with the GPU result.
6. **Expected table "Environmental fate":** 12 rows. Each row shows:
   - an estimate with units, and a line in everyday units, e.g. "≈ 5.1 mg/L";
   - a likely range with a bar;
   - "NN% of n test chemicals / nominal 90%" (how often the range held on test chemicals, next to how often it was designed to hold);
   - a novelty tag: ● familiar, ▲ somewhat new or ✖ new to the model;
   - the EPI Suite value with the EPI Suite module that produced it.
   - pKa rows say "no EPI comparator (EPI Suite has no pKa module)".
7. Click the **Octanol–water partition** row. **Expected:**
   - "What drove this estimate": a bar showing the shares from structure / quantum chemistry / spectrum, and up to 5 named contributions such as "▲ raises by 0.31: Crippen logP".
   - "How good is this model on test chemicals": NN% of the naive error (the error of always guessing the training mean), then the same for chemicals as new to the model as this one.
   - "In everyday units".
8. Point at the **Consistency check** box: the Henry constant implied by the predicted vapour pressure and water solubility, compared with the one estimated directly.

## Scene 2: the tool refuses when a property does not exist (about 30 s)
1. Click the example button **"Quaternary ammonium salt"**. This also works offline, without the server.
2. **Expected:** the logKow, vapour pressure, Henry, boiling point, logKoa and kOH rows show **"⊘ Not physically defined for this compound"**, with no number and a "Why:" sentence (permanent cation, no neutral form or gas phase). Koc and BCF do show numbers, with "▲ Depends strongly on test conditions for a permanent ion".
3. Say: "A wide interval would claim that the quantity exists. Here it does not exist, so the tool says so."

## Scene 3: spectrum only, no structure (about 30 s)
1. Click **"I only have an MS/MS spectrum"**, then click the first example spectrum button.
2. **Expected:** the form fills in (ion mode, adduct, precursor m/z, collision energy, instrument, peaks) and a stick plot appears with ▲ marking the precursor ion. The results table uses "spectral match" for novelty. Below it, **How good is it?** shows the spectrum-only error next to the structure-based error.
3. Clear the "Ion mode" field and click **Estimate from spectrum**. **Expected:** a red box reading "Missing or inconsistent: ion mode…". The tool never guesses missing metadata.

## Scene 4: how good is it (about 20 s)
1. Click **"How good is it? (test results)"**.
2. **Expected:** a table per property comparing this tool (structure only), the tool with quantum chemistry added, and EPI Suite, each as error in % of the naive guess, overall and by novelty band (nn_sim, the similarity to the nearest training compound: <0.3 / 0.3–0.5 / 0.5–0.7 / ≥0.7), with "range held" given as empirical (nominal).

## Also record: the live swarm view
Show `(internal path removed)` (`watch -n 5 cat (internal path removed)`) and the board for about 15 s: agents, turns, spend, and the hypothesis market.

## Fallback without the server
Open `dashboard/index.html` directly. The examples, the spectrum examples and "How good is it?" all work.
Typing a new SMILES shows a red box explaining how to start the tool. Show that box too: it is the intended behaviour.
