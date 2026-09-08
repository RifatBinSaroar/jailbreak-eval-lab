# Canonical registries

Research Platform v0.1 integrates PRs #3–#6 under one JSON Schema:
`src/jailbreak_eval/schemas/registry.schema.json`. Python validation, intake, run recording and
web export all consume that contract. `literature/paper_schema.json` is a compatibility reference.
There are exactly nine registry files. No independent website or importer scientific registry exists.

| File in registries/ | Stable ID prefix | Purpose |
| --- | --- | --- |
| papers.json | paper: | Sources, review history, evidence, interpretation, questions and novelty review |
| benchmarks.json | benchmark: | Benchmark definitions, source/version/licence provenance |
| domains.json | domain:, subdomain: | Hierarchical candidate/selected scope |
| validators.json | validator: | Versioned methods, endpoints, rubric and implementation/capture provenance |
| datasets.json | dataset: | Versioned manifests and permanent case/group split membership |
| experiments.json | experiment: | Code/config/data/method/protocol pins and human-readable EXP-001 code |
| runs.json | run: | Immutable bundle registration and full canonical input hashes |
| human_labels.json | label: | Run/case/rubric context and unresolved/consensus/adjudicated reference records |
| results.json | result: | Predictions and reproduced aggregates, descriptive analysis and artifact provenance |

Every file has `schema_version`, `registry` and `records`. Objects have `id`, `version`,
`timestamp`, `record_kind` and notes. Unknown scientific values remain null or uncomputed.
`record_kind` is research, synthetic or template. Templates are separate and rejected from
production. Synthetic records remain explicitly marked and are excluded from web output by default.

## Stable identity and revisions

`(id, version)` identifies an immutable revision. A stable ID identifies the same object throughout
its lifetime. **Append a new version under the SAME ID**; never replace/delete a prior revision.
The new timestamp must be later. The website selects the latest revision by timestamp; version
strings are opaque and are not lexically sorted.

A paper can progress listed → screened → deep-reviewed → verified with that same ID. Scientific
updates require fresh review provenance. Intake-only attachments preserve curated paper content.
The current JSON files contain the revision history; Git also retains it. `validate_history` and
`scripts/check_registry_history.py` reject deletion and same-version scientific modification.
CI checks every intervening commit as well as the final PR head.

Dataset and validator pins always resolve an exact version. Runs resolve their exact experiment
revision by SHA-256, then hash the complete pinned experiment/dataset/validator/benchmark definitions.
A later experiment revision cannot rewrite an earlier run. Nested configs/rubrics/models are
versioned definitions; artifacts are immutable by ID/hash. Never reuse a version for different content.

Finalized recorder bundles are immutable. Corrections to capture inputs or later reference labels
require a new run. The prior run-specific label/result objects remain part of that run's provenance.
This preserves the history of which observations and reference labels produced each metric.

## Capture formats versus canonical records

The PR4 JSON manifest and CSV column formats are **intake transport**, retained so existing local
captures can be recorded. The adapter validates them and normalizes them to the canonical schema.
They are not an alternate editable experiment/result registry. `canonical_inputs.json` seals the
exact canonical definitions in each bundle. Export reconstructs canonical records from captured
inputs and compares them to the registered versions before displaying any metric.

Capture identifiers are deterministically mapped to namespaced IDs with case-sensitive collision
guards. You can supply existing canonical dataset/validator/model/attack/case IDs directly. Use
`canonical_experiment_id` in a capture when an experiment already has a curated stable ID; keep
`experiment_id: "EXP-001"` for the human-readable code. New definitions need new versions when
scientific content changes, including a pilot-to-final-test protocol transition.

Imported external decisions are `external_recorded` validators, not implicitly `implemented`.
Missing provider/version/implementation details are not inferred. The captured definition and
configuration remain traceable; software cannot audit a remote implementation from its decisions.

Imported human reference rows may provide consensus/adjudication attestations and annotator IDs
without individual votes. `reference_review` preserves that limitation and the exact CSV row.
The adapter never invents individual annotations. Native adjudication records still require two
independent, context-matching annotations. Unresolved labels are excluded from classification metrics.

## Splits, metrics and evidence

Pilot is distinct from development and final test. Task, intent, prompt-family, duplicate-group,
case and response-hash membership cannot cross splits, including across dataset aliases/versions.
Final-test captures need final_evaluation purpose and a protocol frozen before capture creation.
The same protocol ID/version cannot change its definition. A frozen final-test protocol also
binds the dataset version, validators, models, attacks, code/config, seed, rubric and ablation;
changing those requires a new protocol version.
This protects recorded metadata; it cannot prove someone did not view test material elsewhere.

PR4 arithmetic is preserved: confusion matrices, accuracy, precision, recall, F1, FPR, FNR,
specificity/MCC, ASR with determinate coverage/bounds, paired ASR differences, evaluator/human
disagreement, grouped comparisons, balanced descriptive rankings and ablation metadata.
ASR differences use matched determinate cases and are in percentage points. Bounds are not
confidence intervals. Rankings are descriptive and suppressed for incomplete/unbalanced comparisons.
FX, error, indeterminate and missing predictions never become binary failures. Undefined metrics
remain null. Metric denominators preserve their actual formulas, including F1 and MCC; separate
cohort_size metadata records paired case counts. Formula components remain in the confusion matrix.

Literature intake has no paper evidence. Explicit source-linked screening/deep review can add
extraction; export displays its actual review and verification state. Novelty remains manual.

## One web build

```text
python scripts/research.py build-web
```

This calls `jailbreak_eval.registry.write_web`, producing only
`apps/web/data/research.json` with contract `research-platform/0.1`.
`jailbreak-registry export-web` and `scripts/experiment.py rebuild-web` are aliases to the same code.

The export contains canonical record projections, readiness, source-linked paper extraction,
novelty questions, and reproduced aggregate results. It omits raw predictions, individual human
labels, case membership and nested config parameters. Run records include the exact experiment and
validator versions used so a later revision cannot relabel an old result. Artifact links/hashes stay
available. Serving a whole repository locally also makes linked files accessible locally; public
publication would need an explicit artifact-release review, not a different scientific data contract.

## Validation and local persistence

```text
python scripts/research.py validate
python -m jailbreak_eval.registry validate --artifact-root .
python -m jailbreak_eval.registry validate --directory examples/registries --allow-templates
python scripts/check_registry_history.py --base FULL_BASE_COMMIT_SHA
```

Directory writes use an exclusive local lock, a staged directory and rollback on ordinary write
errors. An OS/process crash can require restoring the preserved sibling backup and clearing a stale
lock after checking no writer remains. Missing/partial input registries fail closed, never as zeros.
An immutable bundle published before a registry write failure can be registered with `experiment.py sync`.

Validation proves structure, relationships and local integrity, not truth of paper prose, genuine
human independence, source licences, remote model implementation or the existence of every declared
code commit. Analysis implementation and source/schema hashes are sealed. If analysis code changes,
retain the recorded revision to verify old bundles or deliberately create a new analysis run.
