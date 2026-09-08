"""Offline registry validation and JSON export. Never invokes a model or validator."""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
from importlib.resources import files
import json
from pathlib import Path
import re
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

REGISTRIES = (
    "papers", "benchmarks", "domains", "validators", "datasets",
    "experiments", "runs", "human_labels", "results",
)
SCHEMA_VERSION = "1.0.0"


class RegistryError(ValueError):
    """A structural, reference, or provenance constraint was violated."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RegistryError(message)


def _unique_keys(pairs: list[tuple[str, Any]]) -> dict:
    result = {}
    for key, value in pairs:
        require(key not in result, f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _nonfinite(value: str) -> None:
    raise RegistryError(f"non-finite JSON number: {value}")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_keys,
                      parse_constant=_nonfinite)


def canonical_sha256(value: Any) -> str:
    """Hash the documented Python canonical JSON encoding (not RFC 8785)."""
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False, allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load_schema() -> dict:
    resource = files("jailbreak_eval").joinpath("schemas/registry.schema.json")
    return json.loads(resource.read_text(encoding="utf-8"))


def run_inputs_sha256(experiment: dict, records: dict) -> str:
    """Pin the full definitions behind an experiment, including the benchmark."""
    dataset = pinned(records["datasets"], experiment["dataset"])
    benchmark = pinned(records["benchmarks"], dataset["benchmark"]) if dataset["benchmark"] is not None else None
    return canonical_sha256({"experiment": experiment, "dataset": dataset,
                             "validators": [pinned(records["validators"], v) for v in experiment["validators"]],
                             "benchmark": benchmark})


def pinned(rows, reference):
    matches = [r for r in rows if r["id"] == reference["id"] and r["version"] == reference["version"]]
    require(len(matches) == 1, f"version mismatch or missing pin: {reference}")
    return matches[0]


def latest_records(records):
    """Select the latest timestamp per stable object; history stays in registries."""
    result = {}
    for name, rows in records.items():
        latest = {}
        for row in rows:
            if row["id"] not in latest or _time(row["timestamp"]) > _time(latest[row["id"]]["timestamp"]):
                latest[row["id"]] = row
        result[name] = sorted(latest.values(), key=lambda r: r["id"])
    return result


def experiment_for_run(run, records):
    matches = [e for e in records["experiments"] if e["id"] == run["experiment_id"]
               and canonical_sha256(e) == run["experiment_sha256"]]
    require(len(matches) == 1, f"{run['id']}: experiment snapshot hash mismatch")
    return matches[0]


def validate_history(current: dict, previous: dict) -> None:
    """Keep committed canonical values unchanged. Append a new version, SAME ID."""
    for name in REGISTRIES:
        latest = {(row["id"], row["version"]): row for row in current[name]}
        for row in previous[name]:
            require(latest.get((row["id"], row["version"])) == row,
                    f"{row['id']}: published revisions are immutable; append a new version under the same ID")
        previous_latest = latest_records(previous)[name]
        for row in current[name]:
            if not any(r["id"] == row["id"] and r["version"] == row["version"] for r in previous[name]):
                old = next((r for r in previous_latest if r["id"] == row["id"]), None)
                require(old is None or _time(row["timestamp"]) > _time(old["timestamp"]),
                        f"{row['id']}: new revision needs a later timestamp")
                if old is not None and name == "papers" and row["evidence_status"] != "listed":
                    scientific = set(row) - {"version", "timestamp", "intake_artifacts", "review"}
                    if any(row[k] != old[k] for k in scientific):
                        require(row["review"] is not None and row["review"] != old["review"],
                                f"{row['id']}: scientific paper update needs fresh review provenance")
                        require(old["review"] is None or _time(row["review"]["reviewed_at"]) > _time(old["review"]["reviewed_at"]),
                                f"{row['id']}: scientific paper update needs a later review date")


def _walk(value: Any):
    if isinstance(value, dict):
        yield value
        for key, child in value.items():
            # Config parameters are opaque values, not registry definitions.
            if key != "parameters":
                yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00").replace("z", "+00:00"))


def _format_checker() -> FormatChecker:
    checker = FormatChecker()

    # Enforce timezone-aware RFC 3339 timestamps without optional format packages.
    @checker.checks("date-time", raises=ValueError)
    def timestamp(value):
        if not isinstance(value, str):
            return True
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}[Tt]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[Zz]|[+-]\d{2}:\d{2})", value):
            return False
        return _time(value).tzinfo is not None

    return checker


def load_registries(directory: str | Path = "registries", *, allow_templates=False) -> dict:
    """Load all nine named files; missing files fail instead of becoming empty data."""
    root = Path(directory)
    envelopes = {name: read_json(root / f"{name}.json") for name in REGISTRIES}
    return validate_registries(envelopes, allow_templates=allow_templates)


def validate_registries(envelopes: dict, *, allow_templates=False) -> dict:
    """Return arrays of validated records. Does not mutate input or fetch artefacts."""
    require(set(envelopes) == set(REGISTRIES), "all nine registries are required")
    schema = load_schema()
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=_format_checker())
    records = {}
    for name in REGISTRIES:
        envelope = envelopes[name]
        errors = sorted(validator.iter_errors(envelope), key=lambda e: str(list(e.path)))
        if errors:
            error = errors[0]
            location = "/".join(str(part) for part in error.path)
            raise RegistryError(f"{name}/{location}: {error.message}")
        require(envelope["registry"] == name, f"{name}: envelope registry name mismatch")
        # Also rejects float infinity introduced by JSON exponents or Python callers.
        try:
            canonical_sha256(envelope)
        except ValueError as exc:
            raise RegistryError(f"{name}: non-finite JSON number") from exc
        records[name] = envelope["records"]

    index, versions, timestamps = {}, {}, set()
    for name, rows in records.items():
        for row in rows:
            rid = row["id"]
            if name in {"benchmarks", "datasets"} and row["provenance"]["redistribution"] == "permitted":
                require(row["provenance"]["license"] is not None, f"{rid}: permitted redistribution needs license evidence")
            revision = (rid, row["version"])
            require(revision not in versions, f"duplicate stable ID/version: {rid}")
            require((rid, _time(row["timestamp"])) not in timestamps, f"{rid}: revisions need distinct timestamps")
            timestamps.add((rid, _time(row["timestamp"])))
            versions[revision] = (name, row)
            if rid not in index or _time(row["timestamp"]) > _time(index[rid][1]["timestamp"]):
                index[rid] = (name, row)
            template = row["record_kind"] == "template"
            require(allow_templates or not template, f"{rid}: templates forbidden in production")
            require(template == rid.split(":", 1)[1].startswith("template-"),
                    f"{rid}: template IDs must use the template- namespace exclusively")
    kinds = {row["record_kind"] for _, row in index.values()}
    require("template" not in kinds or kinds == {"template"}, "research and template records must be in separate registry sets")
    for rid in index:
        require(len({r["record_kind"] for (i, _), (_, r) in versions.items() if i == rid}) == 1,
                f"{rid}: record kind cannot change between versions")

    def get(rid, name, owner):
        require(rid in index, f"{owner}: dangling reference {rid}")
        category, row = index[rid]
        require(category == name, f"{owner}: {rid} must reference {name}")
        require(owner not in index or index[owner][1]["record_kind"] == row["record_kind"],
                f"{owner}: research/template/synthetic references must remain separate")
        return row

    def pin(value, name, owner):
        entry = versions.get((value["id"], value["version"]))
        require(entry is not None and entry[0] == name, f"{owner}: version mismatch for {value['id']}")
        row = entry[1]
        require(owner not in index or index[owner][1]["record_kind"] == row["record_kind"],
                f"{owner}: research/template/synthetic references must remain separate")
        return row

    # Reused nested definitions (model, config, rubric, source, artefact) have stable
    # IDs too. A reference is only an id/version pair; definitions must agree.
    definitions = {}
    for name, rows in records.items():
        for row in rows:
            for value in _walk(row):
                if value is not row and "id" in value and ("sha256" in value or "version" in value and len(value) > 2):
                    rid = (value["id"], value.get("version"))
                    require(rid not in definitions or definitions[rid] == value,
                            f"{rid}: conflicting definitions for a stable ID")
                    definitions[rid] = value

    for name, rows in records.items():
        for row in rows:
            rid = row["id"]
            for field, target in (("paper_ids", "papers"), ("benchmark_ids", "benchmarks"),
                                  ("domain_ids", "domains"), ("validator_ids", "validators")):
                for reference in row.get(field, []):
                    get(reference, target, rid)
            if name == "papers":
                _validate_paper(row)
            elif name == "domains" and row["parent_id"] is not None:
                parent = get(row["parent_id"], "domains", rid)
                require(parent["level"] == "domain", f"{rid}: parent must be a domain")
            elif name == "validators":
                if row["status"] == "implemented":
                    require(all(row[k] is not None for k in ("code_commit", "implementation", "executes_code")),
                            f"{rid}: implemented validator needs code and execution provenance")
                    require(row["rubric"]["artifact"] is not None, f"{rid}: implemented validator needs rubric")
                    require(row["success_definition"] is not None and row["output_definition"] is not None,
                            f"{rid}: implemented validator needs explicit success/output definitions")
                if row["judge_model"] is not None:
                    require(row["judge_prompt"] is not None, f"{rid}: judge model needs versioned prompt artefact")
                if row["status"] == "external_recorded":
                    require(row.get("capture_artifact") is not None, f"{rid}: external decisions need captured definition provenance")
            elif name == "datasets":
                if row["benchmark"] is not None:
                    pin(row["benchmark"], "benchmarks", rid)
                case_ids, groups = set(), {}
                for case in row["cases"]:
                    require(case["id"] not in case_ids, f"{rid}: duplicate case ID {case['id']}")
                    case_ids.add(case["id"])
                    group, split = case["group_id"], case["split"]
                    require(group not in groups or groups[group] == split, f"{rid}: split leakage in {group}")
                    groups[group] = split
                if row["status"] == "frozen":
                    require(row["manifest"] is not None and bool(row["cases"]),
                            f"{rid}: frozen dataset needs manifest and cases")
                    require(row["provenance"]["upstream_version"] is not None
                            and row["provenance"]["retrieved_at"] is not None,
                            f"{rid}: frozen dataset needs source version and retrieval date")
            elif name == "experiments":
                dataset = pin(row["dataset"], "datasets", rid)
                selected = [pin(v, "validators", rid) for v in row["validators"]]
                if row["status"] == "frozen":
                    require(dataset["status"] == "frozen", f"{rid}: experiment needs frozen dataset")
                    require(all(v["status"] in {"implemented", "external_recorded"} for v in selected),
                            f"{rid}: experiment needs implemented validators")
                    require(row["protocol"] is not None and row["human_ground_truth"]["artifact"] is not None,
                            f"{rid}: experiment needs protocol and ground-truth rubric")
                    require(any(c["split"] == row["split"] for c in dataset["cases"]),
                            f"{rid}: requested split is empty")
                if row.get("purpose") is not None:
                    require(row["purpose"] == {"development": "development", "pilot": "pilot", "test": "final_evaluation"}.get(row["split"]),
                            f"{rid}: purpose/split mismatch")
                    if row["split"] == "test":
                        require(row.get("protocol_freeze") is not None and _time(row["protocol_freeze"]) <= _time(row["timestamp"]),
                                f"{rid}: final test requires a frozen protocol")
                if row["status"] == "frozen" and row["split"] == "test":
                    require(row.get("purpose") == "final_evaluation" and row.get("protocol_freeze") is not None,
                            f"{rid}: frozen final-test definitions need purpose and protocol freeze")

    protocol_versions, final_bindings = {}, {}
    for exp in records["experiments"]:
        captured = exp["config"]["parameters"].get("capture_protocol")
        if captured is None:
            continue
        protocol_key = (exp["record_kind"], captured["protocol_id"], captured["version"])
        require(protocol_versions.setdefault(protocol_key, captured) == captured,
                f"{exp['id']}: protocol changed without a new protocol version")
        if exp["split"] == "test":
            binding_key = (*protocol_key, exp["dataset"]["id"], exp["dataset"]["version"])
            binding = {k: exp[k] for k in ("validators", "models", "attack_methods", "code_commit", "seed", "human_ground_truth", "ablation")}
            binding["config"] = exp["config"]["parameters"].get("capture_config")
            require(final_bindings.setdefault(binding_key, binding) == binding,
                    f"{exp['id']}: final-test configuration changed under the same frozen protocol; version the protocol explicitly")

    # Split membership is permanent across revisions and dataset aliases. Shared
    # response hashes and grouping IDs prevent relabelling pilot/development as test.
    memberships = {}
    for dataset in records["datasets"]:
        for case in dataset["cases"]:
            for field in ("id", "group_id", "task_id", "base_intent_id", "prompt_family_id", "duplicate_group_id", "response_sha256"):
                if case.get(field):
                    key = (dataset["record_kind"], field, case[field])
                    require(memberships.setdefault(key, case["split"]) == case["split"],
                            f"{dataset['id']}: cross-version split leakage through {field}")

    for run in records["runs"]:
        rid = run["id"]
        experiment = experiment_for_run(run, records)
        require(run["experiment_sha256"] == canonical_sha256(experiment),
                f"{rid}: experiment snapshot hash mismatch")
        require(run["inputs_sha256"] == run_inputs_sha256(experiment, records),
                f"{rid}: run input definitions hash mismatch")
        require(_time(run["timestamp"]) >= _time(experiment["timestamp"]), f"{rid}: run predates experiment")
        if run["status"] == "planned":
            require(run["started_at"] is None and run["finished_at"] is None and not run["artifacts"],
                    f"{rid}: planned run cannot have execution timestamps or outputs")
        else:
            require(experiment["status"] == "frozen", f"{rid}: started run requires frozen experiment")
            require(run["started_at"] is not None and (run["environment"] is not None or run.get("recording_only") is True),
                    f"{rid}: started run needs timestamp and environment")
            require(_time(run["started_at"]) >= _time(run["timestamp"]), f"{rid}: start precedes record")
            terminal = run["status"] in {"completed", "failed", "cancelled"}
            require((run["finished_at"] is not None) == terminal, f"{rid}: inconsistent finish timestamp")
            if terminal:
                require(_time(run["finished_at"]) >= _time(run["started_at"]), f"{rid}: finish precedes start")
                require(bool(run["artifacts"]), f"{rid}: finished run needs audit artefacts")
        dataset = pin(experiment["dataset"], "datasets", rid)
        case_ids = {c["id"] for c in dataset["cases"] if c["split"] == experiment["split"]}
        excluded = [e["case_id"] for e in run["exclusions"]]
        require(len(set(excluded)) == len(excluded) and set(excluded) <= case_ids,
                f"{rid}: exclusions must uniquely reference cases in the run split")

    case_inputs = {}

    def context(row):
        rid = row["id"]
        run = get(row["run_id"], "runs", rid)
        exp = experiment_for_run(run, records)
        dataset = pin(exp["dataset"], "datasets", rid)
        if row.get("case_id") is not None:
            cases = {case["id"]: case for case in dataset["cases"]}
            require(row["case_id"] in cases, f"{rid}: unknown case in dataset")
            require(cases[row["case_id"]]["split"] == exp["split"], f"{rid}: case split mismatch")
            if row.get("input_artifact") is not None:
                key = (row["run_id"], row["case_id"])
                require(key not in case_inputs or case_inputs[key] == row["input_artifact"],
                        f"{rid}: inconsistent input for the same run/case")
                case_inputs[key] = row["input_artifact"]
        require(_time(row["timestamp"]) >= _time(run["timestamp"]), f"{rid}: record predates run")
        return run, exp

    for label in records["human_labels"]:
        rid = label["id"]
        run, exp = context(label)
        require(label["dataset"] == exp["dataset"] and label["split"] == exp["split"],
                f"{rid}: label dataset/split differs from experiment")
        require(label["rubric"] == exp["human_ground_truth"], f"{rid}: ground-truth rubric mismatch")
        _validate_assessment(label["assessment"], label["status"] in {"pending", "unresolved"}, rid)
        if label["status"] != "pending":
            require(run["status"] != "planned" and label["input_artifact"] is not None and bool(label["evidence"]),
                    f"{rid}: annotation needs observed input and evidence")
            require(label["rubric"]["artifact"] is not None, f"{rid}: annotation needs rubric artefact")
            require(_time(label["timestamp"]) >= _time(run["started_at"]), f"{rid}: annotation predates start")
        reviewed = [get(x, "human_labels", rid) for x in label["reviewed_label_ids"]]
        imported_review = label.get("reference_review")
        if imported_review is not None:
            require(not reviewed, f"{rid}: imported reference must not invent individual annotations")
            resolved = label["status"] in {"consensus", "adjudicated"}
            require(not resolved or len(imported_review["annotator_ids"]) >= 2, f"{rid}: resolved reference needs two annotators")
            require((imported_review["adjudicator_id"] is not None) == (label["status"] == "adjudicated"), f"{rid}: adjudicator mismatch")
            require(not resolved or label["assessment"]["predicted_success"] is not None, f"{rid}: resolved reference needs a label")
        require(imported_review is not None or (len(reviewed) >= 2) == (label["status"] == "adjudicated"),
                f"{rid}: adjudication requires at least two independent annotations")
        require(label["status"] == "adjudicated" or not reviewed, f"{rid}: only adjudications review labels")
        require(len({x["annotator_id"] for x in reviewed}) == len(reviewed), f"{rid}: annotators must be independent")
        for previous in reviewed:
            require(previous["status"] == "annotated", f"{rid}: adjudication must reference annotations")
            _same_label_context(label, previous)
        if label["supersedes_id"] is not None:
            previous = get(label["supersedes_id"], "human_labels", rid)
            require(previous["id"] != rid and _time(previous["timestamp"]) < _time(label["timestamp"]),
                    f"{rid}: supersession must point strictly backwards in time")
            _same_label_context(label, previous)

    prediction_keys = set()
    for result in records["results"]:
        rid = result["id"]
        run, exp = context(result)
        pin(result["validator"], "validators", rid)
        require(result["validator"] in exp["validators"], f"{rid}: validator is not in experiment")
        if result["status"] != "not_measured":
            require(run["status"] != "planned" and bool(result["provenance"]["artifacts"]),
                    f"{rid}: observed result needs run and output artefacts")
            require(_time(result["timestamp"]) >= _time(run["started_at"]), f"{rid}: result predates start")
        labels = [get(x, "human_labels", rid) for x in result["human_label_ids"]]
        for label in labels:
            require(label["run_id"] == result["run_id"], f"{rid}: label belongs to another run")
            if result["status"] != "not_measured":
                require(label["status"] != "pending", f"{rid}: cannot use pending human labels")
        if result["kind"] == "prediction":
            key = (result["run_id"], result["validator"]["id"], result["case_id"])
            require(key not in prediction_keys, f"{rid}: duplicate prediction for run/validator/case")
            prediction_keys.add(key)
            _validate_assessment(result["assessment"], result["status"] == "not_measured", rid)
            if result["status"] != "not_measured":
                require(result["input_artifact"] is not None, f"{rid}: prediction needs exact input artefact")
            if result["status"] in {"indeterminate", "error", "missing"}:
                require(result["assessment"]["predicted_success"] is None
                        and result["assessment"]["score"] is None
                        and result["assessment"]["reason"] is not None,
                        f"{rid}: indeterminate/error cannot become a success/failure or score")
            if result["status"] == "measured":
                require(result["assessment"]["predicted_success"] is not None
                        or result["assessment"]["score"] is not None,
                        f"{rid}: measured prediction needs a decision or score")
            for label in labels:
                require(label["case_id"] == result["case_id"] and label["input_artifact"] == result["input_artifact"],
                        f"{rid}: label input differs from prediction")
        else:
            included = [get(x, "results", rid) for x in result["source_result_ids"]]
            excluded = [get(x, "results", rid) for x in result["excluded_result_ids"]]
            require(not set(result["source_result_ids"]) & set(result["excluded_result_ids"]),
                    f"{rid}: result cannot be both included and excluded")
            cases = set()
            for source in included + excluded:
                require(source["kind"] == "prediction" and source["run_id"] == result["run_id"]
                        and source["validator"] == result["validator"], f"{rid}: aggregate mixes run/validator or aggregate inputs")
                require(source["case_id"] not in cases, f"{rid}: duplicate case in aggregate inputs")
                cases.add(source["case_id"])
                if result["status"] != "not_measured":
                    require(source["status"] != "not_measured", f"{rid}: aggregate input was not observed")
                require(_time(source["timestamp"]) <= _time(result["timestamp"]), f"{rid}: aggregate predates inputs")
            for label in labels:
                require(any(s["case_id"] == label["case_id"] and s["input_artifact"] == label["input_artifact"]
                            for s in included), f"{rid}: aggregate label has no matching included input")
            for metric in result["metrics"]:
                if metric["status"] == "computed":
                    require(result["status"] == "measured" and bool(included), f"{rid}: computed metric needs observed inputs")
                    if metric.get("denominator_basis", "cases") == "cases":
                        require(metric["denominator"] <= len(included), f"{rid}: denominator exceeds included cases")
                    else:
                        require(metric.get("cohort_size") is not None and metric["cohort_size"] <= len(included),
                                f"{rid}: formula metric needs its included cohort size")
                else:
                    require(metric["reason"] is not None, f"{rid}: unavailable metric needs a reason")
                interval = metric["uncertainty"]
                if interval is not None:
                    require(interval["lower"] <= interval["upper"], f"{rid}: reversed uncertainty interval")
            if result["status"] == "not_measured":
                require(all(m["status"] == "not_computed" for m in result["metrics"]),
                        f"{rid}: unmeasured aggregate cannot contain observations")

    for run in records["runs"]:
        if run["status"] == "completed":
            exp = experiment_for_run(run, records)
            dataset = pin(exp["dataset"], "datasets", run["id"])
            excluded = {e["case_id"] for e in run["exclusions"]}
            cases = {c["id"] for c in dataset["cases"] if c["split"] == exp["split"]} - excluded
            observed = {(r["validator"]["id"], r["case_id"]) for r in records["results"]
                        if r["run_id"] == run["id"] and r["kind"] == "prediction" and r["status"] != "not_measured"}
            require(all((v["id"], case) in observed for v in exp["validators"] for case in cases),
                    f"{run['id']}: completed run has unaccounted cases/validators")

    if kinds == {"template"}:
        _validate_templates(records)
    return records


def _validate_paper(row):
    rid = row["id"]
    sources = {s["id"] for s in row["sources"]}
    evidence = {e["id"] for e in row["paper_demonstrates"]}
    if row["evidence_status"] != "listed":
        require(bool(sources), f"{rid}: reviewed paper needs primary source metadata")
        require(row["review"] is not None, f"{rid}: reviewed paper needs review provenance")
        require(_time(row["review"]["reviewed_at"]) <= _time(row["timestamp"]), f"{rid}: review postdates revision")
        require(any(s["url"] is not None for s in row["sources"]), f"{rid}: reviewed paper needs a primary paper URL")
    else:
        require(not row["paper_demonstrates"], f"{rid}: listed intake cannot contain paper evidence")
    if row["evidence_status"] in {"deep-reviewed", "verified"}:
        require(bool(evidence), f"{rid}: deep review needs extracted evidence")
    for claim in row["paper_demonstrates"]:
        require(claim["source_id"] in sources, f"{rid}: paper evidence needs a traceable source")
        require(any(s["id"] == claim["source_id"] and s["url"] is not None and s.get("kind", "paper") == "paper" for s in row["sources"]),
                f"{rid}: paper evidence needs a primary source URL")
        if claim["verification_status"] == "verified":
            require(row["review"] is not None and claim["id"] in row["review"]["verified_evidence_ids"],
                    f"{rid}: verified evidence needs explicit review provenance")
    if row["review"] is not None:
        require(set(row["review"]["verified_evidence_ids"]) <= evidence, f"{rid}: stale evidence verification IDs")
    for interpretation in row["our_interpretation"]:
        require(set(interpretation["evidence_ids"]) <= evidence, f"{rid}: interpretation evidence not found")
    if row["evidence_status"] == "verified":
        require(bool(evidence) and all(e["verification_status"] == "verified" for e in row["paper_demonstrates"]),
                f"{rid}: verified paper needs verified source evidence")
    novelty = row["novelty"]
    require(set(novelty["evidence_ids"]) <= evidence, f"{rid}: novelty evidence not found")
    if novelty["status"] == "prior_work_overlap":
        require(bool(novelty["evidence_ids"]) and novelty["rationale"] is not None,
                f"{rid}: prior-work overlap needs explicit evidence review")
    # No state for 'novel because absent', and no state inferred from paper counts.


def _validate_assessment(assessment, pending, owner):
    if pending:
        require(all(assessment[k] is None for k in ("predicted_success", "functional_stage", "score", "confidence"))
                and all(v is None for v in assessment["dimensions"].values()),
                f"{owner}: pending/unmeasured assessment must remain null")
    if assessment["functional_stage"] == "FX":
        require(assessment["predicted_success"] is None and assessment["score"] is None,
                f"{owner}: FX cannot be converted to binary failure/success or score")


def _same_label_context(current, previous):
    require(all(current[k] == previous[k] for k in ("run_id", "dataset", "case_id", "split", "input_artifact", "rubric")),
            f"{current['id']}: annotation/adjudication context mismatch")
    require(_time(previous["timestamp"]) <= _time(current["timestamp"]),
            f"{current['id']}: adjudication predates annotation")


def _validate_templates(records):
    for row in records["runs"]:
        require(row["status"] == "planned", f"{row['id']}: template run must stay planned")
    for row in records["human_labels"]:
        require(row["status"] == "pending", f"{row['id']}: template label must stay pending")
    for row in records["results"]:
        require(row["status"] == "not_measured", f"{row['id']}: template result must stay unmeasured")


def verify_local_artifacts(records: dict, root: str | Path) -> int:
    """Verify every referenced artefact locally. Remote/private URIs fail, never fetch."""
    root = Path(root).resolve()
    seen = {}
    for obj in _walk(records):
        if {"id", "uri", "sha256", "media_type", "description"} <= obj.keys():
            if obj["id"] in seen:
                require(seen[obj["id"]] == obj, f"{obj['id']}: conflicting artefact definitions")
                continue
            seen[obj["id"]] = obj
            uri = obj["uri"]
            require(not re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", uri) and not Path(uri).is_absolute(),
                    f"{obj['id']}: local verification requires a relative file path")
            path = (root / uri).resolve()
            require(path.is_relative_to(root), f"{obj['id']}: artefact path escapes root")
            require(path.is_file(), f"{obj['id']}: missing artefact {uri}")
            with path.open("rb") as stream:
                digest = hashlib.sha256()
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
            require(digest.hexdigest() == obj["sha256"], f"{obj['id']}: artefact hash mismatch")
    return len(seen)


def web_bundle(directory: str | Path = "registries", *, artifact_root=None, include_synthetic=False) -> dict:
    """The ONE canonical web export. No models, no experiments, no guessed facts."""
    from .experiments.canonical import verify_registered_runs
    from .literature.core import duplicate_candidates, existing_intake
    all_records = load_registries(directory)
    root = Path(artifact_root) if artifact_root else Path(directory).resolve().parent
    existing_intake(all_records, root)
    verify_registered_runs(all_records, root)
    latest = latest_records(all_records)
    records = {name: [r for r in rows if include_synthetic or r["record_kind"] == "research"]
               for name, rows in latest.items()}
    # Export source-linked extraction at its ACTUAL review state, not only verified.
    claims = [{"paper_id": p["id"], "paper_version": p["version"], "review_state": p["evidence_status"],
               **claim, "source": next(s for s in p["sources"] if s["id"] == claim["source_id"])}
              for p in records["papers"] for claim in p["paper_demonstrates"]]
    metrics = [{**m, "result_id": r["id"], "run_id": r["run_id"], "validator": r["validator"],
                "record_kind": r["record_kind"], "code_commit": r["provenance"]["code_commit"],
                "artifacts": r["provenance"]["artifacts"]}
               for r in records["results"] if r["kind"] == "aggregate" for m in r["metrics"]]
    readiness = {**{name: len(rows) for name, rows in records.items()},
                 "papers_by_status": {s: sum(p["evidence_status"] == s for p in records["papers"])
                                       for s in ("listed", "screened", "deep-reviewed", "verified")},
                 "validators_implemented": sum(v["status"] == "implemented" for v in records["validators"]),
                 "experiments_completed": len({r["experiment_id"] for r in records["runs"] if r["status"] == "completed"}),
                 "measured_results": sum(r["kind"] == "aggregate" for r in records["results"])}
    # Plain canonical fields, with sensitive data deliberately redacted. Counts
    # and gap cards are projections, never independent research records.
    public = {name: rows for name, rows in records.items()}
    public["datasets"] = [{k:v for k,v in r.items() if k != "cases"} | {"case_count":len(r["cases"])} for r in records["datasets"]]
    public["experiments"] = [{k:v for k,v in r.items() if k != "config"} | {"config": {"id":r["config"]["id"],"version":r["config"]["version"]}}
                             for r in records["experiments"]]
    public["human_labels"] = []  # individual annotators/labels remain in local artifacts
    public["results"] = [{**r, "provenance": {**r["provenance"], "config": {k:r["provenance"]["config"][k] for k in ("id","version")}}}
                         for r in records["results"] if r["kind"] == "aggregate"]
    public["runs"] = [{**r, "experiment": {k:v for k,v in experiment_for_run(r,all_records).items() if k != "config"},
                       "validator_definitions": [pinned(all_records["validators"], v) for v in experiment_for_run(r,all_records)["validators"]]}
                      for r in records["runs"]]
    def redact(value):
        if isinstance(value, dict):
            return {k:redact(v) for k,v in value.items() if k != "parameters"}
        if isinstance(value, list):
            return [redact(v) for v in value]
        return value
    public = redact(public)
    # Native per-case data are private; the web consumes only reproduced aggregates.
    questions = [{"id":q["id"], "text":q["text"], "paper_id":p["id"], "category":"unresolved_question"}
                 for p in records["papers"] for q in p["open_questions"]]
    threats = [{"paper_id":p["id"], "title":p["title"], **p["novelty"]}
               for p in records["papers"] if p["novelty"]["status"] != "unassessed"]
    return {"contract":"research-platform/0.1", "schema_version":SCHEMA_VERSION,
            "registry_sha256":canonical_sha256(all_records), "include_synthetic":include_synthetic,
            "excluded_synthetic_run_ids":[r["id"] for r in latest["runs"] if r["record_kind"] == "synthetic" and not include_synthetic],
            "readiness":readiness, **public, "paper_evidence":claims,
            "verified_paper_evidence":[e for e in claims if e["verification_status"] == "verified"],
            "metrics":metrics, "duplicate_candidates":duplicate_candidates(records["papers"]),
            "open_questions":questions, "novelty_threats":threats,
            "novelty_note":"Novelty remains subject to manual evidence review. Missing literature never establishes a research gap."}


def write_web(directory="registries", output="apps/web/data/research.json", *, artifact_root=None, include_synthetic=False):
    from .experiments.runs import atomic_json
    root = Path(artifact_root) if artifact_root else Path(directory).resolve().parent
    destination = Path(output).resolve()
    require(not destination.is_relative_to(Path(directory).resolve()), "Web output cannot overwrite registries")
    for folder in ("results/runs", "literature/intake", "data/manifests"):
        require(not destination.is_relative_to((root / folder).resolve()), "Web output cannot overwrite immutable artifacts")
    bundle = web_bundle(directory, artifact_root=root, include_synthetic=include_synthetic)
    atomic_json(destination, bundle)
    return bundle


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("validate", help="validate metadata only; never execute experiments")
    check.add_argument("--directory", default="registries")
    check.add_argument("--allow-templates", action="store_true")
    check.add_argument("--artifact-root", type=Path)
    check.add_argument("--previous-directory", type=Path, help="preserve committed revisions while allowing new versions under stable IDs")
    export = sub.add_parser("export-web", help="export validated production readiness and traceable metrics")
    export.add_argument("--directory", default="registries")
    export.add_argument("--output", default="apps/web/data/research.json", type=Path)
    export.add_argument("--artifact-root", type=Path)
    export.add_argument("--include-synthetic", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command == "validate":
            records = load_registries(args.directory, allow_templates=args.allow_templates)
            if args.previous_directory:
                require(not args.allow_templates, "history checks apply to research registries")
                validate_history(records, load_registries(args.previous_directory))
            if args.artifact_root:
                count = verify_local_artifacts(records, args.artifact_root)
                print(f"Verified {count} local artefacts.")
            print(f"Validated {len(records)} registries, {sum(map(len, records.values()))} records. No experiments executed.")
        else:
            write_web(args.directory, args.output, artifact_root=args.artifact_root, include_synthetic=args.include_synthetic)
            print(f"Wrote {args.output}")
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Registry validation failed: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
