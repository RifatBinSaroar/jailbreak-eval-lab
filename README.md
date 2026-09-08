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

## Research Platform v0.1

Start here: **[Very easy Python + VS Code + Live Server instructions](docs/PLATFORM_QUICKSTART.md)**.
No npm is needed. This integration reconciles PRs #3–#6; it does not run the study.

```text
python -m pip install -e .
python scripts/research.py validate
python scripts/research.py build-web
```

Open `apps/web/index.html` with VS Code Live Server. The eight dashboard views use one canonical
export from the nine registries. Papers retain stable IDs and versioned review history. Locally
collected outputs can be recorded as immutable bundles with reproduced metrics and provenance.

The initial state is **47 listed reading entries, 7 planned validators, 3 benchmark candidates,
3 domain/subdomain entries, zero experiments and zero measured results**. There are no verified
literature findings or inferred novelty claims in this release.

- [Canonical data model and lifecycle](docs/REGISTRIES.md)
- [Literature import and review](docs/LITERATURE_QUICKSTART.md)
- [Offline experiment capture and analysis](docs/EXPERIMENT_FRAMEWORK.md)
- [Integration reconciliation and test handoff](docs/INTEGRATION_V0_1.md)

No novelty claim or experimental conclusion is established until supported by literature review
and held-out empirical evaluation.
