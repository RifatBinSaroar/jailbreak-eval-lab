# Web application

The web interface is a first-class research interface, not a decorative landing page.

It should eventually expose:

- Home / research overview
- Run Evaluation
- Experiments
- Datasets
- Validators
- Results
- Visualisations
- Reports
- Documentation
- Papers & References

## Design direction

The approved visual direction is a polished research dashboard with:

- dark navy left navigation
- bright, spacious main workspace
- soft blue / purple / green accent cards
- strong typography and restrained shadows
- metric cards and comparison charts
- recent experiment panels
- literature and documentation views

The website must read structured repository artefacts. Do not hard-code unverified research claims or fake metrics into production views.

## Development sequence

1. Build the visual shell and navigation.
2. Connect literature records.
3. Connect experiment/result artefacts.
4. Add evaluator comparison views.
5. Add safe interactive evaluation only after the backend contract is stable.

## Available data contract

From the repository root, build the validated production projection:

```bash
python -m jailbreak_eval.registry export-web --output apps/web/dist/research-data.json
```

Read `readiness`, `papers`, `verified_paper_evidence` and `metrics` from that JSON.
There are currently no research records: completed experiments are zero and the
metrics array is empty. An empty array means no recorded measurements, not zero
ASR or zero error. Do not substitute demo metrics. Templates cannot pass this
export path.

Every metric includes result, run, experiment, validator, code and artefact-hash
references. Resolve these against the canonical snapshot identified by
`registry_sha256`. Keep paper evidence, interpretation and open questions
visually separate, with sources and verification states visible. See
`docs/REGISTRIES.md` for artefact verification and publication review.
This PR supplies the data contract; it does not deploy or change a UI.
