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
    datasets = {r["id"]: r for r in records["datasets"]}
    validators = {r["id"]: r for r in records["validators"]}
    benchmarks = {r["id"]: r for r in records["benchmarks"]}
    dataset = datasets[experiment["dataset"]["id"]]
    benchmark = benchmarks[dataset["benchmark"]["id"]] if dataset["benchmark"] is not None else None
    return canonical_sha256({"experiment": experiment, "dataset": dataset,
                             "validators": [validators[v["id"]] for v in experiment["validators"]],
                             "benchmark": benchmark})


def validate_history(current: dict, previous: dict) -> None:
    """Existing research IDs are append-only. Corrections use new IDs/versions."""
    for name in REGISTRIES:
        latest = {row["id"]: row for row in current[name]}
        for row in previous[name]:
            require(row["id"] in latest and latest[row["id"]] == row,
                    f"{row['id']}: published records are immutable; append a new ID/version")


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

    index = {}
    for name, rows in records.items():
        for row in rows:
            rid = row["id"]
            if name in {"benchmarks", "datasets"} and row["provenance"]["redistribution"] == "permitted":
                require(row["provenance"]["license"] is not None, f"{rid}: permitted redistribution needs license evidence")
            require(rid not in index, f"duplicate stable ID: {rid}")
            index[rid] = (name, row)
            template = row["record_kind"] == "template"
            require(allow_templates or not template, f"{rid}: templates forbidden in production")
            require(template == rid.split(":", 1)[1].startswith("template-"),
                    f"{rid}: template IDs must use the template- namespace exclusively")
    kinds = {row["record_kind"] for _, row in index.values()}
    require(len(kinds) <= 1, "research and template records must be in separate registry sets")

    def get(rid, name, owner):
        require(rid in index, f"{owner}: dangling reference {rid}")
        category, row = index[rid]
        require(category == name, f"{owner}: {rid} must reference {name}")
        return row

    def pin(value, name, owner):
        row = get(value["id"], name, owner)
        require(value["version"] == row["version"], f"{owner}: version mismatch for {value['id']}")
        return row

    # Reused nested definitions (model, config, rubric, source, artefact) have stable
    # IDs too. A reference is only an id/version pair; definitions must agree.
    definitions = {}
    for name, rows in records.items():
        for row in rows:
            for value in _walk(row):
                if "id" in value and set(value) - {"id", "version"}:
                    rid = value["id"]
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
                if row["judge_model"] is not None:
                    require(row["judge_prompt"] is not None, f"{rid}: judge model needs versioned prompt artefact")
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
                    require(all(v["status"] == "implemented" for v in selected),
                            f"{rid}: experiment needs implemented validators")
                    require(row["protocol"] is not None and row["human_ground_truth"]["artifact"] is not None,
                            f"{rid}: experiment needs protocol and ground-truth rubric")
                    require(any(c["split"] == row["split"] for c in dataset["cases"]),
                            f"{rid}: requested split is empty")

    for run in records["runs"]:
        rid = run["id"]
        experiment = get(run["experiment_id"], "experiments", rid)
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
            require(run["started_at"] is not None and run["environment"] is not None,
                    f"{rid}: started run needs timestamp and environment")
            require(_time(run["started_at"]) >= _time(run["timestamp"]), f"{rid}: start precedes record")
            terminal = run["status"] in {"completed", "failed", "cancelled"}
            require((run["finished_at"] is not None) == terminal, f"{rid}: inconsistent finish timestamp")
            if terminal:
                require(_time(run["finished_at"]) >= _time(run["started_at"]), f"{rid}: finish precedes start")
                require(bool(run["artifacts"]), f"{rid}: finished run needs audit artefacts")
        dataset = get(experiment["dataset"]["id"], "datasets", rid)
        case_ids = {c["id"] for c in dataset["cases"] if c["split"] == experiment["split"]}
        excluded = [e["case_id"] for e in run["exclusions"]]
        require(len(set(excluded)) == len(excluded) and set(excluded) <= case_ids,
                f"{rid}: exclusions must uniquely reference cases in the run split")

    case_inputs = {}

    def context(row):
        rid = row["id"]
        run = get(row["run_id"], "runs", rid)
        exp = get(run["experiment_id"], "experiments", rid)
        dataset = get(exp["dataset"]["id"], "datasets", rid)
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
        _validate_assessment(label["assessment"], label["status"] == "pending", rid)
        if label["status"] != "pending":
            require(run["status"] != "planned" and label["input_artifact"] is not None and bool(label["evidence"]),
                    f"{rid}: annotation needs observed input and evidence")
            require(label["rubric"]["artifact"] is not None, f"{rid}: annotation needs rubric artefact")
            require(_time(label["timestamp"]) >= _time(run["started_at"]), f"{rid}: annotation predates start")
        reviewed = [get(x, "human_labels", rid) for x in label["reviewed_label_ids"]]
        require((len(reviewed) >= 2) == (label["status"] == "adjudicated"),
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
            if result["status"] in {"indeterminate", "error"}:
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
                    require(metric["denominator"] <= len(included), f"{rid}: denominator exceeds included cases")
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
            exp = get(run["experiment_id"], "experiments", run["id"])
            dataset = get(exp["dataset"]["id"], "datasets", run["id"])
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
    for claim in row["paper_demonstrates"]:
        require(claim["source_id"] in sources, f"{rid}: paper evidence needs a traceable source")
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


def web_bundle(directory: str | Path = "registries") -> dict:
    """Production-only deterministic export; raw inputs/labels/configs stay local."""
    records = load_registries(directory)
    public_claims = []
    for paper in records["papers"]:
        sources = {s["id"]: s for s in paper["sources"]}
        for claim in paper["paper_demonstrates"]:
            if claim["verification_status"] == "verified":
                public_claims.append({"paper_id": paper["id"], "paper_version": paper["version"],
                                      **claim, "source": sources[claim["source_id"]]})
    public_metrics = []
    runs = {row["id"]: row for row in records["runs"]}
    for result in records["results"]:
        if result["kind"] == "aggregate" and runs[result["run_id"]]["status"] == "completed":
            for metric in result["metrics"]:
                if metric["status"] == "computed":
                    public_metrics.append({**metric, "result_id": result["id"], "run_id": result["run_id"],
                                           "experiment_id": runs[result["run_id"]]["experiment_id"],
                                           "validator": result["validator"], "code_commit": result["provenance"]["code_commit"],
                                           "artifacts": [{"id": a["id"], "sha256": a["sha256"]}
                                                         for a in result["provenance"]["artifacts"]]})
    return {"schema_version": SCHEMA_VERSION, "registry_sha256": canonical_sha256(records),
            "readiness": {**{name: len(rows) for name, rows in records.items()},
                          "papers_by_status": {s: sum(p["evidence_status"] == s for p in records["papers"])
                                               for s in ("listed", "screened", "deep-reviewed", "verified")},
                          "validators_implemented": sum(v["status"] == "implemented" for v in records["validators"]),
                          "experiments_completed": len({r["experiment_id"] for r in records["runs"] if r["status"] == "completed"})},
            "papers": [{**{k: p[k] for k in ("id", "version", "title", "year", "venue_or_identifier", "evidence_status",
                                             "sources", "open_questions")},
                        "our_interpretation": [i for i in p["our_interpretation"] if i["evidence_ids"]
                                               and set(i["evidence_ids"]) <= {e["id"] for e in p["paper_demonstrates"]
                                                                                 if e["verification_status"] == "verified"}],
                        "novelty_status": p["novelty"]["status"]} for p in records["papers"]],
            "verified_paper_evidence": public_claims, "metrics": public_metrics}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("validate", help="validate metadata only; never execute experiments")
    check.add_argument("--directory", default="registries")
    check.add_argument("--allow-templates", action="store_true")
    check.add_argument("--artifact-root", type=Path)
    check.add_argument("--previous-directory", type=Path, help="enforce append-only research history")
    export = sub.add_parser("export-web", help="export validated production readiness and traceable metrics")
    export.add_argument("--directory", default="registries")
    export.add_argument("--output", required=True, type=Path)
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
            bundle = web_bundle(args.directory)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(bundle, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
            print(f"Wrote {args.output}")
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Registry validation failed: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
