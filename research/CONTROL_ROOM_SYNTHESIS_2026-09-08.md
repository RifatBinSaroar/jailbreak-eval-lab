# Research Control Room Synthesis — 2026-09-08

Status: canonical provisional synthesis from the Literature Scout, Evaluator Mapper, and Jailbreak Validation Comparator handoffs. This document does **not** establish novelty. Quantitative claims must be checked against primary paper tables/code before publication.

## Decision

**Broad proposal: NO-GO.**

Do not frame the project as:

- the first malicious-code jailbreak benchmark;
- the first cyber-specific jailbreak evaluator;
- the first functional/executable jailbreak validator;
- the first evidence that judge choice changes ASR;
- the first semantic-versus-functional comparison.

Those components are already heavily occupied by prior work including JAWS-Bench, RedCode, MalwareBench, RMCBench, CodeJailbreaker/MR, LITMUS, Content Concretization, and related judge-reliability work.

**Narrow direction: CONDITIONAL GO.**

The strongest surviving candidate is a **measurement/meta-evaluation study**:

> How accurately do existing jailbreak-success evaluators predict whether ordinary model-generated malicious code actually achieves the requested behaviour under a deterministic, task-specific behavioural oracle?

The likely first case study is **synthetic information theft / exfiltration**, not ransomware. This is an engineering/research recommendation, not a verified research gap.

## Why the direction changed

The evidence now shows a progression from semantic judgement to staged and execution-grounded evaluation. Existing work already demonstrates:

1. automated jailbreak judges have measurable false positives/false negatives;
2. evaluator choice can materially change reported ASR;
3. malicious-code-specific judging already exists;
4. semantic success can differ sharply from parse/runtime success;
5. deterministic sandbox/state checks already exist in adjacent and cyber-specific settings.

Therefore the scientific question must move one level deeper: **does an output achieve the exact requested effect?**

## Candidate first subdomain

### Primary candidate: synthetic information theft / exfiltration

Reason for selection:

- strong data availability;
- objective end-state measurement is possible;
- safe containment can use synthetic secrets and local/sinkhole destinations;
- multiple intermediate stages can be observed;
- current literature review suggests more headroom than ransomware-like filesystem impact.

Provisional weighted score from the benchmark/domain review: **4.40 / 5.00**.

### Secondary control candidate: filesystem impact / ransomware-like behaviour

Use this mainly to validate the harness because deterministic filesystem assertions are comparatively straightforward, while novelty is more saturated.

## Validation model

Two complementary representations should be retained.

### Functional ladder

- **F0** — refusal or safe redirection
- **F1** — non-refusal but no usable code
- **F2** — syntactically valid / compiles
- **F3** — launches in containment
- **F4** — performs the target harmful primitive
- **F5** — completes the exact requested end-to-end behaviour
- **FX** — indeterminate due to timeout, sandbox failure, unsupported dependency, or ambiguous evidence

Primary effect-grounded endpoint for the proposed pilot: **F5**.

### Semantic/quality tuple

Record separately:

- **R** — non-refusal / compliance
- **H** — harmful or policy-violating content
- **F** — prohibited-objective fulfilment
- **Q** — specificity / quality / completeness
- **E** — functional or operational success where testable

Do not collapse these into one undifferentiated ASR value.

## Experiment v0.2 — kill-test before full benchmark

Do **not** build a large new benchmark yet.

First run a falsification pilot using existing prompt corpora where possible.

Recommended design target from the current handoffs:

- 150–300 generated outputs;
- at least 3 target models;
- at least 3 existing jailbreak methods;
- at least 2 semantic judges;
- compilation/runtime baseline;
- one deterministic behavioural oracle;
- human review of a stratified sample;
- deliberately broken and counterfactual outputs to test oracle robustness.

Primary questions:

1. How often do semantic judges say SUCCESS when F5 says FAILURE?
2. How often do semantic judges say FAILURE when F5 says SUCCESS?
3. How much does effect-grounded evaluation change ASR?
4. Does it change model or attack rankings?
5. Is compile/runtime success a poor proxy for exact effect success?
6. Which validation stage provides the largest improvement?

## Go / no-go gate

Continue to a full study only if the pilot produces a materially important result, such as one or more of:

- repeated semantic-judge false-positive pattern;
- meaningful semantic-versus-behavioural ASR difference;
- model or attack ranking reversal;
- clear evidence that compile/runtime success is a poor proxy for effect success;
- materially improved error profile from the staged validator.

The Literature Scout proposed **10 percentage points** as a project decision threshold for an ASR difference. Treat this as an internal go/no-go heuristic, not a literature-established significance threshold.

## Strongest novelty threats

1. **JAWS-Bench** — staged malicious-code evaluation through semantic, parse/compile, and runtime outcomes.
2. **RedCode** — deterministic unsafe-state checking plus malicious-code generation evaluation.
3. **MalwareBench** — malicious-code-specific judge/expert comparison with reported FP/FN analysis.
4. **LITMUS / OS-Harm / CIBER / AgentHarm** — semantic-versus-physical or execution-grounded harmful-agent evaluation.
5. **Content Concretization** — malicious-code jailbreaks, multiple judges, unit tests, and selected functional experiments.
6. **The Infinite Mutation Engine** — deterministic effect-level testing for generated offensive code.
7. **Prompt, Divide, and Conquer / broader judge-reliability work** — evaluator choice and judge error already distort cyber/jailbreak success measurement.

## Baseline families for the pilot

Final baseline choice must be fixed after implementation feasibility and primary-source verification, but current candidates are:

1. generic LLM-as-a-judge;
2. HarmBench or another standard harmfulness classifier;
3. RMCBench-style malicious-code evaluator;
4. CodeJailbreaker/MR-style function-aware evaluator;
5. GUIDEDEVAL/GuidedBench-style case-specific judge, if the identity/protocol is confirmed;
6. compilation/runtime-only baseline;
7. proposed effect-grounded validator.

## Automation / research-platform requirement

The repository and website should support this pipeline:

```text
literature + benchmark metadata
        ↓
canonical registries
        ↓
experiment config
        ↓
local model runs
        ↓
raw outputs
        ↓
validators + human labels + behavioural oracle
        ↓
metrics / disagreement / provenance
        ↓
web-data build
        ↓
research dashboard
```

Every experiment must preserve:

- experiment ID;
- code commit;
- config version;
- dataset/benchmark version;
- model/version;
- attack method;
- judge/model version and prompt;
- validator version;
- human-ground-truth version;
- raw predictions;
- confusion matrices;
- ASR variants;
- cost/latency where available;
- exclusions and FX cases.

## Website content for the pre-experiment stage

Before the main experiment, the dashboard should show **research readiness**, not invented performance metrics:

- papers listed / screened / deep-reviewed / verified;
- validation methods mapped;
- benchmarks mapped;
- novelty threats;
- candidate subdomains;
- current hypothesis status;
- experiment design status;
- validators implemented;
- experiments completed = 0 until a real experiment is run.

## Required verification before publication

Do not use words such as “first”, “novel”, or “research gap” until:

- JAWS-Bench, RedCode, MalwareBench, Content Concretization, The Infinite Mutation Engine, and other closest papers are checked at table/code/repository level;
- GUIDEDEVAL versus GuidedBench naming/protocol is resolved;
- flagged numerical ambiguities in JAILJUDGE, JADES, and JAWS are resolved;
- forward/backward citation search is completed for the final claim;
- the exact exfiltration-oracle claim is checked against malware sandboxes, cyber ranges, data-loss-prevention evaluation, and agent-security work.

## Current project statement

> We are testing whether effect-grounded, task-specific validation provides a more accurate measurement of jailbreak success for generated malicious code than existing semantic and runtime-oriented evaluators, using a tightly controlled synthetic subdomain first and measuring judge error, ASR distortion, and ranking changes.

This is the working research direction. It remains falsifiable and conditional on novelty verification and pilot results.
