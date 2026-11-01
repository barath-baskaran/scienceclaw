# Submission answers (DRAFT — a human approves every answer before anything is submitted)

*Plata lab hackathon work on environmental fate and toxicity. Built 2026-11-01 00:55.*

**Read this first.** The official submission form was not available to the agents on this machine, so
the twelve questions below are the standard ones we expect and the answers are drafted against them.
**Re-map every answer to the real form before use.** Where a question asks about a sponsor technology we
did not use, the honest answer is a blank, not a stretched paragraph — those are marked
"NOT USED — leave blank".

---

**1. What problem does your project solve?**

Chemists designing new molecules, and analysts identifying unknown ones, both need environmental fate
and hazard estimates for compounds that may never have been made. Existing tools were fitted to the
chemistry that already exists and do not tell a user when they are extrapolating. We built a predictor
that works from a structure, a structure plus a measured MS/MS spectrum, or a spectrum alone, and that
reports how far outside its experience each request is.

**2. What did you build?**

An offline, single-file dashboard and the models behind it: 12 physicochemical fate endpoints and
5 hazard endpoints. Each prediction returns a value, a split-conformal interval with its measured
empirical coverage, a domain flag, the EPI Suite comparator where one exists, and the features that
drove the prediction. Three input modes are offered, including spectrum-only. In structure + MS/MS mode the spectrum changes the hazard and spectral-model panels but cannot change a fate number, because the shipped fate model (structure + AIMNet2 physics) contains no spectral features.

**3. How do you know it works?**

We score error as RMSE as a percentage of a naive guess that always predicts the training mean, so
100% means no skill. The headline is measured only on **leak-free** test compounds — no training
analogue at Tanimoto ≥ 0.40 on Morgan r2/2048 fingerprints — and the flattered full-test number is reported afterwards, labelled. Under other fingerprints some of those compounds do have close analogues, so the stricter claim is the novel-scaffold one.
On leak-free compounds the shipped model reaches 45%–53%
of naive on the five largest endpoints. A second, harder protocol (graph-partitioned cross-validation,
every compound tested with no neighbour in its training folds) reproduces the result.

**4. How does it compare with the standard tool (EPI Suite)?**

On identical leak-free rows, with a paired cluster bootstrap. Nine comparisons could be made: three
fate endpoints have no EPI module or too few leak-free rows (both pKa endpoints, and logKOA at n=3),
so they are not comparisons at all rather than unresolved ones. Of the nine, our model is better
unadjusted on 6, EPI Suite is better on 1 (koh_gas) and we
do not know why, and 2 are unresolved (Henry, BCF). After a Bonferroni correction over the nine, four
wins stand — melting point, water solubility, boiling point and vapour pressure — and those are the
only ones we claim; logKow and Koc are marginal and we do not claim them. Only melting point and water
solubility survive every control we ran — the EPI range-clip and symmetric tail-trimming controls, median absolute error, the strictly-novel-scaffold cut, and the restriction to PhysProp-sourced labels (`data/attack_strict_novel.csv`, `CRITIC/attack_trim_symmetric.csv  [not redistributed; VM-internal]`, `data/label_source_attack.csv`). On PhysProp labels
intersected with the leak-free cut, boiling point and vapour pressure tie and for logKow the comparison leans towards EPI Suite but is
not resolved (44.2% vs 34.4% of naive, n=237, CI [-1.5, +20.5], which contains zero). [DISPUTED, deliberately left open: how far the EPI 'home-turf' caveat extends. On PhysProp rows intersected with leak-free, melting point and water solubility keep a margin over EPI Suite and boiling point, vapour pressure, logKow, Henry and BCF are not resolved (`data/label_source_attack.csv`); on ALL PhysProp test rows vapour pressure also keeps one (`data/dg2_fairness_dedup.csv`). The two cells disagree; a human should pick. See whitepaper Section 4.1.] The model behind this table is structure + AIMNet2 physics and
contains no spectral features. EPI Suite's training data overlap our label source, so its numbers are
optimistic and ours are leak-free — that asymmetry favours EPI, and clipping EPI's estimates to the
training-label range removes most of our logKow, vapour-pressure and boiling-point advantage.

**5. What is novel?**

Three things. (a) The evaluation: leak-free first, plus a graph-partitioned split that makes
"never seen anything like this" the default test rather than a sensitivity analysis. (b) Spectrum-only
prediction treated as a first-class mode across many endpoints rather than one endpoint at a time, with
the controls that show fragments carry information beyond the precursor mass. (c) A three-way
distinction in the domain flag between "in domain", "far from training", and "physically undefined for
this species" — a gas-phase property does not exist for a permanently charged species, and calling that
a data gap would misdirect a measurement budget.

**6. What does the uncertainty mean?**

Intervals are split-conformal at a nominal 90%. We never print the nominal level without the empirical
coverage measured on held-out data beside it. Coverage holds reasonably per familiarity bin; it is
weaker per compound class, so we ship a normalised-Mondrian variant that removed every significantly
under-covered class cell in our audit, at the cost of wider intervals on small endpoints. Intervals from the separate
spectrum-only model (W-SPECTRA `spectrum_only_v31`, one spectrum per compound) under-cover on
leak-free compounds (0.81–0.96 against a nominal 0.90; 0.854–0.967 on the full test) and are labelled
as approximate in the interface.

**7. What did not work?**

Several things, all measured cleanly and all in the main text. Physics descriptors from AIMNet2
relaxations give a small gain whose significant-endpoint set changed with every defensible scoring
choice. Rebuilding the spectral representation did not beat the previous one. The model predicts a
parent-to-product transformation change no better than a change between two arbitrary similar
compounds. A spectral-similarity domain flag does not predict spectrum-only error. A spectrum alone
carries essentially no skill for acute lethality. And our own pre-registered bet that training on
measured labels would transfer better than training on another model's labels was falsified for the
androgen receptor and is not established for ER-alpha. The pair we first published compared a
continuous-potency regressor against a binary-label classifier on a binary benchmark, which
handicaps the measured arm; on the matched arm (a classifier trained on the measured ChEMBL call)
the paired 95% intervals on the PR-AUC difference are AR [-0.193, -0.084], excluding zero, and
ER-alpha [-0.117, +0.009], which crosses it.

**8. What data did you use?**

Experimental labels from the US EPA CompTox Chemicals Dashboard; measured receptor potencies from
ChEMBL (CC BY-SA 3.0); mass spectra from the CompTox AMOS collection; experimental 1H NMR spectra from
NMRexp (CC BY 4.0, doi:10.5281/zenodo.17296666). Identity is by standardised InChIKey with
stereochemistry retained, never by name or CAS. Splits are by chemical-space cluster; a further
validation set is held out by a human and was never visible to the models.

**9. How is hazard handled responsibly?**

Hazard endpoints are evaluative only: we predict properties of supplied structures and do not rank,
generate or optimise structures toward hazard. Receptor-activity labels are rare positives, so they are
never scored with accuracy; we report precision, recall and PR-AUC against each familiarity bin's own
base rate, with a control that knows only the similarity bin. That control already reaches a large share
of the pooled ranking performance, which is why the pooled number must not be quoted alone.

**10. Who is it for, and how would they use it?**

A bench chemist choosing between candidate structures, and an analytical chemist with an unidentified
peak. Both open one offline HTML file. The interface is colour-blind accessible, works at phone width,
and was cold-reviewed for usability by someone who had not built it.

**11. What would you do next?**

Recalibrate the spectrum-only intervals, which are the weakest part of the product. Replace the
single-conformer physics descriptors with the conformer-ensemble version — for flexible molecules the
single conformer is close to a random draw. Fund measurements by compound class rather than by count:
a leave-class-out experiment with a size-matched control names the classes where the penalty is largest,
and a learning curve shows that untargeted extra data helps familiar chemistry most.

**12. Sponsor technology used.**

GPU-accelerated AIMNet2 relaxations (with Ewald electrostatics and D3(BJ) dispersion) produced the
physics descriptor table and the relaxed structures, and the same path runs at inference for a new
structure. We report its measured contribution honestly: small, and not reliably attributable to any one
endpoint. Anything else on the sponsor list that we did not use: **NOT USED — leave blank.**
