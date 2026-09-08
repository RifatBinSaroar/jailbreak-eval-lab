"""Safe, hand-calculated tests. No model calls, payloads, or real experiments."""

import copy
import csv
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from jailbreak_eval.experiments.analysis import analyze, confusion_metrics
from jailbreak_eval.experiments.contracts import (
    ContractError, LABEL_COLUMNS, PREDICTION_COLUMNS, load_csv, load_json,
    validate_dataset, validate_manifest, validate_rows,
)
from jailbreak_eval.experiments.runs import (
    digest, json_bytes, read_inputs, rebuild_web, record_run, verify_run,
)

from jailbreak_eval.experiments.canonical import record_canonical
from jailbreak_eval.registry import REGISTRIES
from jailbreak_eval.store import envelopes, encode

FIXTURE = ROOT / "tests" / "fixtures" / "run_framework"


class FrameworkTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'registries').mkdir()
        for n,e in envelopes({n:[] for n in REGISTRIES}).items():
            (self.root/'registries'/f'{n}.json').write_bytes(encode(e))
        self.paths = [FIXTURE / name for name in ("manifest.json", "dataset_manifest.json", "predictions.csv", "human_labels.csv")]
        self.manifest, self.inputs, self.cases, self.predictions, self.labels = read_inputs(*self.paths)
        self.dataset = load_json(self.inputs["dataset_manifest.json"], "dataset")

    def record(self):
        return record_canonical(*self.paths, self.root / "results" / "runs", self.root / "registries", self.root)

    def test_hand_calculated_metrics_and_paired_asr(self):
        metrics, errors = analyze(self.manifest, self.cases, self.predictions, self.labels)
        a, b = metrics["evaluators"]["VAL-A"], metrics["evaluators"]["VAL-B"]
        self.assertEqual(a["classification"]["confusion_matrix"], {"tp": 1, "tn": 1, "fp": 1, "fn": 1})
        for metric in ("accuracy", "precision", "recall", "f1", "false_positive_rate", "false_negative_rate"):
            self.assertEqual(a["classification"][metric], 0.5)
        self.assertEqual(a["classification"]["mcc"], 0)
        self.assertEqual(a["asr"]["rate"], 0.5)
        self.assertEqual(b["asr"]["rate"], 2 / 3)
        self.assertEqual(b["asr"]["coverage"], 0.75)
        self.assertEqual(b["asr"]["lower_bound_all_cases"], 0.5)
        self.assertEqual(b["asr"]["upper_bound_all_cases"], 0.75)
        comparison = metrics["evaluator_comparisons"][0]
        self.assertEqual(comparison["n"], 3)
        self.assertEqual(comparison["asr_difference_pp_a_minus_b"], 0)
        self.assertEqual(comparison["disagreement_rate"], 2 / 3)
        self.assertEqual(b["classification"]["accuracy"], 1)
        self.assertEqual(metrics["common_cohort"]["n"], 3)
        self.assertEqual(len(errors["evaluator_outcomes"]), 3)
        self.assertEqual(len(errors["disagreements"]), 2)

    def test_asr_difference_sign_and_paired_denominator(self):
        rows = [r for r in self.predictions if (r["case_id"], r["validator_id"]) != ("CASE-003", "VAL-B")]
        metrics, _ = analyze(self.manifest, self.cases, rows, self.labels)
        pair = metrics["evaluator_comparisons"][0]
        self.assertEqual(pair["n"], 2)
        self.assertEqual(pair["asr_difference_pp_a_minus_b"], 50)
        self.assertEqual(metrics["evaluators"]["VAL-B"]["coverage"]["missing"], 1)

    def test_undefined_metrics_and_f1_zero_are_distinct(self):
        empty = confusion_metrics([])
        for key in ("accuracy", "precision", "recall", "f1", "false_positive_rate", "false_negative_rate", "mcc"):
            self.assertIsNone(empty[key])
        all_negative = confusion_metrics([(0, 0), (0, 0)])
        self.assertEqual(all_negative["accuracy"], 1)
        self.assertIsNone(all_negative["precision"])
        self.assertIsNone(all_negative["f1"])
        self.assertEqual(all_negative["false_positive_rate"], 0)
        only_misses = confusion_metrics([(1, 0), (1, 0)])
        self.assertEqual(only_misses["f1"], 0)
        self.assertEqual(only_misses["false_negative_rate"], 1)
        self.assertIsNone(only_misses["false_positive_rate"])

    def test_no_predictions_or_labels_is_unknown_not_zero(self):
        validate_rows([], [], self.cases, self.manifest)
        metrics, errors = analyze(self.manifest, self.cases, [], [])
        for item in metrics["evaluators"].values():
            self.assertEqual(item["coverage"]["missing"], 4)
            self.assertIsNone(item["asr"]["rate"])
            self.assertIsNone(item["classification"]["accuracy"])
            self.assertEqual(item["asr"]["lower_bound_all_cases"], 0)
            self.assertEqual(item["asr"]["upper_bound_all_cases"], 1)
        self.assertEqual(len(errors["reference_exclusions"]), 4)

    def test_indeterminate_is_distinct_from_error_and_negative(self):
        self.predictions[-1].update(status="indeterminate", error_type="")
        validate_rows(self.predictions, self.labels, self.cases, self.manifest)
        metrics, errors = analyze(self.manifest, self.cases, self.predictions, self.labels)
        item = metrics["evaluators"]["VAL-B"]
        self.assertEqual(item["coverage"]["indeterminate"], 1)
        self.assertEqual(item["coverage"]["errors"], 0)
        self.assertEqual(item["classification"]["confusion_matrix"]["fn"], 0)
        self.assertEqual(errors["evaluator_outcomes"][-1]["category"], "indeterminate")

    def test_uncertain_labels_do_not_become_ground_truth(self):
        self.labels[1].update(label="", status="uncertain", annotator_ids="")
        self.labels.pop()
        validate_rows(self.predictions, self.labels, self.cases, self.manifest)
        metrics, errors = analyze(self.manifest, self.cases, self.predictions, self.labels)
        self.assertEqual(metrics["evaluators"]["VAL-A"]["classification"]["n"], 2)
        self.assertEqual(metrics["evaluators"]["VAL-A"]["asr"]["denominator"], 4)
        self.assertEqual([r["status"] for r in errors["reference_exclusions"]], ["uncertain", "missing"])
        self.labels[1]["label"] = "0"
        with self.assertRaisesRegex(ContractError, "unresolved labels"):
            validate_rows(self.predictions, self.labels, self.cases, self.manifest)

    def test_split_leakage_all_group_types_and_task(self):
        for field in ("base_intent_id", "prompt_family_id", "duplicate_group_id", "response_sha256", "task_id"):
            with self.subTest(field=field):
                dataset = copy.deepcopy(self.dataset)
                dataset["cases"][-1][field] = dataset["cases"][0][field]
                if field == "task_id":
                    dataset["cases"][-1]["attempt_id"] = "another-attempt"
                with self.assertRaisesRegex(ContractError, "split leakage"):
                    validate_dataset(dataset)

    def test_unknown_and_duplicate_prediction_keys_and_wrong_split(self):
        for mutation in ({"case_id": "CASE-005"}, {"case_id": "unknown"}, {"validator_id": "unknown"}):
            rows = copy.deepcopy(self.predictions)
            rows[0].update(mutation)
            with self.subTest(mutation=mutation), self.assertRaises(ContractError):
                validate_rows(rows, self.labels, self.cases, self.manifest)
        with self.assertRaisesRegex(ContractError, "duplicate prediction"):
            validate_rows(self.predictions + self.predictions[:1], self.labels, self.cases, self.manifest)
        self.labels[0]["case_id"] = "CASE-005"
        with self.assertRaisesRegex(ContractError, "wrong-split"):
            validate_rows(self.predictions, self.labels, self.cases, self.manifest)

    def test_label_integrity(self):
        mutations = ({"annotator_ids": "reviewer"}, {"annotator_ids": "a|a"},
                     {"label": "true"}, {"label": ""}, {"status": "adjudicated"},
                     {"evidence_ref": ""})
        for mutation in mutations:
            labels = copy.deepcopy(self.labels)
            labels[0].update(mutation)
            with self.subTest(mutation=mutation), self.assertRaises(ContractError):
                validate_rows(self.predictions, labels, self.cases, self.manifest)
        with self.assertRaisesRegex(ContractError, "duplicate label"):
            validate_rows(self.predictions, self.labels + self.labels[:1], self.cases, self.manifest)

    def test_fx_and_f5_endpoint_semantics(self):
        for mutation in ({"status": "ok", "predicted_success": "0"}, {"predicted_success": "0"}):
            rows = copy.deepcopy(self.predictions)
            rows[-1].update(mutation)
            with self.subTest(mutation=mutation), self.assertRaises(ContractError):
                validate_rows(rows, self.labels, self.cases, self.manifest)
        self.manifest["validators"][0]["success_construct"] = "F5"
        self.predictions[0]["functional_level"] = "F3"
        with self.assertRaisesRegex(ContractError, "F5 endpoint"):
            validate_rows(self.predictions, self.labels, self.cases, self.manifest)
        self.predictions[0]["functional_level"] = "F5"
        validate_rows(self.predictions, self.labels, self.cases, self.manifest)

    def test_invalid_scores_json_and_csv(self):
        for value in ("NaN", "inf", "1e999", "-0.1", "1.01", "banana"):
            self.predictions[0]["score"] = value
            with self.subTest(value=value), self.assertRaises(ContractError):
                validate_rows(self.predictions, self.labels, self.cases, self.manifest)
        for raw in (b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":1e999}', b'broken'):
            with self.subTest(raw=raw), self.assertRaises(ContractError):
                load_json(raw, "test")
        for raw in (b'case_id,case_id\nx,y\n', b'case_id\nx\n', self.inputs["predictions.csv"] + b'x,y\n'):
            with self.subTest(raw=raw[:30]), self.assertRaises(ContractError):
                load_csv(raw, PREDICTION_COLUMNS, "test")

    def test_test_split_requires_frozen_protocol_and_matching_hash(self):
        for key, value in (("purpose", "development"), ("code_commit", "main"), ("experiment_id", "../EXP-001"), ("run_id", "../../escape")):
            manifest = copy.deepcopy(self.manifest)
            manifest[key] = value
            with self.subTest(key=key), self.assertRaises(ContractError):
                validate_manifest(manifest, self.dataset, digest(self.inputs["dataset_manifest.json"]))
        for frozen in (None, "2026-09-09T00:00:00Z", "2026-09-08T00:00:00"):
            self.manifest["protocol"]["frozen_at"] = frozen
            with self.subTest(frozen=frozen), self.assertRaises(ContractError):
                validate_manifest(self.manifest, self.dataset, digest(self.inputs["dataset_manifest.json"]))
        self.manifest = load_json(self.paths[0].read_bytes(), "manifest")
        with self.assertRaisesRegex(ContractError, "SHA-256 mismatch"):
            validate_manifest(self.manifest, self.dataset, "f" * 64)

    def test_balanced_attack_rank_reversal_and_ties(self):
        rows = copy.deepcopy(self.predictions)
        for row in rows:
            odd = int(row["case_id"][-1]) % 2
            row.update(status="ok", error_type="", functional_level="",
                       predicted_success=str(odd if row["validator_id"] == "VAL-A" else 1 - odd))
        metrics, _ = analyze(self.manifest, self.cases, rows, self.labels)
        ranks = metrics["rankings"]["attack_method_id"]
        self.assertEqual(ranks["status"], "descriptive")
        self.assertEqual(ranks["by_evaluator"]["VAL-A"][0]["condition_id"], "METHOD-A")
        self.assertEqual(ranks["by_evaluator"]["VAL-B"][0]["condition_id"], "METHOD-B")
        self.assertEqual(ranks["rank_changes"][0]["conditions"][0]["rank_difference_a_minus_b"], -1)
        for row in rows:
            row["predicted_success"] = "1"
        metrics, _ = analyze(self.manifest, self.cases, rows, self.labels)
        self.assertEqual([r["rank"] for r in metrics["rankings"]["attack_method_id"]["by_evaluator"]["VAL-A"]], [1, 1])

    def test_model_rankings_and_unfair_comparisons_are_suppressed(self):
        cases = copy.deepcopy(self.cases)
        for case in cases:
            case["model_id"], case["attack_method_id"] = case["attack_method_id"], case["model_id"]
        rows = copy.deepcopy(self.predictions)
        rows[-1].update(status="ok", predicted_success="1", error_type="", functional_level="")
        metrics, _ = analyze(self.manifest, cases, rows, self.labels)
        self.assertEqual(metrics["rankings"]["model_id"]["status"], "descriptive")
        metrics, _ = analyze(self.manifest, self.cases, self.predictions, self.labels)
        self.assertEqual(metrics["rankings"]["attack_method_id"]["reason"], "incomplete_evaluator_coverage")
        cases = copy.deepcopy(self.cases)
        cases[0]["task_id"] = "different-task"
        metrics, _ = analyze(self.manifest, cases, rows, self.labels)
        self.assertEqual(metrics["rankings"]["attack_method_id"]["reason"], "unbalanced_condition_grid")

    def test_record_bundle_preserves_bytes_and_refuses_overwrite(self):
        run = self.record()
        self.assertEqual({p.name for p in run.iterdir()}, {"manifest.json", "dataset_manifest.json", "predictions.csv", "human_labels.csv", "metrics.json", "errors.json", "canonical_inputs.json"})
        for name, raw in self.inputs.items():
            self.assertEqual((run / name).read_bytes(), raw)
        verify_run(run)
        before = {p.name: p.read_bytes() for p in run.iterdir()}
        with self.assertRaisesRegex(ContractError, "already exists"):
            self.record()
        self.assertEqual(before, {p.name: p.read_bytes() for p in run.iterdir()})

    def test_observation_tuple_and_quoted_evidence_survive_import(self):
        self.predictions[0].update(r="1", h="0", f="0", q="0.75", e="0", score="0.25",
                                   functional_level="F2", evidence_ref='synthetic:quoted,"line"\nnext')
        buffer = io.StringIO(newline="")
        writer = csv.DictWriter(buffer, fieldnames=PREDICTION_COLUMNS, lineterminator="\r\n")
        writer.writeheader()
        writer.writerows(self.predictions)
        raw = buffer.getvalue().encode("utf-8")
        predictions_path = self.root / "input.csv"
        predictions_path.write_bytes(raw)
        run = record_run(*self.paths[:2], predictions_path, self.paths[3], self.root / "results" / "runs")
        self.assertEqual((run / "predictions.csv").read_bytes(), raw)
        verify_run(run)

    def test_tampering_rejected_even_if_output_hash_is_rewritten(self):
        run = self.record()
        path = run / "metrics.json"
        metric = load_json(path.read_bytes(), "metric")
        metric["evaluators"]["VAL-A"]["classification"]["accuracy"] = 1
        raw = json_bytes(metric)
        path.write_bytes(raw)
        with self.assertRaisesRegex(ContractError, "hash/size mismatch"):
            verify_run(run)
        saved = load_json((run / "manifest.json").read_bytes(), "manifest")
        saved["artifacts"]["metrics.json"] = {"sha256": digest(raw), "size_bytes": len(raw)}
        (run / "manifest.json").write_bytes(json_bytes(saved))
        with self.assertRaisesRegex(ContractError, "does not reproduce"):
            verify_run(run)

    def test_web_rebuild_is_deterministic_aggregate_only_and_synthetic_opt_in(self):
        self.record()
        path = self.root / "website.json"
        empty = rebuild_web(self.root / "results" / "runs", path)
        self.assertEqual(empty["readiness"]["runs"], 0)
        self.assertEqual(empty["runs"], [])
        result = rebuild_web(self.root / "results" / "runs", path, include_synthetic=True)
        self.assertEqual(len(result["runs"]), 1)
        self.assertTrue(all(r["record_kind"] == "synthetic" for r in result["runs"]))
        raw = path.read_bytes()
        self.assertNotIn(b'"case_ids"', raw)
        self.assertNotIn(b'"annotator_ids"', raw)
        self.assertNotIn(b'"evidence_ref"', raw)
        self.assertNotIn(b'"parameters"', raw)
        rebuild_web(self.root / "results" / "runs", path, include_synthetic=True)
        self.assertEqual(raw, path.read_bytes())

    def test_ablation_metadata_survives_without_pooled_results(self):
        manifest = copy.deepcopy(self.manifest)
        manifest["ablation"] = {"study_id": "ABL-TEST", "variant_id": "without-test-feature", "components": ["synthetic-check"]}
        new_manifest = self.root / "input.json"
        new_manifest.write_bytes(json_bytes(manifest))
        record_canonical(new_manifest, *self.paths[1:], self.root / "results" / "runs", self.root / "registries", self.root)
        result = rebuild_web(self.root / "results" / "runs", self.root / "web.json", True)
        self.assertEqual(result["runs"][0]["experiment"]["ablation"], manifest["ablation"])
        self.assertNotIn("pooled_asr", result)

    def test_failed_export_preserves_previous_file_and_rejects_incomplete_run(self):
        run = self.record()
        path = self.root / "web.json"
        rebuild_web(self.root / "results" / "runs", path)
        original = path.read_bytes()
        (run / "predictions.csv").unlink()
        with self.assertRaisesRegex(ContractError, "incomplete"):
            rebuild_web(self.root / "results" / "runs", path)
        self.assertEqual(path.read_bytes(), original)

    def test_cross_run_dataset_version_conflict(self):
        self.record()
        self.dataset["provenance"]["transformations"].append("A second synthetic metadata revision")
        dataset_path = self.root / "dataset.json"
        dataset_path.write_bytes(json_bytes(self.dataset))
        self.manifest["dataset"]["sha256"] = digest(dataset_path.read_bytes())
        self.manifest["run_id"] = "RUN-SAFE-TEST-002"
        manifest_path = self.root / "manifest.json"
        manifest_path.write_bytes(json_bytes(self.manifest))
        with self.assertRaisesRegex(ValueError, "unversioned change"):
            record_canonical(manifest_path, dataset_path, *self.paths[2:], self.root / "results" / "runs", self.root / "registries", self.root)

    def test_cross_version_split_reassignment_rejected(self):
        self.record()
        self.dataset["version"] = "test-2"
        for case in self.dataset["cases"]:
            case["split"] = "development" if case["split"] == "test" else "test"
        dataset_path = self.root / "dataset.json"
        dataset_path.write_bytes(json_bytes(self.dataset))
        self.manifest["dataset"].update(sha256=digest(dataset_path.read_bytes()), version="test-2")
        self.manifest.update(run_id="RUN-SAFE-TEST-002", split="development", purpose="development")
        manifest_path = self.root / "manifest.json"
        manifest_path.write_bytes(json_bytes(self.manifest))
        self.manifest['config_version'] = 'test-2'
        self.manifest['created_at'] = '2026-09-09T01:00:00Z'
        self.dataset['provenance']['retrieved_at'] = '2026-09-09T00:00:00Z'
        dataset_path.write_bytes(json_bytes(self.dataset))
        self.manifest['dataset']['sha256'] = digest(dataset_path.read_bytes())
        manifest_path.write_bytes(json_bytes(self.manifest))
        with self.assertRaisesRegex(ValueError, "split leakage"):
            record_canonical(manifest_path, dataset_path, *self.paths[2:], self.root / "results" / "runs", self.root / "registries", self.root)

    def test_invalid_record_does_not_publish_partial_directory(self):
        self.manifest["dataset"]["sha256"] = "f" * 64
        manifest_path = self.root / "manifest.json"
        manifest_path.write_bytes(json_bytes(self.manifest))
        with self.assertRaises(ContractError):
            record_run(manifest_path, *self.paths[1:], self.root / "results" / "runs")
        self.assertFalse((self.root / "results" / "runs").exists())

    def test_web_output_cannot_overwrite_run_inputs(self):
        run = self.record()
        original = (run / "manifest.json").read_bytes()
        with self.assertRaisesRegex(ValueError, "immutable artifacts"):
            rebuild_web(self.root / "results" / "runs", run / "manifest.json")
        self.assertEqual((run / "manifest.json").read_bytes(), original)

    def test_run_id_directory_mismatch_and_symlink_rejected(self):
        run = self.record()
        other = run.with_name("RUN-OTHER")
        run.rename(other)
        with self.assertRaisesRegex(ContractError, "run_id mismatch"):
            verify_run(other)
        try:
            run.symlink_to(other, target_is_directory=True)
        except OSError:
            self.skipTest("symlinks unavailable on this platform")
        with self.assertRaisesRegex(ContractError, "invalid run directory"):
            verify_run(run)

    def test_cli_from_outside_checkout_and_nonzero_error_exit(self):
        command = [sys.executable, str(ROOT / "scripts" / "experiment.py")]
        args = ["record", "--manifest", str(self.paths[0]), "--dataset", str(self.paths[1]),
                "--predictions", str(self.paths[2]), "--labels", str(self.paths[3]),
                "--runs-dir", str(self.root / "results" / "runs")]
        recorded = subprocess.run(command + args, cwd=self.root, capture_output=True, text=True)
        self.assertEqual(recorded.returncode, 0, recorded.stderr)
        failed = subprocess.run(command + args, cwd=self.root, capture_output=True, text=True)
        self.assertEqual(failed.returncode, 1)
        self.assertIn("already exists", failed.stderr)
        exported = subprocess.run(command + ["rebuild-web", "--runs-dir", str(self.root / "results" / "runs"),
                                           "--output", str(self.root / "web.json")], cwd=self.root, capture_output=True, text=True)
        self.assertEqual(exported.returncode, 0, exported.stderr)


if __name__ == "__main__":
    unittest.main()
