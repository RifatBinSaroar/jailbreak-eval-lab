# Canonical research registries v1

## Scope and baseline

This is metadata infrastructure only. It neither runs jailbreak experiments nor
generates, downloads or executes payloads. It does not establish novelty or any
empirical result. Production registries initially contain empty arrays.

Guidance was read at main commit `9f673eadaa2b2364aa08f4cb4d2462e566ac7f80`.
The requested `research/CONTROL_ROOM_SYNTHESIS_2026-09-08.md` was absent on main
and was read at `108e3cb9d74d844c909f74f227a7d1ba40a7c3a9` on `web-v0.1-static`.
Its provisional distinctions inform these contracts; no quantitative handoff
claims have been promoted into verified literature or experimental records.
Research decisions and success definitions retain their existing review process.

## Files and identities

Each `registries/<name>.json` is an ordinary JSON envelope:

```json
{"schema_version": "1.0.0", "registry": "papers", "records": []}
```

| Registry | ID prefix | Purpose-specific information |
| --- | --- | --- |
| papers | `paper:` | Citations, review status, evidence, interpretation, questions, manual novelty review |
| benchmarks | `benchmark:` | Version, taxonomy, paper links, source/licence/retrieval/transformation provenance, manifest |
| domains | `domain:`, `subdomain:` | Definition, inclusion/exclusion criteria, status, explicit domain parent for subdomains |
| validators | `validator:` | Version, success/output definitions, evaluation type, execution flag, rubric, implementation, judge model/prompt |
| datasets | `dataset:` | Version, benchmark pin, source provenance, manifest checksum, case/group IDs and splits |
| experiments | `experiment:` | Config ID/version/parameters, dataset/validator pins, model/version, attack/version/config, code commit, timestamp, split, seed, protocol, ground-truth rubric/version |
| runs | `run:` | Experiment reference/hash, full input-definition hash, lifecycle timestamps, environment, audit artefacts, exclusions |
| human_labels | `label:` | Run, dataset version, case/split, input checksum, pseudonymous annotator ID, rubric/version, assessment/evidence, adjudication/correction links |
| results | `result:` | Prediction or aggregate, run, validator version, input or source results, human labels, analysis code/config, evidence artefacts, metrics/exclusions |

Every record has `id`, `record_kind`, `version`, `timestamp` and `notes`. Use
lower-case namespaced IDs such as `dataset:response-set-v1` or a prefixed UUID.
Never derive IDs from array position or mutable titles. Nested identifiable
entities (sources, claims, questions, configs, models, attack methods, rubrics,
metrics, artefacts and cases) also have stable IDs. Value objects such as
assessments, pins and uncertainty intervals belong to their owning record.

Research records are **append-only after commit**. A correction or changed version
gets a new stable ID and version. Never reuse the old ID, delete its definition
or rewrite a record used by a run. Label corrections also use `supersedes_id`.
A lifecycle state is an immutable snapshot: append a new experiment/run snapshot
ID when freezing or finalising, and reference the final run snapshot when
importing results. This is a manifest store, not an in-place job-state database.
Failed/cancelled attempts remain recorded.

Dataset and validator pins repeat `version` to catch drift. Same-ID embedded
definitions must be identical. `validate_history()` and the CI history gate
reject modifications/deletions of committed research records. Retirement and
supersession discovery in the website is a future extension; the full registries
retain historical records.

## Evidence and novelty

`paper_demonstrates` contains claims with stable IDs, source IDs, exact
section/table/page locators and verification states. Use `topic` to capture the
evidence-rule fields: research problem, benchmark, success definition, judge,
labels/scores, evaluation type, execution, human ground truth, metrics, false
positives/negatives and author limitations. Preserve exact quantities as
source-backed claim text with population/denominator context. No automatic
rounding or conversion of notes into verified claims occurs.

`our_interpretation` is separate text with explicit evidence IDs where available.
`open_questions` stores unresolved questions. A listed paper may lack extracted
evidence; a verified paper requires verified claims with traceable citations.
Unverified claims remain marked unverified and are excluded from the website's
verified-evidence projection.

Novelty is manually entered as `unassessed`, `under_review` or
`prior_work_overlap`. The basis is always `manual_evidence_review`; overlap
requires cited evidence and a rationale. There is no automatic novel/first/gap
state or inference from missing papers, search counts or an empty registry.
Software cannot prove prose or citations truthful: primary-source review under
`EVIDENCE_RULES.md` remains necessary.

The legacy `literature/paper_schema.json` points to the canonical definition.
There were no old paper records on the baseline. Future imports must map
`paper_id` to a stable `id`, capture citations as `sources`, and split old
free-text claims into sourced evidence and interpretation. Do not silently map
old `novelty_threat: LOW` to a novelty finding. Preserve original workbook notes
in the source artefact and promote only reviewed fields explicitly.

## Reproducibility and lifecycle

One experiment is one dataset version, target model version, attack-method
version and split, evaluated by one or more pinned validators. Use additional
records for other combinations. `config.parameters` is the only unconstrained
configuration map. Do not put API keys, raw prompts or payloads in public records.
Seeds may be null when not applicable, with an explanation in the protocol.
Model/attack versions must identify the actual version used, not a floating
alias such as `latest`; this code cannot resolve remote provider versions.

Before execution is separately authorised, freeze dataset manifests and case
groups, implemented validators, protocol and ground-truth rubric. A group (such
as an original prompt and variants) cannot span splits within a dataset version.
Frozen experiments need a nonempty selected split. This checks declared group
leakage, not hidden duplicates or actual tuning on test data.

Use `canonical_sha256(experiment)` for `run.experiment_sha256` and
`run_inputs_sha256(experiment, records)` for `run.inputs_sha256`. The latter pins
the full experiment, dataset, selected validator definitions and benchmark. It
detects changed definitions even if an ID/version was accidentally reused.
The byte encoding is Python `json.dumps(sort_keys=True, separators=(",", ":"),
ensure_ascii=False, allow_nan=False).encode("utf-8")`, not RFC 8785. Generate these
hashes with Python; JavaScript consumers read them without recomputing using a
different number/string encoding. Exports omit a changing build timestamp.

Artefacts are `{id, uri, sha256, media_type, description}`. SHA-256 identifies
exact bytes; a file path alone is insufficient. Manifests may point to local or
access-controlled storage without committing raw data. `input_artifact` identifies
the exact prompt/response envelope assessed; annotations and predictions must
agree on it. Labels record rubric versions and evidence; adjudication requires
at least two distinct annotators' matching records. Annotator IDs are
pseudonymous, never names or email addresses.

Started runs need timezone-aware timestamps and environment/audit artefacts.
Completed runs account for every selected case/validator through an observed
prediction or explicit case exclusion. Unknown outcomes need not be fabricated
as measured successes or failures.

## Outcomes and aggregation

`predicted_success`, `score`, `confidence`, `functional_stage` and all R/H/F/Q/E
dimensions are nullable. Null means unobserved/unknown, never false or zero.
F0–F5 and FX preserve the synthesis ladder as optional metadata. They do not
select an endpoint or automatically derive success. R/H/F/Q/E fields are
**rubric-defined binary judgements** represented by bool/null, not a universal
measurement scale. Graded quality can use `score` with an explicit definition.
Definitions, thresholds and score interpretation require review before a
validator is marked implemented.

Planned labels/results have null observations. FX cannot have binary
success/failure or a numeric score. `indeterminate`/`error` predictions require a
reason and null decisions. The existing runtime dataclasses are unchanged;
there is no automatic conversion of their boolean outputs into registry results.

Aggregates list included/excluded prediction IDs and human-label IDs, with
run/validator/input consistency checks. Each aggregate covers one run and
validator; cross-experiment ranking/ASR-distortion analysis is a future extension.
Metrics record a definition (endpoint and inclusion policy), value, unit,
denominator and optional uncertainty method/level/bounds. Confusion-matrix cells
or distinct ASR endpoints may be separate entries with IDs and definitions.
This infrastructure computes no metrics.

Uncomputed/undefined values are null with reasons. Computed metrics need observed
predictions, a positive denominator no larger than the included case count, and
analysis artefacts. Configs/definitions must explain FX treatment, missing labels,
exclusions, denominator choice and ground-truth requirements. Validation cannot
certify custom formulas or statistical methods; those remain review tasks.

## Python, verification and website use

```python
from jailbreak_eval.registry import load_registries, verify_local_artifacts, web_bundle

records = load_registries("registries")
paper_by_id = {paper["id"]: paper for paper in records["papers"]}
verify_local_artifacts(records, ".")
dashboard = web_bundle("registries")
```

The loader uses the packaged [JSON Schema 2020-12](https://json-schema.org/draft/2020-12/json-schema-core)
and [python-jsonschema validation](https://python-jsonschema.readthedocs.io/en/stable/validate/).
All schema references are internal and validation is offline. Missing files,
unknown fields, duplicate keys/IDs, non-finite values, invalid timestamps,
dangling references and version drift fail closed. The CLI exits nonzero.

```bash
python -m jailbreak_eval.registry validate --artifact-root .
python -m jailbreak_eval.registry validate --previous-directory /path/to/previous/registries
python -m jailbreak_eval.registry export-web --output apps/web/dist/research-data.json
```

Normal validation checks provenance structure, references and metadata hashes;
it does not download artefacts or verify their contents. `--artifact-root`
verifies **every** referenced artefact against local bytes, rejecting missing
files, hash mismatches, absolute paths, escaping symlinks and remote URIs.
Materialize authorised private artefacts locally before this check. No downloader
or execution is supplied. Source truth, licensing and actual commit existence
need independent review.

The website export includes actual inventory/status counts, bibliographic
metadata, verified evidence with citations, interpretations supported by that
evidence, open questions and separately labelled manual novelty status. Only
computed aggregate metrics from completed runs are exported, with traceable IDs,
analysis commit and artefact hashes. Resolve these against the snapshot identified
by `registry_sha256`. Raw inputs, label records, arbitrary configs and artefact
storage locations are not copied to the projection.

Review public-facing text and confirm artefact availability/checksums before
publication; schema validation is not a licensing or safety approval. Production
export has no template override. Empty input produces zero recorded completed
experiments and `metrics: []`, never invented performance values. No UI or
deployment changes are included.

## Validation and review gates

CI installs the package, validates research and template registries separately,
checks append-only history against the PR base, runs benign metadata unit tests
and builds website JSON. Tests never invoke runners, models or validators.
Temporary synthetic records exercise rejection paths and are never published as
research data.

Review the nullable assessment representation, FX handling, annotation/adjudication
references and split constraints under AGENTS.md rule 9. No existing label,
score, success definition or ground truth is changed by this registry PR.
