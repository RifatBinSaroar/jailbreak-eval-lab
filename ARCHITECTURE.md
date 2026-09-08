# Architecture

The repository is organised around four linked research assets: literature evidence, benchmark/response data, validator implementations, and reproducible experiment results.

```text
literature evidence
       ↓
research definitions
       ↓
shared evaluation cases
       ↓
validator adapters
       ↓
standard validation results
       ↓
metrics / error analysis / ASR analysis
       ↓
web dashboard
```

## Planned repository structure

```text
jailbreak-eval-lab/
├── literature/
├── data/
├── src/jailbreak_eval/
│   ├── schemas/
│   ├── validators/
│   ├── routing/
│   └── metrics/
├── experiments/
├── configs/
├── tests/
├── results/
├── apps/web/
├── scripts/
└── docs/
```

## Core abstraction

Every validator should accept the same `EvaluationCase` and return the same `ValidationResult` shape. Baselines and proposed methods should therefore be comparable without custom result-processing logic.

The first implementation should remain deliberately simple. Routing and multi-subdomain orchestration are future layers, not prerequisites for the first experiment.

## Research Platform v0.1 integration

Exactly nine JSON registries share one packaged canonical schema. Records are append-only revisions
keyed by (stable ID, version). New versions keep the same object ID and a later timestamp. Git
history checks reject silent deletion and unversioned changes. Full input hashes pin old runs to
exact experiment, dataset, validator and benchmark revisions.

The literature input reader preserves XLSX/CSV/JSON/JSONL cells and provenance in immutable intake
artifacts. It adds listed papers; explicit source-linked curator revisions advance review. It does
not automatically promote matrix notes to evidence or infer novelty.

The offline recorder accepts existing capture manifests and CSV decisions, computes PR4 metrics,
seals immutable run artifacts and populates the canonical experiment/run/label/result registries.
Capture formats are intake transport only. No model, attack, validator or generated code executes.

One exporter, `jailbreak_eval.registry.write_web`, validates all canonical inputs and verifies/replays
recorded analysis before producing `apps/web/data/research.json`. The eight-view zero-build dashboard
renders those canonical projections. It defines no scientific records and never stores measured
metrics in HTML. See `docs/REGISTRIES.md` for pins, synthetic exclusion and verification boundaries.
