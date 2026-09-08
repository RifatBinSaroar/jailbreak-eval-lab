# Offline experiment and run framework

This framework records existing evaluator decisions, validates their provenance,
and derives reproducible metrics. It never generates responses, invokes a model
or validator, executes response code, fetches datasets, or runs the main study.
Actual collection and validator execution remain a future, separately reviewed
local workflow. The existing `EvaluationCase`, `ValidationResult`, and `Validator`
interfaces remain available to that workflow.

## Research inputs read before implementation

- `RESEARCH_PLAN.md`, `AGENTS.md`, `EVIDENCE_RULES.md`, `SAFETY.md`, and `ARCHITECTURE.md`
  on main at `9f673eadaa2b2364aa08f4cb4d2462e566ac7f80`.
- [Control-room synthesis, 2026-09-08](https://github.com/RifatBinSaroar/jailbreak-eval-lab/blob/108e3cb9d74d844c909f74f227a7d1ba40a7c3a9/research/CONTROL_ROOM_SYNTHESIS_2026-09-08.md),
  read from `web-v0.1-static` because it was absent from main at implementation.

The synthesis takes precedence for the provisional research direction. This
generic infrastructure locks no domain, baseline, novelty claim, or go/no-go
threshold. F0–F5/FX and R/H/F/Q/E remain separate observations. No synthesis
numbers or preliminary experimental ASRs have been copied into website results.

## Start here — Python and Git only

Requires Python **3.10 or newer**. No npm, pip packages, virtual environment,
or web build is needed. Open the repository folder in VS Code, then open
**Terminal → New Terminal**. Check out this PR branch and run:

```sh
git fetch origin
git switch feat/experiment-run-framework
python --version
python -m unittest discover -s tests -v
python scripts/experiment.py rebuild-web
```

If your computer calls Python `python3` or `py`, substitute that for `python`.
The tests create temporary synthetic run bundles and remove them automatically.
The rebuild writes `apps/web/data/results.json`. With no research runs it contains
an empty `runs` array and `research_run_count: 0`, with no performance values.

To inspect the command options:

```sh
python scripts/experiment.py --help
python scripts/experiment.py record --help
```

## Future local workflow

1. Review and version the experiment protocol, success definition, annotation
   rubric, decision thresholds, denominator policy, and evaluator configuration.
2. Assign a stable experiment ID such as `EXP-001`. Freeze a **full** dataset
   manifest covering the development and test assignments. Split by base intent,
   prompt family, and near-duplicate group before tuning.
3. Preserve responses in your approved local storage. The manifest stores their
   SHA-256 and case/condition IDs; this tool needs no response text.
4. Collect validator predictions and independent human annotations through the
   separately approved local process. Resolve reference rows using the protocol.
   Keep raw independent annotations behind the reference rows' `evidence_ref`.
5. Create a run input manifest and CSVs below. Validate, then record them using
   a new run ID. The command copies exact input bytes and derives metrics.
6. Rebuild website JSON. Review publishable metadata and redistribution rights
   before committing run artifacts. Corrections create a **new run ID**, never
   edit an existing run bundle.

Example commands for **your future local inputs**, not bundled experiment data:

```sh
python scripts/experiment.py validate --manifest configs/my-run.json --dataset data/manifests/my-dataset.json --predictions data/derived/my-predictions.csv --labels data/human_labels/my-reference.csv
python scripts/experiment.py record --manifest configs/my-run.json --dataset data/manifests/my-dataset.json --predictions data/derived/my-predictions.csv --labels data/human_labels/my-reference.csv
python scripts/experiment.py verify results/runs/RUN-YOUR-ID
python scripts/experiment.py rebuild-web
```

`--runs-dir` and `--output` accept other local paths. Relative paths resolve from
your terminal's current folder. Run `rebuild-web` from the repository root for
the default paths. Python imports also work after a normal optional package
installation; the source-checkout script does not need installation.

The old YAML example is a research sketch, not an executable configuration.
This command accepts the versioned JSON contract described here. Its complete
synthetic format reference is in `tests/fixtures/run_framework/`; those files
must stay marked synthetic. Populate real fields from source records, not from
the fixture's placeholders. There is no automatic inference of missing metadata.

## Saved structure and integrity

Each recorded run contains exactly:

```text
results/runs/<run-id>/manifest.json
results/runs/<run-id>/dataset_manifest.json
results/runs/<run-id>/predictions.csv
results/runs/<run-id>/human_labels.csv
results/runs/<run-id>/metrics.json
results/runs/<run-id>/errors.json
```

The saved manifest contains the full input configuration plus SHA-256 and byte
length for all five other files. It also records the analysis version and a
hash of the analysis implementation. The run appears only after all files have
been written. Existing run IDs cannot be overwritten. These hashes detect
changes; they are not a cryptographic attestation of who collected the data.
`code_commit` is the supplied collection/evaluation commit and must be a full
SHA. Its existence and a clean collection checkout remain the collector's duty.
The independent analysis fingerprint identifies the derivation code used here.

`verify` rechecks all inputs and recomputes metrics/errors byte for byte.
`rebuild-web` does the same before writing anything. Malformed, incomplete,
changed, duplicate, wrong-split, or non-reproducible inputs cause a nonzero exit
and preserve the previous website file. Paths inside run bundles cannot be
symlinks. The output must be outside the immutable runs directory.

Keep the generating code revision with the run. If the analysis implementation
changes, check out its recorded version to reproduce old bundles, or deliberately
create a new run from the original inputs under the new implementation. Do not
rewrite old metrics. Mixed analysis implementations need a future explicit
migration/version-dispatch design, rather than silent recomputation.

## Dataset manifest contract, schema_version `1.0`

Unknown top-level fields are rejected. JSON objects reject duplicate keys and
non-finite numbers. IDs use letters, numbers, underscores, dots and hyphens,
start with a letter/number, and have a maximum length of 128 characters.

| Field | Meaning |
|---|---|
| `schema_version` | `"1.0"` |
| `dataset_id`, `version` | Stable dataset identity and exact version |
| `record_kind` | `research` or `synthetic` |
| `provenance` | `source`, `source_version`, `license`, timezone-aware `retrieved_at`, `redistribution_allowed` (`true`/`false`/`null`), and `transformations` list |
| `cases` | Nonempty list of metadata-only case rows below |

Every case requires `case_id`, `task_id`, `attempt_id`, `split`, `base_intent_id`,
`prompt_family_id`, `duplicate_group_id`, `response_sha256`, `model_id`, and
`attack_method_id`. The SHA-256 is the lowercase hash of the stored response
bytes. `task_id` identifies the same evaluation task across methods/models;
`attempt_id` identifies a prespecified replicate within that condition.

`split` is exactly `development` or `test`. A case ID is unique, and a
task/attempt/model/attack combination cannot repeat. Tasks, base intents,
prompt families, duplicate groups, and identical response hashes cannot cross
splits. Exact repeated refusals are conservatively caught by the response-hash
guard too; resolve the split/data protocol explicitly rather than disguising
duplicate responses. Group quality still requires researcher review; this
tool does not discover semantic near-duplicates.

The entire dataset manifest is copied into each run, while only the selected
split is scored. This lets the validator check leakage against the other split.
The website builder also rejects conflicting hashes under the same dataset
ID/version and split reassignment across versions under the same dataset ID.
It cannot detect hidden prior test exposure or intentionally renamed datasets.

## Run input manifest contract, schema_version `1.0`

| Field | Meaning |
|---|---|
| `experiment_id` | `EXP-` followed by at least three digits, e.g. `EXP-001` |
| `run_id` | Unique filename-safe `RUN-...` ID, at most 124 characters |
| `created_at` | Collection timestamp with timezone, e.g. ISO 8601 with `Z` |
| `split`, `purpose` | `development` with `development`, or `test` with `final_evaluation` |
| `record_kind` | Must match the dataset's `research`/`synthetic` value |
| `code_commit` | Full lowercase 40-character collection/evaluation Git SHA; zero fixture SHA only allowed for synthetic records |
| `config_version`, `config` | Nonempty version and exact JSON configuration snapshot |
| `protocol` | Fields described below |
| `dataset` | Exact `dataset_id`, `version`, and SHA-256 of dataset manifest bytes |
| `models` | List of `model_id`, `name`, exact `version`, and `config` objects |
| `attack_methods` | List of `attack_method_id`, `name`, `version`, and `config` objects |
| `validators` | List of `validator_id`, `name`, `version`, `success_construct`, and `config` objects |
| `human_ground_truth` | Nonempty `version`, `rubric_version`, and `source` |
| `seed` | Integer, or `null` when no randomness was used |
| `ablation` | `null` or `{study_id, variant_id, components: [...]}` |

Model and attack metadata must exactly cover the selected split. Validator IDs
must be unique. For an LLM judge, place its model/version, full judge prompt
or immutable prompt reference/hash, generation parameters and thresholds in
the validator's `config`. For deterministic checks, version the check/oracle
and its environment there. Config is preserved locally but omitted from the
aggregate website JSON. Empty config means no configuration, not unknown values.

`protocol` requires `protocol_id`, `version`, `success_definition`,
`human_label_policy`, `asr_denominator`, and `frozen_at`. This version supports
only `asr_denominator: "determinate_predictions"` with explicit coverage/bounds.
`frozen_at` can be null during development. Test runs require a timezone-aware
freeze timestamp no later than `created_at`. This is an auditable declaration,
not an enforcement system for a researcher's prior access to test cases.

`success_construct` names what each evaluator's binary output actually measures,
such as `R`, `H`, `F`, `Q`, `E`, or `F5`. Comparisons keep these names so a
semantic positive is never silently relabelled as effect-grounded success.

## Prediction CSV

UTF-8 CSV with exactly these columns (order may vary), one row per
`case_id`/`validator_id` pair in the selected split:

```csv
case_id,validator_id,predicted_success,status,functional_level,score,r,h,f,q,e,error_type,evidence_ref
```

- `status`: `ok`, `indeterminate`, or `error`.
- `predicted_success`: `0` or `1` for `ok`; blank for other statuses. Never
  convert a timeout, unsupported dependency, or absent prediction to failure.
- `functional_level`: blank when unobserved, or `F0`…`F5`/`FX`. `FX` requires
  indeterminate/error status. For the `F5` endpoint, an observed `F5` is positive
  and observed `F0`–`F4` are negative; contradictory binary rows are rejected.
- `score`, `r`, `h`, `f`, `q`, `e`: optional finite values in `[0,1]`. Any
  normalization or score-to-binary threshold belongs in the frozen config.
  These observations are retained separately and never collapsed by this tool.
- `error_type`: required for `error`, blank otherwise.
- `evidence_ref`: optional opaque reference to retained decision evidence; it
  is preserved byte for byte and never fetched by this program.

Missing rows are counted explicitly as missing predictions; no synthetic rows
are inserted into your CSV. An empty CSV with the correct header is valid and
produces unknown metrics, not fabricated zeros. Unknown/wrong-split IDs,
duplicate predictions, malformed rows, and invalid scores fail validation.

## Human reference CSV

UTF-8 CSV with exactly these columns, one reference row per case:

```csv
label_id,case_id,label,status,annotator_ids,adjudicator_id,evidence_ref
```

`label_id` is a stable unique ID. `status` is `consensus`, `adjudicated`,
`uncertain`, or `unreviewed`. Only consensus/adjudicated rows contribute to
classification metrics. They require `label` 0/1, at least two distinct
pseudonymous annotator IDs separated by `|`, and an evidence reference to the
underlying annotations. Adjudicated rows also require `adjudicator_id`.
The protocol must specify expertise, blinding, independence, and adjudication;
these cannot be established by the presence of IDs alone.

Uncertain/unreviewed labels must be blank; missing reference rows are allowed
and reported. A single review is not automatically ground truth. Raw annotation
storage, blinding tools, adjudication workflow and inter-annotator agreement are
future work. No label is derived from an evaluator prediction.

## Metric definitions

`1` means success under the declared construct. For each evaluator, truth and
prediction are joined by case ID. Confusion matrices use human truth as rows
and evaluator prediction as columns: TP=(1,1), TN=(0,0), FP=(0,1), FN=(1,0).

| Metric | Formula |
|---|---|
| Accuracy | `(TP + TN) / (TP + TN + FP + FN)` |
| Precision | `TP / (TP + FP)` |
| Recall | `TP / (TP + FN)` |
| F1 | `2TP / (2TP + FP + FN)` |
| False-positive rate | `FP / (FP + TN)` |
| False-negative rate | `FN / (FN + TP)` |
| Specificity | `TN / (TN + FP)` |
| MCC | `(TP×TN − FP×FN) / sqrt((TP+FP)(TP+FN)(TN+FP)(TN+FN))` |
| Evaluator ASR | Positive predictions / determinate predictions |
| Paired ASR difference | `100 × (positive_A − positive_B) / common determinate cases` |
| Evaluator disagreement | Different binary decisions / common determinate cases |

Zero denominators produce JSON `null`, not zero, NaN, or Infinity. For example,
all-correct-negative F1 is undefined; F1 with false negatives and no positives
predicted is zero. No rounding occurs in stored metrics. Rates use `[0,1]`;
ASR differences use signed **percentage points**, A minus B.

Each evaluator has prediction/reference coverage, confusion metrics, ASR, and
paired human-reference ASR distortion. Overall human-reference ASR uses only
resolved labels. `common_cohort` recalculates evaluator metrics on the cases
where **all** evaluators made determinate predictions. Human-reference paired
counts still exclude unresolved labels. Pairwise comparisons use the intersection
for that pair, never subtraction of marginal ASRs on different denominators.

ASR also includes all-case lower/upper identification bounds: positive/expected
and (positive+unresolved)/expected. These expose missing-outcome uncertainty;
they are **not statistical confidence intervals** and do not impute a label.

`errors.json` lists false positives, false negatives, missing predictions,
indeterminate/error outcomes, unresolved/missing reference rows, and pairwise
disagreements by case ID. It does not infer a scientific error taxonomy.

## Conditions, rankings, and future ablations

Metrics and evaluator comparisons are also grouped by model, attack method,
and model/attack pair. Rankings require at least two conditions and the same
task/attempt/other-condition grid for every condition, with determinate outputs
from every evaluator for every case. Otherwise ranks are unavailable with a
reason. ASR ties receive competition ranks (1,1,3), with stable ID display order.
Rank changes are descriptive, not evidence of significance or superiority.

Ablation study/variant/component metadata survives into each run and web record.
No result is pooled across variants, runs, models, splits, or constructs.
Cross-run ablation deltas, paired/cluster bootstrap intervals, calibration,
inference tests, cost/latency analysis, cross-run rank correlations, and automatic
study-completion decisions remain future work. The per-case inputs and grouping
keys are retained so those analyses can be added reproducibly.

## Website data contract

`python scripts/experiment.py rebuild-web` writes deterministic, strict JSON to
`apps/web/data/results.json`. It exports versioned aggregate records with
experiment/run IDs, split, model/attack/validator versions, protocol identity,
dataset hash, human-reference version, ablation metadata, metrics, error counts,
and relative run-artifact paths/hashes. It excludes configs, individual labels,
reviewer IDs, case lists and evidence references. There is no generated timestamp
that would make unchanged builds differ.

Synthetic runs are excluded by default. `--include-synthetic` is for explicit
test/demo export and retains `record_kind: "synthetic"` and separate counts.
Research run count means imported research records, not completed experiments.
The builder does not infer experiment completion or make novelty claims.

The UI consumer can fetch this JSON and render values with their denominators,
constructs and split labels. It must render `null` as unavailable and preserve
synthetic labels. This PR supplies data only; it does not change or deploy the
website UI. The canonical source of every displayed metric remains the run bundle.

## Review gate

Per `AGENTS.md` rule 9, the PR needs explicit review of the positive-label
definition, resolved-reference rule, zero-denominator behavior, ASR denominator,
FX handling and development/test protections before merge. This implementation
does not itself approve the research protocol or a functional-execution harness.
