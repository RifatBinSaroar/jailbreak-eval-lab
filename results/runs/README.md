# Immutable local run bundles

Use `python scripts/experiment.py record` with existing capture inputs. The command never calls
models or executes generated code. See [the run guide](../../docs/EXPERIMENT_FRAMEWORK.md).

Every bundle includes manifest.json, canonical_inputs.json, dataset_manifest.json, predictions.csv,
human_labels.csv, metrics.json and errors.json. The recorder also appends canonical registry records.
Do not edit a bundle; corrections require a new run ID. `verify` checks its integrity and arithmetic;
`sync` can recover canonical registration. The canonical web build also checks registry equality.

Run folders are ignored by Git by default. Keep exact local bundles when retaining registered results.
Their deliberate public release is a separate review decision. No real runs are committed here.
