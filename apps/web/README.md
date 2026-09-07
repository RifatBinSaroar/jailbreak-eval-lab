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
