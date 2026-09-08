# Data policy

This public repository should version data **manifests, provenance, labels, and safe derived artefacts** rather than blindly copying every external dataset or raw executable output.

Recommended layout:

```text
data/
├── manifests/        # source, version, licence, retrieval metadata
├── human_labels/     # annotation files and adjudicated ground truth
├── derived/          # safe transformed data used for analysis
└── raw/              # local-only by default; ignored by git
```

For every external benchmark, record its original source and redistribution terms.

Canonical dataset and benchmark metadata now lives in `registries/datasets.json`
and `registries/benchmarks.json`; human-label records live in
`registries/human_labels.json`. The directories above are artefact locations, not
independent metadata databases. Record manifests, checksums, source versions,
licensing/redistribution status, retrieval timestamps and transformations there.
`null` means unknown/unavailable, never permission or a negative observation.
See `docs/REGISTRIES.md` before adding records or publishing labels.
