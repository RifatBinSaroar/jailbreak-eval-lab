# Literature Matrix Ingest Plan v0.1

Source workbook: `Jalibreak Literature Matrix.xlsx` (user-supplied working matrix)

## Current inventory

- 37 paper titles are listed.
- 12 rows currently contain the full original 19-column review record.
- 25 rows are currently title-only / not yet completed.
- The original matrix was designed mainly for the earlier attack/new-method direction, so it is useful historical research data but is not yet sufficient as the canonical evidence database for the validation project.

## Existing matrix fields

The workbook currently tracks: Paper, Year, Venue, Category, Attack Type, White/Black Box, Main Idea, Models Tested, Benchmark, Evaluation Metric, Main Result, Limitation, Future Work, Code/Data, My Understanding, Questions, How the Request is Transformed, SoK Relevance, and New-Method Relevance.

These fields should be preserved rather than discarded. Attack-specific fields remain useful for attack papers, but the validation project needs a second layer of structured fields.

## Validation-project fields required in the canonical record

The repository schema in `paper_schema.json` adds the fields needed for the new direction:

- research problem;
- benchmark;
- domain and subdomains;
- exact success definition;
- validator / judge;
- labels or score;
- evaluation type: semantic / static / functional / behavioural / hybrid;
- whether code is executed;
- human ground truth / reference-label procedure;
- metrics;
- false-positive evidence;
- false-negative evidence;
- author limitations;
- paper-demonstrated claims;
- our interpretation;
- open questions;
- novelty threat;
- evidence status.

## Evidence discipline

The import must never silently turn the user's notes into verified paper facts.

Every record must separate:

1. `paper_demonstrates` — directly supported by the paper or audited primary source;
2. `our_interpretation` — project interpretation;
3. `open_questions` — unresolved items;
4. `evidence_status` — screened / deep-reviewed / verified.

Unverified quantitative claims must remain visibly provisional until checked against the primary paper.

## Immediate priorities

The current matrix already contains useful completed records for papers including the two SoKs, JailbreakHub/DAN, GCG, PAIR, LLM-Fuzzer, WordGame, GuidedBench, WildGuard, DUALBREACH, Refusal Direction, and NeuroStrike.

For the validation project, the highest-priority incomplete or missing records are the evaluation/benchmark papers and direct novelty threats, especially RMCBench, HarmBench, JailbreakBench, CodeJailbreaker / Smoke and Mirrors, RedCode, StrongREJECT, and any recent functional/executable malicious-code evaluation work found by the specialist agents.

## Website behaviour

The website should display real research-readiness counts from the canonical registry, such as:

- papers listed;
- papers deep-reviewed;
- papers verified;
- validators mapped;
- benchmarks mapped;
- candidate subdomains;
- experiments completed.

It must not display invented performance metrics before experiments are run.

## Automation target

The local research workflow should become:

```text
Excel / structured paper handoffs
        ↓
import + validation script
        ↓
canonical literature registry
        ↓
web-data build step
        ↓
research dashboard
```

The Excel workbook remains useful as a human-editable working view, while the repository JSON becomes the machine-readable canonical layer used by experiments and the web interface.
