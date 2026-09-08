# Web export contract v1

These are read-only presentation exports, not a replacement for canonical research registries. `project.json` is presentation guidance; other files are entity collections. Keep research content in JSON, not in the HTML or JavaScript. The browser has no dependency on an importer package.

## File envelopes and stable IDs

The preferred collection shape is `{"schema_version": 1, "records": []}`. Bare arrays and named envelopes such as `{"papers": []}` are also accepted for importer integration. An explicitly supplied `schema_version` must be the number `1`.

| File | Required unique record ID | Role |
| --- | --- | --- |
| `papers.json` | `paper_id` | Reading queue and paper extraction |
| `validators.json` | `validator_id` | Method mappings |
| `benchmarks.json` | `benchmark_id` | Benchmark and dataset readiness |
| `domains.json` | `domain_id` | Hierarchy using nullable `parent_id` |
| `experiments.json` | `experiment_id` | Experiment registry, e.g. `EXP-001` once registered |
| `results.json` | `result_id` | One evaluator/result record for one run and split |
| `gaps.json` | `gap_id` | Evidence issues, candidate questions and novelty threats |

IDs must be non-empty strings and unique within each collection. The `WEB-*` IDs shipped here are provisional web planning IDs. When a canonical importer supplies permanent IDs, replace the provisional records and update all `paper_ids`, `parent_id`, `experiment_id` and `validator_id` references in the same export. Do not append duplicate papers under unrelated IDs. Canonical paper deduplication belongs in the importer; the UI only rejects duplicate stable IDs.

All collection records may have `source_links: [{"label": "Source description", "url": "https://…"}]`. Use direct primary sources for paper claims and version-pinned repository documents for project interpretations. Sources open in a new tab when external. Only HTTP(S) and repository-relative file URLs are linkable; HTML is rendered as text. Export public, licensed metadata and artifacts only.

## Project guidance

`project.json` has `schema_version: 1` and a `project` object:

| Field | Shape / use |
| --- | --- |
| `project_id`, `hypothesis` | Required non-empty strings |
| `direction`, `status`, `decision` | Working direction and project interpretation |
| `as_of` | Guidance snapshot date, not a run timestamp |
| `candidate`, `candidate_note` | Provisional first case and its qualification |
| `scope_note`, `novelty_note` | Export coverage and unresolved novelty status |
| `readiness` | Required array of `{id, title, status, detail, view}` |
| `readiness[].status` | `pending`, `in-progress`, `complete` or `blocked`; supplied explicitly |
| `readiness[].view` | One of the eight route names in the sidebar |
| `planned_outcomes`, `open_questions` | Arrays of strings; not measured values |
| `source_links` | Source records as described above |

## Papers

The presentation fields align with `literature/paper_schema.json`; this export additionally supports **unreviewed** reading-queue entries and null metadata, so it is deliberately not that canonical schema. Unreviewed entries do not count as screened or verified.

Required: `paper_id`, `title`, `evidence_status` (`unreviewed`, `screened`, `deep-reviewed`, `verified`). Reviewed records also require a direct HTTP(S) `url`. Never promote an entry just because its fields are populated. A source document listing a title is not a primary-paper source.

Supported extraction fields:

- `year`, `venue_or_arxiv`, `url`, `domain`, `subdomains`, `benchmark`;
- `success_definition`, `validator`, `labels_or_score`, `evaluation_type`, `executes_code`;
- `human_ground_truth`, `metrics` (metric **names**, not our measured results);
- `false_positive_evidence`, `false_negative_evidence`, `authors_limitations`;
- `paper_demonstrates`, `our_interpretation`, `open_questions` (separate arrays of strings);
- `novelty_threat` (normally `LOW`, `MEDIUM`, `HIGH`, `FATAL`, `UNKNOWN`);
- `original_matrix` (optional object preserving the user's original attack-oriented columns);
- `source_links` (provenance of extraction or provisional queue entry).

Use `null` for unknown scalar metadata and empty arrays for unextracted list fields. The UI names missing key fields and displays boolean `false` differently from unknown. Paper-demonstrated claims are withheld if the direct source URL is absent. Review status is declared metadata, not an independent browser verification of the paper.

## Mappings and planning

| Collection | Display fields |
| --- | --- |
| Validators | `name`, `role`, `status` (`planned` or `implemented`), `evaluation_type` (display string), `version`, `success_definition`, `implementation_url`, `our_interpretation`, `open_questions` |
| Benchmarks | `name`, `status`, `version`, `licence`, `redistribution` (`true`, `false`, `null`), `split`, `dataset_manifest` (URL), `paper_ids`, `our_interpretation`, `open_questions` |
| Domains | `name`, `parent_id` (`null` for a root), `status`, `our_interpretation`, `open_questions` |
| Experiments | `title`, `description`, `status` (e.g. `planned`, `in-progress`, `completed`), `dataset_version`, `development_manifest`, `test_manifest`, `validator_ids`, `model`, `attack_method`, `config_version`, `config_url`, `code_commit`, `success_definition` |
| Gaps | `title`, `kind`, `status`, `paper_ids`, `our_interpretation`, `open_questions` |

All support `source_links`. Domain parents must exist; self-links and cycles are rejected. Paper references link to extraction details; missing referenced paper records are visibly unavailable. Missing mapping metadata stays **Not recorded**. Do not mark a validator implemented without an actual versioned implementation. Experiment registration is independent of the project readiness checklist.

## Measured results

The initial `results.json` is intentionally empty. No numeric example belongs in the served data directory. One result record represents one evaluator on one declared run/split. It must contain:

| Field | Required content |
| --- | --- |
| `result_id` | Unique string |
| `kind` | Exactly `measured` |
| `experiment_id`, `validator_id` | IDs present in their loaded registries |
| `is_example`, `is_synthetic` | Must not be `true`; exclude examples from production exports |
| `sample_size` | Positive integer measured case count |
| `success_definition` | Explicit measured endpoint |
| `metrics` | Object of supported metric keys; at least one numeric measurement |
| `comparison` | Required for `asr_difference`: direction, reference evaluator and comparable case population |
| `notes` | Optional denominator, exclusions, undefined-metric and interpretation qualifications |
| `provenance` | Object with the fields below |

Required `provenance` fields: `run_id`, `dataset_version`, `validator_version`, `model`, `attack_method`, `config_version`, `human_labels_version`, `code_commit` (full 40-character SHA), `timestamp` (ISO timestamp with timezone), `split` (`development` or `test`), `artifacts`.

`provenance.artifacts` requires linkable `manifest`, `predictions`, `metrics` and `human_labels` files. Additional artifacts, such as errors or config, may be linked too. For a server rooted at the repository, a run manifest link can be `../../results/runs/<run-id>/manifest.json`. Version-pinned HTTP(S) links also work. Serve the whole repository when following relative links outside `apps/web/`.

Supported metric keys: `accuracy`, `precision`, `recall`, `f1`, `false_positive_rate`, `false_negative_rate`, `asr`, `asr_difference`, `disagreement`. Values are JSON numbers in `[0,1]`, or `null` for an undefined/not-measured quantity; `asr_difference` allows `[-1,1]`. Do not send percentage values such as `90` for a fraction. Unknown keys, numeric strings, non-finite/out-of-range numbers, missing provenance or missing linked records withhold that record.

The UI converts supplied fractions to percentages for display (two decimal places); ASR differences are percentage points. It performs no evaluator scoring or cross-record aggregation. Keep confusion matrices, rankings and ablations in source artifacts until an explicit comparison/export contract exists. Artifact links are not fetched or recomputed by the UI; generating and scientifically verifying them is the result exporter's responsibility.
