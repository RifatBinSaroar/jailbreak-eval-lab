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

## Implemented offline infrastructure

The generic framework lives in `src/jailbreak_eval/experiments/`. It records
existing local decisions; it does not run this planned experiment. See
[the framework guide](../docs/EXPERIMENT_FRAMEWORK.md) for the versioned file
contract and `python scripts/experiment.py` commands.
