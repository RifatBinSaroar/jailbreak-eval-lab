# Offline experiment capture and immutable runs

This framework records **already collected decisions**. It has no model caller, attack generator,
validator executor or sandbox. Safe synthetic fixtures are used only in tests. Start with
[PLATFORM_QUICKSTART.md](PLATFORM_QUICKSTART.md) for copyable commands.

## Inputs

The PR4 capture formats remain supported as immutable intake transport. The recorder immediately
maps them into the single nine-registry contract; there is no parallel scientific result registry.
The files in `tests/fixtures/run_framework/` are complete benign format examples, explicitly marked
synthetic. They are not research measurements, implementation evidence or real human annotations.

The capture manifest records:

| Field | Meaning |
| --- | --- |
| schema_version | Capture transport version, currently 1.0 |
| experiment_id | Human-readable code such as EXP-001 |
| canonical_experiment_id | Optional existing stable experiment: ID |
| run_id | New immutable bundle name, such as RUN-PILOT-001 |
| created_at | Timezone-aware capture/recording event time |
| split / purpose | development/development, pilot/pilot, test/final_evaluation |
| record_kind | research or synthetic, matching the dataset capture |
| code_commit | Full declared collection/code commit; zero commit allowed only for synthetic fixtures |
| config_version / config | Versioned capture configuration |
| protocol | ID/version, success definition, human-label policy, ASR denominator, frozen_at |
| dataset | Exact dataset ID/version and raw manifest SHA-256 |
| models / attack_methods | IDs, names, versions and supplied configuration |
| validators | IDs, names, versions, config and success_construct |
| human_ground_truth | Reference version, rubric_version and supplied source description |
| seed / ablation | Explicit seed or null; study/variant/components or null |

For final test, the protocol must be frozen no later than created_at and purpose must be
final_evaluation. Pilot does not bypass membership checks and cannot become final-test data.

Existing canonical dataset, validator, model, attack and case IDs can be supplied directly in the
capture. Otherwise deterministic, case-sensitive namespaced IDs are allocated. Preserve the capture
ID throughout the object's lifetime. Set `canonical_experiment_id` when continuing an already
curated experiment; retain `experiment_id` as its EXP-001 code. A materially different version of
an experiment/dataset/validator needs a new version, not a new stable object ID.

## Dataset manifest

A manifest has schema_version, dataset_id, version, record_kind, provenance and cases.
Provenance preserves source, source_version, licence text, retrieved_at, nullable
redistribution_allowed and transformations. A case has:

```text
case_id, task_id, attempt_id, split, base_intent_id, prompt_family_id,
duplicate_group_id, response_sha256, model_id, attack_method_id
```

Case/intent/family/duplicate-group/task/response-hash memberships are protected across versions
and dataset aliases. A task/attempt/model/attack condition cannot be duplicated. The exact full
manifest is snapshotted and checksummed. Per-case response SHA-256 values bind the declared outputs;
raw model-response bytes need not be published. A manifest hash is not a claim that the recorder
fetched or executed the response. Keep raw outputs in your approved local collection workflow.

## Predictions CSV

Exact columns:

```text
case_id,validator_id,predicted_success,status,functional_level,score,r,h,f,q,e,error_type,evidence_ref
```

- status=ok requires 0 or 1 for predicted_success.
- indeterminate/error requires a blank decision and blank score; error requires error_type.
- Missing CSV rows produce explicit canonical missing predictions.
- F0–F5/FX are retained. FX must stay indeterminate/error, never failure.
- For the explicit F5 endpoint, a determinate functional stage must agree with the binary decision.
- R/H/F/Q/E and score preserve supplied values in [0,1] or blank. They are not collapsed into ASR.
- Unspecified cells stay unknown. Quotes, embedded newlines and original CSV bytes are preserved.

## Human reference CSV

Exact columns:

```text
label_id,case_id,label,status,annotator_ids,adjudicator_id,evidence_ref
```

One reference row per case. Consensus/adjudicated rows require a 0/1 label, evidence reference,
and at least two distinct annotator IDs separated by `|`. Adjudicated rows also require an
adjudicator ID. Uncertain/unreviewed capture rows must have blank labels and become canonical
unresolved records. Missing rows remain missing; neither enters classification ground truth.

These imported rows attest to a resolved reference. They do not supply each annotator's individual
vote. The canonical `reference_review` preserves the attestation and source row without inventing
votes. The native canonical human-label contract also supports independent annotation records and
adjudications referencing two context-matching independent annotations.

## Recording, checking and recovery

```text
python scripts/experiment.py validate --manifest my-input/manifest.json --dataset my-input/dataset_manifest.json --predictions my-input/predictions.csv --labels my-input/human_labels.csv
python scripts/experiment.py record --manifest my-input/manifest.json --dataset my-input/dataset_manifest.json --predictions my-input/predictions.csv --labels my-input/human_labels.csv
python scripts/experiment.py verify results/runs/RUN-YOUR-ID
python scripts/research.py build-web
```

Use --directory, --runs-dir and --project-root for an isolated workspace. All nine registry files
must already exist; clone the repository for production work or use an empty nine-file set for
isolated tests. Never label a synthetic fixture as research.

A run contains manifest.json, canonical_inputs.json, dataset_manifest.json, predictions.csv,
human_labels.csv, metrics.json and errors.json. The capture manifest seals byte sizes, SHA-256
hashes and the analysis implementation/schema identity. Canonical run metadata pins the full
experiment and input definitions and points to the manifest checksum. Canonical predictions,
labels and aggregates are reconstructed from the bundle. Named capture definitions are also kept
as content-addressed artifacts under `data/manifests/captured/`.

The recorded run's completed status means the **offline recording and analysis** completed.
Capture created_at is used for that recorder event. Unknown model-execution start/finish times and
runtime environments are not inferred; recording_only and null environment make this explicit.
Imported validator decisions are external_recorded, not a claim that this repository implemented
or audited the validator.

Registry definition/split validation happens before bundle publication. If publication of canonical
outputs then fails, the immutable bundle remains recoverable:

```text
python scripts/experiment.py sync results/runs/RUN-YOUR-ID
```

Sync verifies the entire bundle, rebuilds canonical records and appends only missing identical
revisions. It does not replace existing scientific records or edit the run. Retain the original
analysis code revision for old bundles; changed analysis code intentionally causes verification to
fail rather than silently changing results. Use a new analysis/run ID for deliberate recomputation.

## Metrics and website export

Preserved PR4 analysis includes confusion counts, accuracy, precision, recall, F1, FPR/FNR,
specificity/MCC, ASR per evaluator with coverage and all-case bounds, paired ASR differences,
evaluator disagreement, human-reference distortion, model/attack grouping, balanced descriptive
rankings/rank changes and ablation metadata. No automatic pooling across runs, endpoints or splits.

Classification uses resolved-human ∩ determinate-evaluator cases. ASR uses determinate predictions;
coverage and unresolved counts accompany it. Pairwise comparisons use shared determinate cases.
Undefined denominators produce null. All-case bounds are identification bounds, not confidence
intervals. Rankings require balanced task/attempt/other-condition grids and complete evaluator
coverage; they are descriptive, not statistical significance claims.

There is one web build: `python scripts/research.py build-web`. It checks immutable artifacts,
recomputes every analysis and compares generated canonical records to the registries. Hand-entered
metrics, stale scientific versions and missing/tampered bundles block the export. The previous good
web file remains intact after a failure. Synthetic runs are excluded by default; explicit
--include-synthetic previews stay labelled synthetic and are never production findings.
