"""Deterministic descriptive metrics on explicit, paired case sets."""

from collections import Counter
from itertools import combinations
from math import sqrt


ANALYSIS_VERSION = "1.0"


def ratio(numerator, denominator):
    return numerator / denominator if denominator else None


def confusion_metrics(pairs):
    """Pairs are (human truth, evaluator prediction); 1 means success."""
    counts = Counter(pairs)
    tp, tn, fp, fn = (counts[key] for key in ((1, 1), (0, 0), (0, 1), (1, 0)))
    n = tp + tn + fp + fn
    return {
        "n": n,
        "confusion_matrix": {"tp": tp, "tn": tn, "fp": fp, "fn": fn},
        "accuracy": ratio(tp + tn, n),
        "precision": ratio(tp, tp + fp),
        "recall": ratio(tp, tp + fn),
        "f1": ratio(2 * tp, 2 * tp + fp + fn),
        "false_positive_rate": ratio(fp, fp + tn),
        "false_negative_rate": ratio(fn, fn + tp),
        "specificity": ratio(tn, tn + fp),
        "mcc": ratio(tp * tn - fp * fn, sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))),
    }


def asr_summary(values, expected):
    n, successes = len(values), sum(values)
    return {
        "successes": successes, "denominator": n, "expected": expected,
        "unresolved": expected - n, "coverage": ratio(n, expected),
        "rate": ratio(successes, n),
        "lower_bound_all_cases": ratio(successes, expected),
        "upper_bound_all_cases": ratio(successes + expected - n, expected),
    }


def paired_summary(a, b):
    common = sorted(a.keys() & b.keys())
    n = len(common)
    a_successes, b_successes = sum(a[c] for c in common), sum(b[c] for c in common)
    return {
        "n": n, "case_ids": common,
        "a_successes": a_successes, "b_successes": b_successes,
        "a_asr": ratio(a_successes, n), "b_asr": ratio(b_successes, n),
        "asr_difference_pp_a_minus_b": ratio(100 * (a_successes - b_successes), n),
        "disagreements": sum(a[c] != b[c] for c in common),
        "disagreement_rate": ratio(sum(a[c] != b[c] for c in common), n),
        "a_positive_b_negative": sum(a[c] == 1 and b[c] == 0 for c in common),
        "a_negative_b_positive": sum(a[c] == 0 and b[c] == 1 for c in common),
    }


def summarize_cohort(case_ids, validators, predictions, truth):
    expected = len(case_ids)
    output = {}
    for validator_id in validators:
        rows = {case: predictions[(case, validator_id)] for case in case_ids if (case, validator_id) in predictions}
        decided = {case: int(row["predicted_success"]) for case, row in rows.items() if row["status"] == "ok"}
        reference = {case: truth[case] for case in case_ids if case in truth}
        matched = sorted(decided.keys() & reference.keys())
        output[validator_id] = {
            "coverage": {
                "expected": expected, "received": len(rows), "determinate": len(decided),
                "missing": expected - len(rows),
                "indeterminate": sum(r["status"] == "indeterminate" for r in rows.values()),
                "errors": sum(r["status"] == "error" for r in rows.values()),
                "human_resolved": len(reference), "human_unresolved_or_missing": expected - len(reference),
                "paired_with_human": len(matched),
            },
            "classification": confusion_metrics([(reference[c], decided[c]) for c in matched]),
            "asr": asr_summary(list(decided.values()), expected),
            "versus_human": paired_summary(decided, reference),
        }
    return output


def rankings(cases, validators, decisions, dimension):
    """Only rank balanced, completely observed matched task/attempt blocks.

    Different model/attack mixes, missing predictions, or FX suppress ranks.
    The result is descriptive; it makes no claim of statistical significance.
    """
    other = "model_id" if dimension == "attack_method_id" else "attack_method_id"
    entities = sorted({c[dimension] for c in cases})
    base = {"dimension": dimension, "status": "unavailable", "reason": None,
            "by_evaluator": {}, "rank_changes": []}
    if len(entities) < 2:
        return {**base, "reason": "fewer_than_two_conditions"}
    units = {entity: {} for entity in entities}
    for case in cases:
        units[case[dimension]][(case["task_id"], case["attempt_id"], case[other])] = case["case_id"]
    grid = set(units[entities[0]])
    if any(set(units[entity]) != grid for entity in entities):
        return {**base, "reason": "unbalanced_condition_grid"}
    if any(case["case_id"] not in decisions[v] for case in cases for v in validators):
        return {**base, "reason": "incomplete_evaluator_coverage"}
    result = {**base, "status": "descriptive", "reason": None, "blocks_per_condition": len(grid)}
    rank_maps = {}
    for v in validators:
        totals = {entity: sum(decisions[v][cid] for cid in units[entity].values()) for entity in entities}
        rank_maps[v] = {entity: 1 + sum(total > totals[entity] for total in totals.values()) for entity in entities}
        result["by_evaluator"][v] = [
            {"condition_id": entity, "successes": totals[entity], "denominator": len(grid),
             "asr": ratio(totals[entity], len(grid)), "rank": rank_maps[v][entity]}
            for entity in sorted(entities, key=lambda e: (-totals[e], e))
        ]
    for a, b in combinations(validators, 2):
        result["rank_changes"].append({
            "evaluator_a": a, "evaluator_b": b,
            "conditions": [{"condition_id": entity, "rank_a": rank_maps[a][entity],
                            "rank_b": rank_maps[b][entity],
                            "rank_difference_a_minus_b": rank_maps[a][entity] - rank_maps[b][entity]}
                           for entity in entities],
        })
    return result


def analyze(manifest, cases, prediction_rows, label_rows):
    validators = sorted(v["validator_id"] for v in manifest["validators"])
    predictions = {(r["case_id"], r["validator_id"]): r for r in prediction_rows}
    truth = {r["case_id"]: int(r["label"]) for r in label_rows if r["status"] in ("consensus", "adjudicated")}
    case_ids = sorted(c["case_id"] for c in cases)
    decisions = {v: {cid: int(predictions[(cid, v)]["predicted_success"]) for cid in case_ids
                     if (cid, v) in predictions and predictions[(cid, v)]["status"] == "ok"} for v in validators}
    common = sorted(set(case_ids).intersection(*(set(decisions[v]) for v in validators)))
    metrics = {
        "schema_version": "1.0", "analysis_version": ANALYSIS_VERSION,
        "experiment_id": manifest["experiment_id"], "run_id": manifest["run_id"],
        "split": manifest["split"], "record_kind": manifest["record_kind"],
        "definitions": {
            "positive_label": "success under the explicitly recorded construct",
            "confusion_matrix": "human rows / evaluator columns; tp=(1,1), tn=(0,0), fp=(0,1), fn=(1,0)",
            "asr": "successes / determinate predictions; report coverage and all-case bounds",
            "asr_bounds": "identification bounds treating every unresolved item as failure or success; not confidence intervals",
            "asr_difference": "percentage points; evaluator A minus evaluator B on the same determinate cases",
            "classification": "resolved human labels intersected with determinate predictions",
            "undefined": "null when a denominator is zero; never replace with zero",
            "ranking": "descending ASR with competition ties, balanced task/attempt/other-condition grid; descriptive only",
        },
        "human_reference_asr": asr_summary(list(truth.values()), len(case_ids)),
        "evaluators": summarize_cohort(case_ids, validators, predictions, truth),
        "common_cohort": {
            "n": len(common), "case_ids": common,
            "evaluators": summarize_cohort(common, validators, predictions, truth),
        },
        "evaluator_comparisons": [], "groups": [],
        "rankings": {dim: rankings(cases, validators, decisions, dim) for dim in ("model_id", "attack_method_id")},
        "ablation": manifest["ablation"],
    }
    for a, b in combinations(validators, 2):
        metrics["evaluator_comparisons"].append({
            "evaluator_a": a, "evaluator_b": b, **paired_summary(decisions[a], decisions[b]),
        })
    for dimensions in (("model_id",), ("attack_method_id",), ("model_id", "attack_method_id")):
        groups = {}
        for case in cases:
            groups.setdefault(tuple(case[d] for d in dimensions), []).append(case["case_id"])
        for key in sorted(groups):
            ids = sorted(groups[key])
            metrics["groups"].append({
                "condition": dict(zip(dimensions, key)), "case_ids": ids,
                "evaluators": summarize_cohort(ids, validators, predictions, truth),
                "evaluator_comparisons": [
                    {"evaluator_a": a, "evaluator_b": b,
                     **paired_summary({c: decisions[a][c] for c in ids if c in decisions[a]},
                                      {c: decisions[b][c] for c in ids if c in decisions[b]})}
                    for a, b in combinations(validators, 2)
                ],
            })
    label_index = {r["case_id"]: r for r in label_rows}
    errors = {"schema_version": "1.0", "run_id": manifest["run_id"],
              "evaluator_outcomes": [], "reference_exclusions": [], "disagreements": []}
    for cid in case_ids:
        if cid not in truth:
            errors["reference_exclusions"].append({"case_id": cid, "status": label_index[cid]["status"] if cid in label_index else "missing"})
        for v in validators:
            row = predictions.get((cid, v))
            category = None
            if row is None:
                category = "missing_prediction"
            elif row["status"] != "ok":
                category = row["status"]
            elif cid in truth and int(row["predicted_success"]) != truth[cid]:
                category = "false_positive" if row["predicted_success"] == "1" else "false_negative"
            if category:
                errors["evaluator_outcomes"].append({
                    "case_id": cid, "validator_id": v, "category": category,
                    "error_type": row["error_type"] if row else None,
                    "evidence_ref": row["evidence_ref"] if row else None,
                })
        for a, b in combinations(validators, 2):
            if cid in decisions[a] and cid in decisions[b] and decisions[a][cid] != decisions[b][cid]:
                errors["disagreements"].append({"case_id": cid, "evaluator_a": a, "evaluator_b": b,
                                               "prediction_a": decisions[a][cid], "prediction_b": decisions[b][cid]})
    return metrics, errors
