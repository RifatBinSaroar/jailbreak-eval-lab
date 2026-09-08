# Jailbreak Evaluation Lab

Open-source research framework for rigorous evaluation of LLM jailbreak success using general, domain-specific, and functional validators.

## Research direction

This project studies whether broad jailbreak evaluators can mismeasure success and whether narrower, subdomain-specific validation can improve agreement with human ground truth.

Current working hypothesis:

> A subdomain-specific functional validator may measure jailbreak success more accurately than broader evaluators for some harmful task categories.

This is a hypothesis to test, not an assumption.

## First study

The first paper-shaped experiment will focus on one narrow malicious-code subdomain and compare:

- a generic LLM judge,
- existing malicious-code or case-specific validation methods,
- a proposed subdomain-specific functional validator,
- and human ground truth.

Planned outcomes include precision, recall, F1, false-positive rate, false-negative rate, agreement with humans, ASR distortion, error analysis, and sensitivity of attack rankings to evaluator choice.

The first subdomain is not locked yet. Ransomware is a current working candidate, with alternatives such as spyware and network-attack-related categories still under review.

## Long-term vision

If specialised validation genuinely helps, the broader research programme may extend to multiple subdomains and an automatic routing layer that selects the appropriate evaluator for each case.

```text
prompt + response
      ↓
domain / subdomain router
      ↓
specialised validator
      ↓
evidence-backed result
```

The repository will also host a living research web interface for literature, experiments, validators, results, visualisations, and reproducible reports.

## Open-source and safety

This repository is intentionally public. Public code, metadata, documentation, and research artefacts should be designed for reproducibility without casually publishing operational harmful payloads, secrets, or uncontrolled executable material. See `SAFETY.md` once the scaffold is complete.

## Status

**v0.1 research scaffold — under construction.**

No novelty claim or experimental conclusion should be treated as established until supported by the literature review and held-out empirical evaluation.

## Experiment infrastructure (Python only)

Record existing predictions and human reference labels in immutable run bundles,
calculate metrics with explicit denominators, and rebuild website result JSON.
No models or response code are executed by these commands.

```sh
python -m unittest discover -s tests -v
python scripts/experiment.py rebuild-web
```

See [the experiment framework guide](docs/EXPERIMENT_FRAMEWORK.md) for easy local
instructions, input formats, split protections, metric definitions, and future
run recording. No npm or Python packages are required (Python 3.10+).
