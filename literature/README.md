# Literature workflow

The canonical records are `registries/papers.json`. `literature/intake/` contains immutable,
source-hashed row/cell provenance linked from those records, not a competing paper schema.
The user's source XLSX is not committed.

```text
python scripts/literature.py import "literature/my-matrix.xlsx"
python scripts/research.py validate
python scripts/research.py build-web
```

Use [the easy guide](../docs/PLATFORM_QUICKSTART.md) and
[the review format](../docs/LITERATURE_QUICKSTART.md). Intake is listed. Explicit source-linked
curator revisions can advance review under the same paper ID. Duplicate candidates are never
silently merged. Novelty is never inferred from missing literature.
