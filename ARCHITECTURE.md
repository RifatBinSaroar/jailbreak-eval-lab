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
