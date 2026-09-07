# Agent Operating Rules

This repository may be worked on by multiple research and coding agents. Parallel work is useful only when all agents share the same scientific definitions and evidence rules.

## Canonical control files

Agents must read these before making substantive changes:

- `RESEARCH_PLAN.md`
- `EVIDENCE_RULES.md`
- `SAFETY.md`
- this file

## Research roles

- **Literature Scout** — find the closest evaluation literature.
- **Novelty Killer** — actively search for prior work that occupies the proposed contribution.
- **Deep Paper Analyst** — extract evaluation methodology from supplied or retrieved papers.
- **Domain Mapper** — map benchmark domains and subdomains.
- **Evaluator Mapper** — compare success definitions, judges, functional checks, ground truth, and failure modes.
- **Experiment Designer** — design a fair experiment that can falsify the hypothesis.

## Engineering roles

- **Research Software Architect** — maintain package boundaries, schemas, interfaces, and reproducibility.
- **Validator Engineer** — implement baseline and proposed validator adapters behind a common interface.
- **Experiment Engineer** — build deterministic experiment runners, manifests, and result artefacts.
- **Website Engineer** — build the research dashboard from structured repository data rather than hard-coded claims.
- **Testing / Reproducibility Reviewer** — check tests, deterministic behaviour, provenance, split leakage, and result reproducibility.

## Non-negotiable rules

1. Do not claim novelty because a search found nothing.
2. Separate paper evidence from interpretation.
3. Do not change the definition of success silently.
4. Do not tune on the held-out test split.
5. Do not publish secrets, credentials, uncontrolled executable payloads, or host-unsafe fixtures.
6. Prefer safe synthetic fixtures in automated tests.
7. Any metric shown on the website must trace to a reproducible result artefact.
8. Any literature claim shown on the website must trace to a structured paper record.
9. Any change affecting labels, scoring, or ground truth requires explicit review in the pull request.
