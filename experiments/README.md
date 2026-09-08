# Experiments

Experiment code belongs here only after the protocol is written down.

## Planned first experiment

- one narrow subdomain
- shared held-out response set
- human ground truth
- 3–4 fair automated baselines
- proposed specialised validator
- primary classification metrics
- uncertainty / confidence intervals where appropriate
- ablation study
- error taxonomy
- ASR distortion analysis
- attack-ranking sensitivity analysis

Every run should save its configuration, input manifest, validator versions, random seed where relevant, and generated result artefacts.

The canonical contracts are `registries/experiments.json`, `registries/runs.json`
and `registries/results.json`. Each experiment represents one dataset version,
model version, attack-method version and split, with one or more validator
versions. Comparisons across models/attacks use multiple experiment records.

`examples/registries/` contains linked planned templates with no measured values.
See `docs/REGISTRIES.md` for version pins, lifecycle snapshots, ground-truth links,
FX handling and provenance. Adding these contracts does not authorise execution.
