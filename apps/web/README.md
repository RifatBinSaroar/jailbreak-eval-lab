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

## Literature data contract

The Python importer now generates `public/data/literature.json` from
`literature/registry.json`. Run `python scripts/literature.py export --replace`
from the repository root after installing the literature dependencies.
No npm or running website is required for this data workflow.

The JSON contains `schema_version`, `records`, `duplicate_candidates` and
`summary`. Each paper includes review stage, missing fields, source links,
original source cells and separate evidence/interpretation/question buckets.
The initial 37 supplied titles are unreviewed and incomplete. Show that status
clearly; `null` is unknown, not negative evidence. Field-level verification
does not verify an entire record. Treat raw cell strings as text, not HTML.

See the [full contract](../../literature/README.md) and
[Python-only quickstart](../../docs/LITERATURE_QUICKSTART.md).

## Development sequence

1. Build the visual shell and navigation.
2. Connect literature records.
3. Connect experiment/result artefacts.
4. Add evaluator comparison views.
5. Add safe interactive evaluation only after the backend contract is stable.
