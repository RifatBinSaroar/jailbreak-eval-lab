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

### Literature ingestion

The Python literature pipeline imports the existing Excel matrix, CSV/TSV or
structured JSON notes into a validated canonical registry and website JSON.
It preserves original attack-oriented columns, source provenance and missing
fields, reports possible duplicates, and records explicit review stages.

Start with [the very easy local run instructions](docs/LITERATURE_QUICKSTART.md).
Python, Git and VS Code are enough; npm is not required.

The initial registry contains 37 user-supplied titles only, all unreviewed and
incomplete. Imported rows are not verified paper evidence.

**v0.1 research scaffold — under construction.**

No novelty claim or experimental conclusion should be treated as established until supported by the literature review and held-out empirical evaluation.
