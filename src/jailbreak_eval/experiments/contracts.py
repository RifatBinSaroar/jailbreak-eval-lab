"""Version 1 file contracts. Validation uses only the Python standard library."""

import csv
import io
import json
import math
import re
from datetime import datetime


SCHEMA_VERSION = "1.0"
ID = r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}"
SHA256 = r"[0-9a-f]{64}"
PREDICTION_COLUMNS = (
    "case_id", "validator_id", "predicted_success", "status", "functional_level",
    "score", "r", "h", "f", "q", "e", "error_type", "evidence_ref",
)
LABEL_COLUMNS = (
    "label_id", "case_id", "label", "status", "annotator_ids",
    "adjudicator_id", "evidence_ref",
)


class ContractError(ValueError):
    """An input cannot be interpreted without changing its scientific meaning."""


def require(condition, message):
    if not condition:
        raise ContractError(message)


def object_fields(value, required, where, optional=()):
    require(isinstance(value, dict), f"{where}: expected an object")
    require(set(required) <= value.keys(), f"{where}: missing fields {sorted(set(required) - value.keys())}")
    require(value.keys() <= set(required) | set(optional),
            f"{where}: unknown fields {sorted(value.keys() - set(required) - set(optional))}")


def nonempty(value, where):
    require(isinstance(value, str) and bool(value.strip()), f"{where}: expected non-empty text")


def identifier(value, where, pattern=ID):
    require(isinstance(value, str) and re.fullmatch(pattern, value) is not None,
            f"{where}: invalid identifier")


def timestamp(value, where):
    nonempty(value, where)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContractError(f"{where}: expected ISO 8601 timestamp") from exc
    require(parsed.tzinfo is not None, f"{where}: timezone required")
    return parsed


def string_list(value, where, allow_empty=False):
    require(isinstance(value, list) and (allow_empty or bool(value)), f"{where}: expected a list")
    for item in value:
        nonempty(item, where)
    require(len(value) == len(set(value)), f"{where}: duplicate entries")


def load_json(raw, where):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, f"{where}: duplicate JSON key {key}")
            result[key] = value
        return result

    def invalid_number(value):
        raise ContractError(f"{where}: non-finite JSON number {value}")

    try:
        result = json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid_number)
        # Also reject overflowing literals such as 1e999, including inside config.
        json.dumps(result, allow_nan=False)
        return result
    except (ValueError, UnicodeError) as exc:
        raise ContractError(f"{where}: invalid JSON: {exc}") from exc


def load_csv(raw, columns, where):
    try:
        reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig"), newline=""), strict=True)
        headers = reader.fieldnames or []
        require(len(headers) == len(set(headers)) and set(headers) == set(columns),
                f"{where}: expected columns {', '.join(columns)}")
        rows = []
        for line, row in enumerate(reader, 2):
            require(None not in row and None not in row.values(), f"{where}:{line}: malformed row")
            rows.append(row)
        return rows
    except (UnicodeError, csv.Error) as exc:
        raise ContractError(f"{where}: invalid UTF-8 CSV: {exc}") from exc


def validate_dataset(dataset):
    object_fields(dataset, ("schema_version", "dataset_id", "version", "record_kind", "provenance", "cases"), "dataset")
    require(dataset["schema_version"] == SCHEMA_VERSION, "dataset: unsupported schema_version")
    identifier(dataset["dataset_id"], "dataset_id")
    nonempty(dataset["version"], "dataset version")
    require(dataset["record_kind"] in ("synthetic", "research"), "dataset: invalid record_kind")
    provenance = dataset["provenance"]
    object_fields(provenance, ("source", "source_version", "license", "retrieved_at",
                              "redistribution_allowed", "transformations"), "dataset provenance")
    for key in ("source", "source_version", "license"):
        nonempty(provenance[key], f"provenance {key}")
    timestamp(provenance["retrieved_at"], "retrieved_at")
    require(type(provenance["redistribution_allowed"]) in (bool, type(None)), "redistribution_allowed: use true, false, or null")
    string_list(provenance["transformations"], "transformations", allow_empty=True)
    require(isinstance(dataset["cases"], list) and bool(dataset["cases"]), "dataset: no cases")
    case_ids = set()
    split_groups = {key: {} for key in ("base_intent_id", "prompt_family_id", "duplicate_group_id", "response_sha256")}
    conditions = set()
    for case in dataset["cases"]:
        object_fields(case, ("case_id", "task_id", "attempt_id", "split", "base_intent_id",
                             "prompt_family_id", "duplicate_group_id", "response_sha256",
                             "model_id", "attack_method_id"), "case")
        for key, value in case.items():
            if key != "response_sha256":
                identifier(value, f"case {key}")
        identifier(case["response_sha256"], "response_sha256", SHA256)
        require(case["split"] in ("development", "test"), "case: invalid split")
        require(case["case_id"] not in case_ids, f"duplicate case_id: {case['case_id']}")
        case_ids.add(case["case_id"])
        condition = tuple(case[k] for k in ("task_id", "attempt_id", "model_id", "attack_method_id"))
        require(condition not in conditions, f"duplicate task/attempt/model/attack condition: {condition}")
        conditions.add(condition)
        for key, groups in split_groups.items():
            previous = groups.setdefault(case[key], case["split"])
            require(previous == case["split"], f"split leakage through {key}: {case[key]}")
    # A task cannot escape the group guard by changing all its group IDs.
    task_splits = {}
    for case in dataset["cases"]:
        require(task_splits.setdefault(case["task_id"], case["split"]) == case["split"],
                f"split leakage through task_id: {case['task_id']}")


def validate_manifest(manifest, dataset, dataset_hash):
    object_fields(manifest, ("schema_version", "experiment_id", "run_id", "created_at", "split",
                            "purpose", "record_kind", "code_commit", "config_version", "config",
                            "protocol", "dataset", "models", "attack_methods", "validators",
                            "human_ground_truth", "seed", "ablation"), "manifest")
    require(manifest["schema_version"] == SCHEMA_VERSION, "manifest: unsupported schema_version")
    identifier(manifest["experiment_id"], "experiment_id", r"EXP-[0-9]{3,}")
    identifier(manifest["run_id"], "run_id", r"RUN-[A-Za-z0-9][A-Za-z0-9_.-]{0,119}")
    created = timestamp(manifest["created_at"], "created_at")
    require(manifest["split"] in ("development", "test"), "manifest: invalid split")
    require(manifest["purpose"] == {"development": "development", "test": "final_evaluation"}[manifest["split"]],
            "test split is reserved for final_evaluation; development must use development split")
    require(manifest["record_kind"] == dataset["record_kind"], "record_kind mismatch")
    identifier(manifest["code_commit"], "code_commit", r"[0-9a-f]{40}")
    require(manifest["record_kind"] == "synthetic" or manifest["code_commit"] != "0" * 40,
            "research records cannot use the synthetic zero commit")
    nonempty(manifest["config_version"], "config_version")
    require(isinstance(manifest["config"], dict), "config: expected an object")
    require(manifest["seed"] is None or type(manifest["seed"]) is int, "seed: use integer or null")
    protocol = manifest["protocol"]
    object_fields(protocol, ("protocol_id", "version", "success_definition", "human_label_policy",
                             "asr_denominator", "frozen_at"), "protocol")
    for key in ("protocol_id", "version", "success_definition", "human_label_policy"):
        nonempty(protocol[key], f"protocol {key}")
    require(protocol["asr_denominator"] == "determinate_predictions", "unsupported ASR denominator policy")
    if protocol["frozen_at"] is not None:
        require(timestamp(protocol["frozen_at"], "frozen_at") <= created, "protocol frozen after run creation")
    require(manifest["split"] != "test" or protocol["frozen_at"] is not None,
            "test runs require a frozen protocol")
    ref = manifest["dataset"]
    object_fields(ref, ("dataset_id", "version", "sha256"), "dataset reference")
    require(ref == {"dataset_id": dataset["dataset_id"], "version": dataset["version"], "sha256": dataset_hash},
            "dataset ID, version, or SHA-256 mismatch")
    for collection, id_key in (("models", "model_id"), ("attack_methods", "attack_method_id"), ("validators", "validator_id")):
        entries = manifest[collection]
        require(isinstance(entries, list) and bool(entries), f"{collection}: expected non-empty list")
        seen = set()
        for entry in entries:
            fields = (id_key, "name", "version", "config")
            if collection == "validators":
                fields += ("success_construct",)
            object_fields(entry, fields, collection)
            identifier(entry[id_key], id_key)
            for key in ("name", "version"):
                nonempty(entry[key], f"{collection} {key}")
            require(isinstance(entry["config"], dict), f"{collection} config: expected object")
            if collection == "validators":
                nonempty(entry["success_construct"], "success_construct")
            require(entry[id_key] not in seen, f"duplicate {id_key}")
            seen.add(entry[id_key])
    ground = manifest["human_ground_truth"]
    object_fields(ground, ("version", "rubric_version", "source"), "human_ground_truth")
    for key in ground:
        nonempty(ground[key], f"human_ground_truth {key}")
    if manifest["ablation"] is not None:
        object_fields(manifest["ablation"], ("study_id", "variant_id", "components"), "ablation")
        identifier(manifest["ablation"]["study_id"], "ablation study_id")
        identifier(manifest["ablation"]["variant_id"], "ablation variant_id")
        string_list(manifest["ablation"]["components"], "ablation components", allow_empty=True)
    selected = [case for case in dataset["cases"] if case["split"] == manifest["split"]]
    require(bool(selected), "run split has no cases")
    for collection, id_key in (("models", "model_id"), ("attack_methods", "attack_method_id")):
        require({c[id_key] for c in selected} == {entry[id_key] for entry in manifest[collection]},
                f"{collection}: metadata must exactly cover the selected split")
    return selected


def validate_rows(predictions, labels, selected, manifest):
    cases = {case["case_id"] for case in selected}
    validators = {v["validator_id"]: v for v in manifest["validators"]}
    seen = set()
    for row in predictions:
        require(row["case_id"] in cases, f"prediction: unknown or wrong-split case {row['case_id']}")
        require(row["validator_id"] in validators, f"unknown validator {row['validator_id']}")
        key = (row["case_id"], row["validator_id"])
        require(key not in seen, f"duplicate prediction: {key}")
        seen.add(key)
        require(row["status"] in ("ok", "indeterminate", "error"), f"prediction {key}: invalid status")
        require(row["predicted_success"] in (("0", "1") if row["status"] == "ok" else ("",)),
                f"prediction {key}: ok needs 0/1; error/indeterminate needs blank prediction")
        if row["status"] == "error":
            nonempty(row["error_type"], "error_type")
        else:
            require(not row["error_type"], "error_type requires error status")
        stage = row["functional_level"]
        require(stage in ("", "F0", "F1", "F2", "F3", "F4", "F5", "FX"), "invalid functional_level")
        if stage == "FX":
            require(row["status"] != "ok", "FX must remain indeterminate/error")
        if validators[row["validator_id"]]["success_construct"] == "F5" and stage:
            if row["status"] == "ok":
                require(row["predicted_success"] == ("1" if stage == "F5" else "0"), "F5 endpoint/stage mismatch")
        for column in ("score", "r", "h", "f", "q", "e"):
            if row[column]:
                try:
                    number = float(row[column])
                except ValueError as exc:
                    raise ContractError(f"{column}: invalid number") from exc
                require(math.isfinite(number) and 0 <= number <= 1, f"{column}: expected finite number in [0,1]")
    seen_cases, seen_ids = set(), set()
    for row in labels:
        require(row["case_id"] in cases, f"label: unknown or wrong-split case {row['case_id']}")
        identifier(row["label_id"], "label_id")
        require(row["case_id"] not in seen_cases and row["label_id"] not in seen_ids, "duplicate label/case; supply one resolved reference row per case")
        seen_cases.add(row["case_id"])
        seen_ids.add(row["label_id"])
        require(row["status"] in ("consensus", "adjudicated", "uncertain", "unreviewed"), "label: invalid status")
        resolved = row["status"] in ("consensus", "adjudicated")
        require(row["label"] in (("0", "1") if resolved else ("",)), "unresolved labels must remain blank; resolved labels need 0/1")
        annotators = row["annotator_ids"].split("|") if row["annotator_ids"] else []
        for annotator in annotators:
            identifier(annotator, "annotator_id")
        require(len(annotators) == len(set(annotators)), "duplicate annotator")
        if resolved:
            require(len(annotators) >= 2, "reference labels require at least two independent annotator IDs")
            nonempty(row["evidence_ref"], "label evidence_ref")
        if row["status"] == "adjudicated":
            identifier(row["adjudicator_id"], "adjudicator_id")
        else:
            require(not row["adjudicator_id"], "adjudicator_id requires adjudicated status")
