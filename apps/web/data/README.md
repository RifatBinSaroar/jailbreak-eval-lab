# Generated canonical data

Only `research.json` belongs here. Rebuild it from the repository root:

```text
python scripts/research.py build-web
```

It is a projection of the nine canonical registries with contract `research-platform/0.1`.
Do not edit it by hand. The importer and recorder write canonical records; they do not publish
separate website schemas. The build validates literature intake checksums, verifies immutable runs,
reproduces their analysis and checks canonical equality before writing this file atomically.

`papers`, `validators`, `benchmarks`, `domains`, `datasets`, `experiments`, `runs` and aggregate
`results` use canonical field names and IDs. Individual human labels, raw predictions/cases and
config parameters are omitted. Readiness counts, evidence projections, duplicate candidates and
novelty/open-question cards are derived from the same registries. Source artifacts remain linked.

Initial production data contains 47 listed entries, 7 planned validator candidates, 3 benchmark
candidates and 3 domain/subdomain entries. Experiments/runs/results remain empty. No literature
findings, measured performance or novelty conclusion is invented.
