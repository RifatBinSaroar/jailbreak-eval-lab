"""Benign metadata contract tests. Synthetic records are never research results.

No test invokes a model, attack, validator adapter, experiment or metric engine.
The observed-path fixture records only an indeterminate benign text artefact.
"""

from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from jailbreak_eval.registry import (
    REGISTRIES, RegistryError, canonical_sha256, load_registries, main,
    read_json, run_inputs_sha256, validate_history, validate_registries,
    verify_local_artifacts, web_bundle,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def templates():
    return {name: read_json(ROOT / "examples/registries" / f"{name}.json") for name in REGISTRIES}


def rows(envelopes):
    return {name: envelope["records"] for name, envelope in envelopes.items()}


def refresh(envelopes):
    data = rows(envelopes)
    for run in data["runs"]:
        experiment = next(e for e in data["experiments"] if e["id"] == run["experiment_id"])
        run["experiment_sha256"] = canonical_sha256(experiment)
        run["inputs_sha256"] = run_inputs_sha256(experiment, data)


def save(envelopes, directory):
    directory.mkdir(parents=True, exist_ok=True)
    for name, envelope in envelopes.items():
        (directory / f"{name}.json").write_text(json.dumps(envelope), encoding="utf-8")
    return directory


@pytest.fixture
def observed(templates, tmp_path):
    # Explicit unit-test-only metadata. These records are never committed/exported
    # as scientific observations. The input bytes really exist and are harmless.
    data = json.loads(json.dumps(templates).replace("template-", "unit-"))
    for collection in rows(data).values():
        for record in collection:
            record["record_kind"] = "research"
            record["notes"] = "UNIT TEST FIXTURE ONLY; not experimental evidence."
    path = tmp_path / "benign.txt"
    path.write_text("Benign metadata validation fixture. No code or payload.\n")
    artifact = dict(id="artifact:unit-benign", uri="benign.txt", sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                    media_type="text/plain", description="Unit-test input/evidence placeholder, never research data.")
    records = rows(data)
    validator = records["validators"][0]
    validator.update(status="implemented", executes_code=False, code_commit=records["experiments"][0]["code_commit"],
                     implementation=deepcopy(artifact))
    # Shared rubric definitions must agree everywhere.
    for row in (validator, records["human_labels"][0]):
        row["rubric"]["artifact"] = deepcopy(artifact)
    dataset = records["datasets"][0]
    dataset.update(status="frozen", manifest=deepcopy(artifact))
    dataset["provenance"].update(upstream_version="unit-fixture-v1", retrieved_at="2026-09-08T00:00:00Z")
    experiment = records["experiments"][0]
    experiment.update(status="frozen", protocol=deepcopy(artifact))
    experiment["human_ground_truth"]["artifact"] = deepcopy(artifact)
    experiment["config"]["parameters"]["private_value"] = "LOCAL_ONLY_SENTINEL"
    run = records["runs"][0]
    run.update(status="completed", started_at="2026-09-08T00:01:00Z", finished_at="2026-09-08T00:03:00Z",
               environment=deepcopy(artifact), artifacts=[deepcopy(artifact)])
    label = records["human_labels"][0]
    label["timestamp"] = "2026-09-08T00:02:00Z"
    result = records["results"][0]
    result.update(status="indeterminate", input_artifact=deepcopy(artifact), timestamp="2026-09-08T00:02:00Z")
    result["assessment"].update(functional_stage="FX", reason="Unit-test evidence only; no success was assessed.")
    result["provenance"]["artifacts"] = [deepcopy(artifact)]
    records["results"][1]["timestamp"] = "2026-09-08T00:03:00Z"
    refresh(data)
    return data


def test_empty_production_is_honest_and_export_is_deterministic():
    data = load_registries(ROOT / "registries")
    assert set(data) == set(REGISTRIES)
    assert all(not collection for collection in data.values())
    bundle = web_bundle(ROOT / "registries")
    assert bundle["readiness"]["experiments_completed"] == 0
    assert bundle["metrics"] == bundle["papers"] == bundle["verified_paper_evidence"] == []
    assert bundle == web_bundle(ROOT / "registries")


def test_linked_templates_are_valid_but_never_production(templates, tmp_path):
    assert len(validate_registries(templates, allow_templates=True)["domains"]) == 2
    with pytest.raises(RegistryError, match="templates forbidden"):
        validate_registries(templates)
    with pytest.raises(RegistryError, match="templates forbidden"):
        web_bundle(save(templates, tmp_path / "templates"))


def test_observed_indeterminate_path_and_local_checksums(observed, tmp_path):
    data = validate_registries(observed)
    assert verify_local_artifacts(data, tmp_path) == 1
    assert data["results"][0]["assessment"]["predicted_success"] is None


@pytest.mark.parametrize("field", ["config", "dataset", "validators", "model", "attack_method", "code_commit", "timestamp", "split"])
def test_experiment_reproducibility_fields_are_required(templates, field):
    del templates["experiments"]["records"][0][field]
    with pytest.raises(RegistryError, match="required property"):
        validate_registries(templates, allow_templates=True)


@pytest.mark.parametrize("value", ["", "2026-09-08", "2026-09-08T00:00:00", "2026-02-30T00:00:00Z"])
def test_invalid_or_naive_timestamps_rejected(templates, value):
    templates["papers"]["records"][0]["timestamp"] = value
    with pytest.raises(RegistryError, match="date-time"):
        validate_registries(templates, allow_templates=True)


def test_duplicate_ids_rejected(templates):
    templates["papers"]["records"].append(deepcopy(templates["papers"]["records"][0]))
    with pytest.raises(RegistryError, match="non-unique|duplicate stable ID"):
        validate_registries(templates, allow_templates=True)


def test_unknown_fields_rejected(templates):
    templates["results"]["records"][0]["fake_asr"] = None
    with pytest.raises(RegistryError, match="Additional properties"):
        validate_registries(templates, allow_templates=True)


def test_dangling_parent_rejected(templates):
    templates["domains"]["records"][1]["parent_id"] = "domain:missing"
    with pytest.raises(RegistryError, match="dangling reference"):
        validate_registries(templates, allow_templates=True)


def test_subdomain_cannot_parent_itself(templates):
    child = templates["domains"]["records"][1]
    child["parent_id"] = child["id"]
    with pytest.raises(RegistryError, match="does not match"):
        validate_registries(templates, allow_templates=True)


def test_version_pin_mismatch_rejected(templates):
    templates["experiments"]["records"][0]["dataset"]["version"] = "different-version"
    with pytest.raises(RegistryError, match="version mismatch"):
        validate_registries(templates, allow_templates=True)


def test_changed_config_invalidates_run_hash(templates):
    templates["experiments"]["records"][0]["config"]["parameters"]["changed"] = True
    with pytest.raises(RegistryError, match="experiment snapshot hash mismatch"):
        validate_registries(templates, allow_templates=True)


def test_changed_dataset_metadata_invalidates_run_hash(templates):
    templates["datasets"]["records"][0]["notes"] = "Changed manifest meaning."
    with pytest.raises(RegistryError, match="input definitions hash mismatch"):
        validate_registries(templates, allow_templates=True)


def test_duplicate_group_cannot_cross_splits(templates):
    dataset = templates["datasets"]["records"][0]
    case = deepcopy(dataset["cases"][0])
    case.update(id="case:template-variant", split="test")
    dataset["cases"].append(case)
    with pytest.raises(RegistryError, match="split leakage"):
        validate_registries(templates, allow_templates=True)


def test_label_case_split_must_match_experiment(templates):
    templates["human_labels"]["records"][0]["split"] = "test"
    with pytest.raises(RegistryError, match="label dataset/split"):
        validate_registries(templates, allow_templates=True)


def test_pending_observations_cannot_become_zero_or_false(templates):
    # Deliberately invalid value exercises rejection, not a reported experiment.
    templates["human_labels"]["records"][0]["assessment"]["predicted_success"] = False
    with pytest.raises(RegistryError, match="must remain null"):
        validate_registries(templates, allow_templates=True)


def test_fx_is_not_failure(observed):
    observed["results"]["records"][0]["assessment"]["predicted_success"] = False
    with pytest.raises(RegistryError, match="FX cannot"):
        validate_registries(observed)


def test_observed_prediction_requires_input(observed):
    observed["results"]["records"][0]["input_artifact"] = None
    with pytest.raises(RegistryError, match="exact input artefact"):
        validate_registries(observed)


def test_observed_result_requires_output_provenance(observed):
    observed["results"]["records"][0]["provenance"]["artifacts"] = []
    with pytest.raises(RegistryError, match="output artefacts"):
        validate_registries(observed)


def test_completed_run_requires_case_accounting(observed):
    observed["results"]["records"] = []
    with pytest.raises(RegistryError, match="unaccounted"):
        validate_registries(observed)


def test_run_finish_cannot_precede_start(observed):
    observed["runs"]["records"][0]["finished_at"] = "2026-09-08T00:00:00Z"
    with pytest.raises(RegistryError, match="finish precedes start"):
        validate_registries(observed)


def test_duplicate_prediction_cannot_bias_aggregate(observed):
    result = deepcopy(observed["results"]["records"][0])
    result["id"] = "result:unit-duplicate"
    observed["results"]["records"].append(result)
    with pytest.raises(RegistryError, match="duplicate prediction"):
        validate_registries(observed)


def annotated(data):
    label = data["human_labels"]["records"][0]
    prediction = data["results"]["records"][0]
    label.update(status="annotated", input_artifact=deepcopy(prediction["input_artifact"]),
                 evidence=deepcopy(prediction["provenance"]["artifacts"]), assessment=deepcopy(prediction["assessment"]))
    return label


def test_independent_annotation_and_adjudication_context(observed):
    first = annotated(observed)
    second = deepcopy(first)
    second.update(id="label:unit-second", annotator_id="annotator:unit-second")
    final = deepcopy(first)
    final.update(id="label:unit-adjudicated", annotator_id="annotator:unit-reviewer", status="adjudicated",
                 reviewed_label_ids=[first["id"], second["id"]])
    observed["human_labels"]["records"].extend([second, final])
    validate_registries(observed)
    second["annotator_id"] = first["annotator_id"]
    with pytest.raises(RegistryError, match="independent"):
        validate_registries(observed)


def test_prediction_cannot_use_different_label_input(observed):
    label = annotated(observed)
    label["input_artifact"] = {**label["input_artifact"], "id": "artifact:unit-other-input", "uri": "other.txt"}
    observed["results"]["records"][0]["human_label_ids"] = [label["id"]]
    with pytest.raises(RegistryError, match="inconsistent input|label input differs"):
        validate_registries(observed)


def test_label_supersession_cannot_cycle(observed):
    label = annotated(observed)
    label["supersedes_id"] = label["id"]
    with pytest.raises(RegistryError, match="strictly backwards"):
        validate_registries(observed)


def test_aggregate_cannot_reference_itself(observed):
    aggregate = observed["results"]["records"][1]
    aggregate["source_result_ids"] = [aggregate["id"]]
    with pytest.raises(RegistryError, match="aggregate mixes"):
        validate_registries(observed)


def test_aggregate_inclusions_and_exclusions_are_disjoint(observed):
    aggregate = observed["results"]["records"][1]
    prediction = observed["results"]["records"][0]
    aggregate["source_result_ids"] = aggregate["excluded_result_ids"] = [prediction["id"]]
    with pytest.raises(RegistryError, match="both included and excluded"):
        validate_registries(observed)


def test_uncomputed_metric_cannot_have_a_value(templates):
    # Deliberate malformed unit-test input; no fabricated metric is accepted.
    templates["results"]["records"][1]["metrics"][0]["value"] = 0
    with pytest.raises(RegistryError, match="not of type 'null'"):
        validate_registries(templates, allow_templates=True)


def test_computed_fixture_inventory_exports_full_provenance(observed, tmp_path):
    # Count actual harmless in-memory fixture records, never fabricate ASR or
    # experimental performance. This exercises the future publication path.
    prediction, aggregate = observed["results"]["records"]
    aggregate.update(status="measured", source_result_ids=[prediction["id"]])
    aggregate["provenance"]["artifacts"] = deepcopy(prediction["provenance"]["artifacts"])
    metric = aggregate["metrics"][0]
    metric.update(name="unit_fixture_inventory_count", definition="Number of included unit-test fixture records, including FX.",
                  status="computed", unit="fixture records", value=len(aggregate["source_result_ids"]),
                  denominator=len(aggregate["source_result_ids"]), reason=None)
    bundle = web_bundle(save(observed, tmp_path / "metadata"))
    exported = bundle["metrics"][0]
    assert exported["value"] == len(aggregate["source_result_ids"])
    assert exported["result_id"] == aggregate["id"]
    assert exported["run_id"] == aggregate["run_id"]
    assert exported["experiment_id"] == observed["experiments"]["records"][0]["id"]
    assert exported["artifacts"][0]["sha256"] == prediction["input_artifact"]["sha256"]
    assert "uri" not in exported["artifacts"][0]
    # An unsupported denominator must fail rather than publish a distorted rate.
    metric["denominator"] = len(aggregate["source_result_ids"]) + 1
    with pytest.raises(RegistryError, match="denominator exceeds"):
        validate_registries(observed)


def test_novelty_cannot_be_inferred_from_missing_papers(templates):
    novelty = templates["papers"]["records"][0]["novelty"]
    novelty.update(status="novel", basis="no_papers_found")
    with pytest.raises(RegistryError):
        validate_registries(templates, allow_templates=True)


def test_overlap_claim_requires_evidence(templates):
    templates["papers"]["records"][0]["novelty"]["status"] = "prior_work_overlap"
    with pytest.raises(RegistryError, match="explicit evidence"):
        validate_registries(templates, allow_templates=True)


def test_verified_paper_cannot_lack_sources(templates):
    templates["papers"]["records"][0]["evidence_status"] = "verified"
    with pytest.raises(RegistryError, match="primary source"):
        validate_registries(templates, allow_templates=True)


def test_website_claims_require_verified_sources_and_keep_buckets(observed, tmp_path):
    paper = observed["papers"]["records"][0]
    source = dict(id="source:unit-paper", url="https://example.invalid/unit-test", locator="Unit-test fixture only")
    paper["sources"] = [source]
    claim = dict(id="evidence:unit-claim", topic="unit-test", claim="Harmless source fixture text.",
                 source_id=source["id"], locator="Fixture line one", verification_status="unverified")
    paper["paper_demonstrates"] = [claim]
    paper["our_interpretation"] = [dict(id="interpretation:unit-claim", text="Unit-test interpretation.", evidence_ids=[claim["id"]])]
    directory = save(observed, tmp_path / "registry")
    bundle = web_bundle(directory)
    assert bundle["verified_paper_evidence"] == []
    assert bundle["papers"][0]["our_interpretation"] == []
    claim["verification_status"] = "verified"
    bundle = web_bundle(save(observed, directory))
    assert bundle["verified_paper_evidence"][0]["source"] == source
    assert bundle["papers"][0]["our_interpretation"] == paper["our_interpretation"]
    assert "LOCAL_ONLY_SENTINEL" not in json.dumps(bundle)
    assert "benign.txt" not in json.dumps(bundle)
    assert bundle["metrics"] == []


def test_malformed_source_reference_rejected(templates):
    paper = templates["papers"]["records"][0]
    paper["paper_demonstrates"] = [dict(id="evidence:template-dangling", topic="unit-test", claim="Fixture only.",
        source_id="source:missing", locator="Missing", verification_status="unverified")]
    with pytest.raises(RegistryError, match="traceable source"):
        validate_registries(templates, allow_templates=True)


def test_published_history_is_append_only(observed):
    previous = validate_registries(observed)
    current = deepcopy(previous)
    validate_history(current, previous)
    current["papers"][0]["title"] = "Changed"
    with pytest.raises(RegistryError, match="immutable"):
        validate_history(current, previous)
    current = deepcopy(previous)
    current["papers"] = []
    with pytest.raises(RegistryError, match="immutable"):
        validate_history(current, previous)


def test_checksum_verification_detects_tampering(observed, tmp_path):
    data = validate_registries(observed)
    (tmp_path / "benign.txt").write_text("changed benign bytes")
    with pytest.raises(RegistryError, match="hash mismatch"):
        verify_local_artifacts(data, tmp_path)


@pytest.mark.parametrize("uri", ["../outside.txt", "/etc/passwd", "https://example.invalid/data"])
def test_artifact_verification_is_local_and_contained(observed, tmp_path, uri):
    data = validate_registries(observed)
    artifact = {**data["validators"][0]["implementation"], "uri": uri}
    with pytest.raises(RegistryError, match="relative file path|escapes root"):
        verify_local_artifacts({"artifacts": [artifact]}, tmp_path)


def test_artifact_verification_rejects_conflicting_repeat_ids(observed, tmp_path):
    data = validate_registries(observed)
    data["validators"][0]["implementation"]["uri"] = "changed.txt"
    with pytest.raises(RegistryError, match="conflicting artefact definitions"):
        verify_local_artifacts(data, tmp_path)


@pytest.mark.parametrize("text", ['{"id": 1, "id": 2}', '{"value": NaN}', '{"value": Infinity}'])
def test_nonstandard_json_rejected(tmp_path, text):
    path = tmp_path / "invalid.json"
    path.write_text(text)
    with pytest.raises(RegistryError):
        read_json(path)


def test_python_nonfinite_values_rejected(templates):
    templates["experiments"]["records"][0]["config"]["parameters"]["invalid"] = float("inf")
    with pytest.raises(RegistryError, match="non-finite"):
        validate_registries(templates, allow_templates=True)


def test_cli_missing_file_is_failure_without_output(tmp_path):
    output = tmp_path / "must-not-exist.json"
    with pytest.raises(SystemExit) as error:
        main(["export-web", "--directory", str(tmp_path), "--output", str(output)])
    assert error.value.code == 1
    assert not output.exists()


def test_cli_production_export(tmp_path):
    output = tmp_path / "research-data.json"
    assert main(["export-web", "--directory", str(ROOT / "registries"), "--output", str(output)]) == 0
    assert read_json(output)["metrics"] == []
