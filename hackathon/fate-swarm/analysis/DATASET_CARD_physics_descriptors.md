# physics_inventory_v1: AIMNet2 relaxed-geometry descriptors over the EPA DSSTox inventory

Owners: OPS-1 / OPS-2 (GPU relaxations), W-PHYSICS (descriptor definitions, table build, this card).
Status: built from whatever shards complete during run 3. The coverage actually reached is in
`physics_inventory_v1_coverage.json  [not redistributed; VM-internal]`, which `build_inventory_descriptors.py  [not redistributed; VM-internal]` + `inventory_coverage.py  [not redistributed; VM-internal]` generate from the table
itself. Every count quoted below comes from those files or from the OPS prep-stats files named here; none were typed by hand.

## What it is
For each structure: one 3D conformer, relaxed with a machine-learned interatomic potential that reproduces
ωB97M-D3/def2-TZVPP DFT (AIMNet2). Descriptors are then computed from the relaxed geometry and the AIMNet2 atomic partial charges.
The descriptor code is **identical** to the training table `physics_descriptors_v1`: the same Python function,
`compute_physics.descriptors_from_geometry`. A model trained on physics_v1 can therefore consume these rows without translation.

## Structure source and selection (OPS-1 `inv3_prep.py  [not redistributed; VM-internal]`; stats in gpu/inventory_v3_all/prep_stats.json)
- Source: the public EPA DSSTox identifiers file, 2021r1. sha256 f4d6aeb4f57bc45a76508d80c67628d05dbbe7ed18a53e0b4d5770c22684096a. 906,511 substances.
- Standardised to parent structures with RDKit 2026.09.1. Identity is the RDKit InChIKey of the parent, and every DTXSID that
  maps to it is kept (map.csv.gz).
- Removed, each counted in prep_stats.json: no InChI, parse failure, radicals, isotopically labelled, no carbon,
  unsupported element (AIMNet2 covers H B C N O F Si P S Cl As Se Br I), too large, fewer than 2 heavy atoms.
  Duplicates sharing an InChIKey are merged. Result: 782,693 structures in 783 shards of 1,000, ordered by InChIKey.
  Shards are therefore an unbiased-by-design (alphabetical-hash) subsample of the inventory: partial coverage is a random
  subset, not one chosen by chemistry.
- 14,396 structures carry a net formal charge (permanent ions, e.g. quaternary ammonium). They are relaxed with that total
  charge; see "Charged structures" below.

## Computational protocol (identical to physics_v1)
RDKit `AddHs` → ETKDGv3, randomSeed 0xF00D (61453), one conformer. If embedding fails: ETKDGv3 with random coordinates,
flagged in `embed`. Then MMFF94 optimisation (flagged if parameters are missing) → AIMNet2 `aimnet2_wb97m_d3_0` + Ewald
long-range electrostatics (accuracy 1e-6) + DFT-D3(BJ) (s6 1.0, s8 0.3908, a1 0.566, a2 3.128) in a 30 Å periodic cubic box →
NVIDIA ALCHEMI FIRE2 (dt 0.01). A molecule is converged when its max per-atom force is < 0.01 eV/Å; at most 3000 steps.

## Columns
| column | definition | units |
|---|---|---|
| inchikey, skeleton | standardised InChIKey; first block (14 chars) | – |
| smiles | RDKit canonical SMILES of the relaxed structure's input (atom order basis) | – |
| charge | net formal charge passed to AIMNet2 | e |
| n_atoms | atoms including H | count |
| embed | `etkdg` or `random_coords` (+`+no_mmff`, `+mmff_missing_params`) | – |
| converged, fmax_eV_A | per-molecule convergence and final max force | –, eV/Å |
| physics_ok | converged AND fmax ≤ 0.01 AND no topology issue. **All descriptors are NaN when False** | bool |
| qc_issue | `bond_broken` (bonded pair > 1.35× sum of covalent radii), `new_close_contact` (non-bonded < 0.85×), `sasa_failed`, `not_converged`, `no_geometry`, `descriptor_error:*` | – |
| charged | charge ≠ 0 | bool |
| energy_eV | total AIMNet2+Ewald+D3 energy. Composition-dominated: do not use as a feature | eV |
| energy_per_atom_eV | energy / n_atoms (a composition proxy) | eV/atom |
| e_resid_eV, e_resid_per_atom_eV | energy − Σ n_e μ_e with the FROZEN physics_v1 element references (e_resid_reference_v1.json): an atomisation-like stability residual | eV, eV/atom |
| e_resid_robust_z | (e_resid_per_atom − median)/(1.4826·MAD), reference statistics from physics_v1 | – |
| q_total_e | Σ AIMNet2 charges (QC; ≈ charge) | e |
| dipole_D, dipole_per_heavy_D | point-charge dipole from AIMNet2 charges (no atomic polarisation) | Debye |
| q_max_e, q_min_e, q_std_e, q_abs_sum_per_atom_e | statistics of AIMNet2 atomic charges | e |
| q_O_min_e, q_N_min_e, q_S_min_e, q_halo_min_e | most negative charge on O / N / S / halogen. **NaN = element absent** (meaningful, not missing) | e |
| q_hetero_min_e, q_hetero_max_e, q_hetero_spread_e | min/max/(max−min) charge on non-C, non-H atoms | e |
| q_C_max_e, q_H_max_e, q_Hpolar_max_e | most positive C; H; H bonded to N/O/S (NaN if none) | e |
| rg_A | mass-weighted radius of gyration | Å |
| asphericity_A2, kappa2 | gyration-tensor asphericity; relative shape anisotropy (0 sphere, 1 rod) | Å², – |
| max_extent_A | largest interatomic distance | Å |
| sasa_A2, sasa_polar_A2, sasa_polar_frac | Lee–Richards SASA (FreeSASA, probe 1.4 Å); polar part (N, O, H on N/O/S); fraction | Å², Å², – |
| cpsa_pos_A2e, cpsa_neg_A2e, cpsa_abs_frac | Σ q_i·SASA_i over q>0 / q<0; Σ|q_i|·SASA_i / SASA | e·Å², e·Å², e |

## Charged structures
Under periodic Ewald, a net charge implies a uniform neutralising background. The total energy then depends on the box
and is not comparable with neutral molecules, and the dipole of an ion depends on the origin. For `charged` rows,
energy_eV, energy_per_atom_eV, e_resid_*, dipole_D and dipole_per_heavy_D are therefore **NaN by design**. Geometry, SASA and charge
descriptors are kept. Properties defined for the neutral species or the gas phase (logKow, VP, Henry, KOA) are
physically undefined for permanent ions. That is a property of the chemistry, not a gap in this dataset.

## Which columns to trust for flexible molecules (W-PHYSICS P-001 pre-test, pretest_flex_shard0.json)
One conformer per molecule. Compared with a 1–20-conformer AIMNet2 ensemble from the same calculator (917 molecules):
- rigid (0–1 rotatable bonds): all descriptors are identical to the ensemble's lowest conformer;
- flexible (≥5 rotatable bonds): **dipole, kappa2, asphericity, rg and max_extent are effectively one random draw** from the
  conformer ensemble (median deviation from the Boltzmann average 0.13–0.59 population SD). SASA, polar SASA, surface-charge
  and atomic-charge descriptors are stable (≤0.03 SD). The seed conformer lies more than 0.1 eV above the best conformer
  found for 50–73 % of flexible molecules, so energy-derived columns carry conformational noise of about 0.1 eV.

## Reproducibility
- CPU path: `compute_physics.compute_physics(smiles, force_cpu=True)` with `AIMNET2_CKPT` set. Same protocol.
- CPU vs GPU parity (parity_cpu_gpu_v1.json, 40 molecules): 40/40 converged; |ΔE| median 2 meV, max 43 meV; charges max
  |Δ| 0.02 e. OPS-2's independent stratified check is in OPS-2/cpu_parity_desc_summary.md. Conformation-dependent
  descriptors of flexible molecules can land in a different local minimum on CPU vs GPU, consistent with the section above.
- Code: inv_pipeline.py (relaxation; OPS), build_inventory_descriptors.py (descriptors; W-PHYSICS), compute_physics.py.

## Licences
AIMNet2 code MIT; weights from the AIMNet2 authors. We redistribute descriptors, not weights. NVIDIA ALCHEMI toolkit
Apache-2.0. RDKit BSD-3. FreeSASA MIT. DSSTox identifiers: US EPA public data.
Cite AIMNet2 (doi:10.1039/D4SC08572H), ETKDG (doi:10.1021/acs.jcim.5b00654), D3(BJ) (doi:10.1002/jcc.21759).
