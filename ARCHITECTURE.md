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

## Canonical registry layer

`registries/{papers,benchmarks,domains,validators,datasets,experiments,runs,human_labels,results}.json`
is the canonical metadata layer. Domains and subdomains share an explicit parent
hierarchy. The single JSON Schema is packaged at
`src/jailbreak_eval/schemas/registry.schema.json`. `jailbreak_eval.registry` checks
both that schema and relationships including version pins, dataset split
consistency, evidence links and run input hashes.

Experiment definitions pin dataset/validator versions, configuration, model,
attack metadata, protocol and code commit. Runs bind those full definitions by
hash. Predictions, human labels and aggregates refer to the exact run and input
artefacts. Artefacts carry stable IDs, locations and SHA-256 checksums. Research
records are append-only once committed; history validation enforces this policy.

The existing `EvaluationCase`, `ValidationResult` and `Validator` interface remain
unchanged. Their in-memory outputs are **not** canonical registry result records:
a future ingestion adapter must supply the full provenance contract. There is no
runner, evaluation adapter, metric calculator or executable benchmark in this layer.

`export-web` produces a deterministic production JSON view with actual readiness
counts, source-linked verified paper evidence and recorded aggregate metrics.
Website code can use ordinary `fetch()` and `response.json()`. The export does
not copy raw inputs, human labels or arbitrary configs. See `docs/REGISTRIES.md`.
