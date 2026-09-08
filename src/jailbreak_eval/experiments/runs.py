"""Immutable run bundles and a fail-closed website data builder."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile

from .analysis import ANALYSIS_VERSION, analyze
from .contracts import (
    ContractError, LABEL_COLUMNS, PREDICTION_COLUMNS, load_csv, load_json,
    object_fields, require, validate_dataset, validate_manifest, validate_rows,
)


INPUT_FILES = ("dataset_manifest.json", "predictions.csv", "human_labels.csv")
DERIVED_FILES = ("metrics.json", "errors.json")


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def json_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def analysis_identity():
    root = Path(__file__).parent
    return {"version": ANALYSIS_VERSION, "implementation_sha256": digest(b"".join(
        name.encode("utf-8") + b"\0" + (root / name).read_bytes().replace(b"\r\n", b"\n")
        for name in ("contracts.py", "analysis.py", "runs.py")
    ))}


def validate_inputs(manifest, inputs):
    dataset = load_json(inputs["dataset_manifest.json"], "dataset_manifest.json")
    validate_dataset(dataset)
    selected = validate_manifest(manifest, dataset, digest(inputs["dataset_manifest.json"]))
    predictions = load_csv(inputs["predictions.csv"], PREDICTION_COLUMNS, "predictions.csv")
    labels = load_csv(inputs["human_labels.csv"], LABEL_COLUMNS, "human_labels.csv")
    validate_rows(predictions, labels, selected, manifest)
    return selected, predictions, labels


def read_inputs(manifest_path, dataset_path, predictions_path, labels_path):
    manifest = load_json(Path(manifest_path).read_bytes(), "manifest.json")
    inputs = {name: Path(path).read_bytes() for name, path in zip(
        INPUT_FILES, (dataset_path, predictions_path, labels_path))}
    selected, predictions, labels = validate_inputs(manifest, inputs)
    return manifest, inputs, selected, predictions, labels


def record_run(manifest_path, dataset_path, predictions_path, labels_path, runs_dir):
    """Import existing decisions, never execute a model, validator, or response."""
    manifest, inputs, selected, predictions, labels = read_inputs(
        manifest_path, dataset_path, predictions_path, labels_path)
    metrics, errors = analyze(manifest, selected, predictions, labels)
    artifacts = {**inputs, "metrics.json": json_bytes(metrics), "errors.json": json_bytes(errors)}
    saved = {**manifest, "analysis": analysis_identity(),
             "artifacts": {name: {"sha256": digest(raw), "size_bytes": len(raw)} for name, raw in artifacts.items()}}
    root = Path(runs_dir)
    root.mkdir(parents=True, exist_ok=True)
    target = root / manifest["run_id"]
    require(not target.exists() and not target.is_symlink(), f"run already exists: {target}; use a new run ID")
    staging = Path(tempfile.mkdtemp(prefix=".run-staging-", dir=root))
    try:
        for name, raw in artifacts.items():
            (staging / name).write_bytes(raw)
        (staging / "manifest.json").write_bytes(json_bytes(saved))
        # The immutable target is published only after the entire bundle exists.
        require(not target.exists(), f"run already exists: {target}")
        staging.rename(target)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return target


def verify_run(run_dir):
    root = Path(run_dir)
    require(root.is_dir() and not root.is_symlink(), f"invalid run directory: {root}")
    expected = {"manifest.json", *INPUT_FILES, *DERIVED_FILES}
    require({p.name for p in root.iterdir()} == expected, f"{root.name}: incomplete or unexpected run files")
    for name in expected:
        path = root / name
        require(path.is_file() and not path.is_symlink(), f"{root.name}: artifact must be a regular file: {name}")
    saved = load_json((root / "manifest.json").read_bytes(), "manifest.json")
    require(isinstance(saved, dict), "manifest.json: expected object")
    manifest = {k: v for k, v in saved.items() if k not in ("artifacts", "analysis")}
    require("artifacts" in saved and "analysis" in saved, f"{root.name}: missing integrity metadata")
    require(manifest.get("run_id") == root.name, "run directory / run_id mismatch")
    require(saved["analysis"] == analysis_identity(),
            "analysis implementation changed; retain the recorded code revision or create a new run under the new implementation")
    object_fields(saved["artifacts"], (*INPUT_FILES, *DERIVED_FILES), "artifacts")
    artifacts = {}
    for name in (*INPUT_FILES, *DERIVED_FILES):
        raw = (root / name).read_bytes()
        require(saved["artifacts"][name] == {"sha256": digest(raw), "size_bytes": len(raw)},
                f"{root.name}: artifact hash/size mismatch: {name}")
        artifacts[name] = raw
    selected, predictions, labels = validate_inputs(manifest, artifacts)
    metrics, errors = analyze(manifest, selected, predictions, labels)
    for name, rebuilt in (("metrics.json", metrics), ("errors.json", errors)):
        require(artifacts[name] == json_bytes(rebuilt), f"{root.name}: {name} does not reproduce from inputs")
    return saved, metrics, errors


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".web-data-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(json_bytes(value))
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def aggregate_only(value):
    """Case membership stays in the traceable run artifacts, outside web JSON."""
    if isinstance(value, dict):
        return {k: aggregate_only(v) for k, v in value.items() if k != "case_ids"}
    if isinstance(value, list):
        return [aggregate_only(v) for v in value]
    return value


def rebuild_web(runs_dir, output, include_synthetic=False):
    root, destination = Path(runs_dir), Path(output)
    require(not destination.resolve().is_relative_to(root.resolve()), "web output must be outside immutable runs directory")
    records, skipped = [], []
    dataset_versions = {}
    dataset_split_groups = {}
    run_dirs = sorted(root.iterdir()) if root.exists() else []
    for run_dir in run_dirs:
        if run_dir.name.startswith(".") or run_dir.name == "README.md":
            continue
        manifest, metrics, errors = verify_run(run_dir)
        # A version identifies one exact full manifest, regardless of run split.
        # Across versions, retain split assignments within the dataset identity.
        dataset = load_json((run_dir / "dataset_manifest.json").read_bytes(), "dataset_manifest.json")
        version_key = (dataset["dataset_id"], dataset["version"])
        known_hash = dataset_versions.setdefault(version_key, manifest["dataset"]["sha256"])
        require(known_hash == manifest["dataset"]["sha256"], f"dataset version has conflicting manifests: {version_key}")
        for case in dataset["cases"]:
            for field in ("case_id", "task_id", "base_intent_id", "prompt_family_id", "duplicate_group_id", "response_sha256"):
                group_key = (dataset["dataset_id"], field, case[field])
                previous = dataset_split_groups.setdefault(group_key, case["split"])
                require(previous == case["split"], f"cross-run split leakage: {group_key}")
        if manifest["record_kind"] == "synthetic" and not include_synthetic:
            skipped.append(manifest["run_id"])
            continue
        summary = {key: manifest[key] for key in (
            "experiment_id", "run_id", "created_at", "split", "purpose", "record_kind",
            "code_commit", "config_version", "dataset", "ablation",
        )}
        summary["protocol"] = {key: manifest["protocol"][key] for key in ("protocol_id", "version", "success_definition", "asr_denominator")}
        for name in ("models", "attack_methods", "validators"):
            # Deliberately keep potentially private model prompts/config outside public aggregates.
            summary[name] = [{k: v for k, v in entry.items() if k != "config"} for entry in manifest[name]]
        summary["human_ground_truth"] = {k: manifest["human_ground_truth"][k] for k in ("version", "rubric_version")}
        summary["metrics"] = aggregate_only(metrics)
        summary["error_counts"] = {
            "evaluator_outcomes": len(errors["evaluator_outcomes"]),
            "reference_exclusions": len(errors["reference_exclusions"]),
            "disagreements": len(errors["disagreements"]),
        }
        summary["provenance"] = {
            "run_directory": f"results/runs/{manifest['run_id']}",
            "manifest_sha256": digest((run_dir / "manifest.json").read_bytes()),
            "artifacts": manifest["artifacts"], "analysis": manifest["analysis"],
        }
        records.append(summary)
    # No automatic pooled estimate across different splits, constructs, runs, or ablations.
    result = {"schema_version": "1.0", "analysis_version": ANALYSIS_VERSION,
              "runs": records, "run_count": len(records),
              "research_run_count": sum(r["record_kind"] == "research" for r in records),
              "synthetic_run_count": sum(r["record_kind"] == "synthetic" for r in records),
              "excluded_synthetic_run_ids": skipped}
    atomic_json(destination, result)
    return result
