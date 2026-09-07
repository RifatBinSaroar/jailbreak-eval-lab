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
