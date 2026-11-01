The question this work was built to answer was not "can a model predict logKow". It was whether
**physics and measured spectra buy anything on chemistry far from the training data**, where a
structure-only QSAR is on the weakest ground and where a designer most needs an answer. The results
section gives three answers, and only one of them is the one we wanted.

**The evaluation, not the model, is what moves the number.** The same model scored on the full test
split and on compounds with no training analogue differs by tens of points of naive error, and almost
all of that gap is harder chemistry rather than memorised neighbours: removing every near neighbour
from the training set costs only a little more than removing the same number of compounds at random
(Section 4.1). A graph-partitioned protocol, in which every labelled compound is predicted by folds
containing no neighbour of it, reproduces the leak-free picture at much larger n. We therefore think
the leak-free and graph-partitioned numbers are the only ones worth quoting for a tool whose purpose
is novelty, and that the convention of reporting random-split performance for fate models is, for this
use case, close to meaningless. That is a claim about evaluation practice, and it is the one we would
defend hardest.

**Physics helped, slightly, and not where we predicted.** We funded the physics work on the hypothesis
that quantum-chemical descriptors would help *disproportionately* far from the training data, because
they encode something transferable that a fingerprint does not. They do not. Across every protocol we
tried — the official leak-free subset, a graph-partitioned cross-validation with a permutation control
that holds capacity fixed, and a capacity control on the descriptor block — the gain is small, between
one and a few points of naive error, and it lowers the whole error-versus-familiarity curve rather
than flattening it (Sections 4.2). Worse for the hypothesis, the set of endpoints on which the gain is
statistically distinguishable from zero changed with every defensible scoring choice, including one as
innocuous as whether repeated InChIKeys are collapsed before scoring. We report the instability instead
of picking the version that reads best, and we draw the modest conclusion: single-conformer AIMNet2
descriptors are a small, real, poorly-localised improvement, and the honest next step is the
conformer-ensemble version, because for flexible molecules the single relaxed geometry we used is close
to a random draw from the conformer distribution.

**A measured spectrum is a substitute for a structure, not a supplement to it.** This is the result we
did not expect to be so clean. Given a structure, adding its MS/MS spectrum changes nothing measurable.
Given no structure at all, a single spectrum recovers a substantial fraction of the skill — and it does
so using the fragments, not merely the precursor mass, which we show against both a mass-only and a
regularised mass-plus-adduct control. The same shape appears in an entirely independent modality: an
experimental 1H NMR peak list alone carries real skill, beats a size-only control by a wide margin, and
adds nothing on top of a known structure. Two different spectroscopies, the same conclusion. For the
analytical chemist staring at an unidentified peak, that is the useful finding: the spectrum is not
waiting on structure elucidation to become informative. For the designer who already has a structure,
the spectrum is not worth acquiring.

**But the mode's limits are sharp, and we had to measure them to find them.** Spectrum-only skill is
endpoint-specific, not mode-wide. For acute lethality a full spectrum is barely better than predicting
the training mean, while the structure is substantially better on the very same compounds — the opposite
of the fate endpoints. And the obvious safeguard does not work: similarity to the nearest training
spectrum does not predict spectrum-only error, so we cannot warn the user with it, and we say so in the
interface rather than shipping a reassuring number that means nothing. The spectrum-only intervals also
under-cover on novel chemistry (empirical 0.81-0.96 against a nominal 0.90; Section 4.3). A product that offered spectrum-only prediction as a uniform capability
would be wrong about half the time it mattered; the version we ship gates it per endpoint.

**Two results reframe where measurement money should go.** The first is the distinction between a cell
of the compound-class × endpoint table being empty because nobody measured it and being empty because
the quantity does not exist for that species: a vapour pressure or a Henry's law constant is defined
through a gas phase that a permanently charged species cannot enter. Deriving that rule from the
endpoint definitions and applying it to every cell moved a large share of apparent "data gaps" into a
category where no experiment is possible, and left a much shorter list that is genuinely worth funding
(Section 4.5). The second is that extra data of the kind we already have helps familiar chemistry most;
the leave-class-out experiment, with a size-matched control, names the specific classes where being
unseen is expensive. Together they argue for targeted measurement by class rather than for more of the
same.

**The one we got wrong, and why we report it.** We expected that hazard models trained on measured
receptor potencies would transfer better than models trained on another model's consensus labels. On an
external benchmark that neither had seen, they transferred worse, on both receptors, with intervals
excluding zero against us (Section 4.6). The explanation we believe — that the measured corpus is
drug-like congeneric chemistry while the benchmark is environmental, so label-space *coverage* beat
label *fidelity* — is a hypothesis, not a result, and it carries a caveat we state in the same breath:
the model-derived labels descend from models trained on related literature data, so that arm may retain
an inherited advantage even after compound and cluster exclusion. We report it because a pre-registered
bet that fails is more informative than one that succeeds, and because the practical implication for
anyone assembling a hazard training set is the opposite of the intuition.

**How much of this should be attributed to the way the work was organised?** We cannot run the
counterfactual, so we claim nothing about the agent swarm being faster or better than a team of people.
What we can report is which specific errors the structure caught: a results section built on model-derived
labels that a reviewing agent insisted be rebuilt on measured ones; a headline figure whose panels no
longer matched the text it illustrated, caught by the rule that a figure must be drawn from the same
result file as the sentence beside it; a statistic about memorised neighbours that was withdrawn by its
own author after an audit showed it confounded; an abstract that reported "zero endpoints" because of a
dictionary-key mismatch rather than because of a result; and a proposal rejected on the proposing agent's
own feasibility data and replaced with a version whose test could actually fail. Each of those was found
by an agent whose job was to disbelieve, not by the agent that produced the number. That is a weak claim
compared with "the swarm did better science", and it is the one the evidence supports.

**What this is not.** It is not a validated regulatory tool; the intervals are honest about their
coverage but they are not accepted by anyone. It is not a demonstration that quantum chemistry is
unnecessary — only that these descriptors, from one conformer, bought little. And it is not a general
spectrum-to-property model: every spectral result here is conditioned on a library-quality spectrum of a
compound that someone has already measured a property for, which is exactly the regime a real unknown is
not in. Closing that last gap, honestly, is the work we would do next.
