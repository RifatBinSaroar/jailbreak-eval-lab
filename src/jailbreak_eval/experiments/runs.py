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
        for name in ("contracts.py", "analysis.py", "runs.py", "canonical.py", "../registry.py", "../schemas/registry.schema.json")
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


def record_run(manifest_path, dataset_path, predictions_path, labels_path, runs_dir, *, canonical_inputs=None):
    """Import existing decisions, never execute a model, validator, or response."""
    manifest, inputs, selected, predictions, labels = read_inputs(
        manifest_path, dataset_path, predictions_path, labels_path)
    metrics, errors = analyze(manifest, selected, predictions, labels)
    artifacts = {**inputs, "metrics.json": json_bytes(metrics), "errors.json": json_bytes(errors)}
    saved = {**manifest, "analysis": analysis_identity(),
             "artifacts": {name: {"sha256": digest(raw), "size_bytes": len(raw)} for name, raw in artifacts.items()}}
    if canonical_inputs is not None:
        raw = json_bytes(canonical_inputs)
        artifacts["canonical_inputs.json"] = raw
        saved["canonical_inputs"] = {"sha256": digest(raw), "size_bytes": len(raw)}
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
    saved = load_json((root / "manifest.json").read_bytes(), "manifest.json")
    expected = {"manifest.json", *INPUT_FILES, *DERIVED_FILES}
    if "canonical_inputs" in saved:
        expected.add("canonical_inputs.json")
    require({p.name for p in root.iterdir()} == expected, f"{root.name}: incomplete or unexpected run files")
    for name in expected:
        path = root / name
        require(path.is_file() and not path.is_symlink(), f"{root.name}: artifact must be a regular file: {name}")
    saved = load_json((root / "manifest.json").read_bytes(), "manifest.json")
    require(isinstance(saved, dict), "manifest.json: expected object")
    manifest = {k: v for k, v in saved.items() if k not in ("artifacts", "analysis", "canonical_inputs")}
    require("artifacts" in saved and "analysis" in saved, f"{root.name}: missing integrity metadata")
    require(manifest.get("run_id") == root.name, "run directory / run_id mismatch")
    require(saved["analysis"] == analysis_identity(),
            "analysis implementation changed; retain the recorded code revision or create a new run under the new implementation")
    if "canonical_inputs" in saved:
        raw = (root / "canonical_inputs.json").read_bytes()
        require(saved["canonical_inputs"] == {"sha256": digest(raw), "size_bytes": len(raw)}, "canonical input snapshot hash mismatch")
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
    """Compatibility command alias; all data comes from canonical registries."""
    from ..registry import write_web
    root = Path(runs_dir).resolve().parent.parent
    return write_web(root / "registries", output, artifact_root=root, include_synthetic=include_synthetic)
