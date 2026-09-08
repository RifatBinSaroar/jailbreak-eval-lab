# Research Platform v0.1 integration handoff

This is an integration-only change on `feat/research-platform-v0.1-integration`, created from
current `main` at `9f673eadaa2b2364aa08f4cb4d2462e566ac7f80`. No source PR was merged.
No model calls, jailbreak experiments or main experiment were run. Automated recordings use
safe synthetic decisions, with no operational malicious payloads.

Start with [PLATFORM_QUICKSTART.md](PLATFORM_QUICKSTART.md): Python, Git, VS Code and Live Server
are sufficient. No npm or frontend build is needed.

## Reconciliation of existing work

| Source | Preserved | Changed or superseded |
| --- | --- | --- |
| PR #3 — data-driven dashboard | Eight views; dark navy sidebar and bright workspace; responsive and keyboard navigation; literature search/filtering; source links; evidence/interpretation/question separation; synthesis reading queue | Reader and views consume one canonical export. Separate website JSON registries, provisional WEB identities and website-specific scientific fields are superseded. Ten synthesis reading candidates remain separate canonical listings with traceable provenance. |
| PR #4 — experiment/run framework | Immutable bundles; input and code checksums; predictions and human references; confusion metrics, ASR comparisons and bounds; errors, disagreement, descriptive rankings, grouping and ablations; strongest arithmetic and tampering tests | Existing capture files are transport inputs to canonical dataset/validator/experiment/run/label/result records. Adds pilot isolation, protocol version/freeze guards, sealed canonical snapshots and export replay. Separate experiment/result web exports are superseded. Formula denominators and paired cohort sizes are represented separately. |
| PR #5 — literature ingestion | XLSX/CSV/TSV/JSON/JSONL and structured notes; every source column/cell, formula, hyperlink and source hash; sheet/row provenance; conservative duplicate candidates; 37 existing workbook titles | Intake maps to canonical `listed`, with immutable sidecars. Explicit review revisions append under the same stable ID. Raw matrix claims never become evidence. The importer-specific paper schema, `unreviewed` state, rebuild-from-scratch records and web exporter are superseded. The user's source XLSX is not committed. |
| PR #6 — canonical registries | Nine-registry architecture; namespaced identity, schema validation, pinned provenance and separate templates; strongest structural validation tests | Same-ID immutable revisions replace the rule requiring a new identity for every change. History checks inspect every intervening commit. Extends experiment capture, pilot/final protocols, external validator provenance and human-review attestations. Screened/deep-reviewed extraction is visible with its actual status; verified-only evidence filtering is superseded. |

The existing `web-v0.1-static` lineage and its project synthesis remain the basis for the
dashboard's visual direction and explicitly labelled research questions, not measured findings.

Source snapshots reconciled:

| Source | Commit |
| --- | --- |
| PR #3 / `feat/data-driven-research-dashboard` | `b5558a86fe6350c0a4fb78ac38d7d85ecbee97ce` |
| PR #4 / `feat/experiment-run-framework` | `27b06989dff0b7214f60b654244e60aad5850683` |
| PR #5 / `feat/literature-ingestion-pipeline` | `4134fd69b018d4543fbd92b99bd24222ef9a7309` |
| PR #6 / `feat/canonical-research-registries` | `1c0a6da638247abb0ebe6f12be4262e2135b6b68` |
| Existing web/synthesis lineage | `108e3cb9d74d844c909f74f227a7d1ba40a7c3a9` |

## Resulting workflows

1. Excel or structured notes → Python importer → canonical paper revisions plus intake sidecars
   → canonical web exporter → dashboard.
2. Outputs collected locally elsewhere → offline recorder → immutable run bundle → canonical
   run/label/result registries → reproduced metrics/error analysis → canonical web exporter
   → dashboard.

`python scripts/research.py build-web` is the single build path. Compatibility aliases call the
same exporter. The site only loads `apps/web/data/research.json`; it defines no scientific records.
Measured metrics are reproduced from registered bundles before export. Templates are rejected
from production; synthetic records are excluded by default and visibly labelled when explicitly
included for testing. There are currently zero production experiments and zero measured results.

## Scientific-impact review (AGENTS.md rule 9)

These changes affect representation and eligibility and need explicit reviewer attention:

- A paper's review state and extracted claims require a new version, later timestamp and current
  review provenance. Listed intake has no paper evidence. Novelty states remain manual; missing
  literature never establishes novelty.
- Existing PR #4 metric arithmetic and binary success decisions are preserved. No new success
  threshold is introduced. FX, indeterminate, errors and missing predictions remain outside
  binary decisions; undefined metrics stay null. F1/MCC formula denominators are distinct from
  the number of paired cases.
- Imported human CSVs preserve the stated unresolved/consensus/adjudicated status as an
  attestation. They do not fabricate individual votes. Unresolved references are excluded from
  classification metrics. Native adjudication still needs independent annotations.
- Pilot, development and test remain distinct across dataset revisions and aliases. Final-test
  captures require a frozen protocol; its version binds the captured methods and configuration.
  Experiments support the actual model/attack arrays rather than inventing one representative.
- External validator decisions are labelled `external_recorded`, with captured configuration
  provenance. Recording decisions does not certify a validator implementation.

## Verification and limits

The local release gate runs Python integration/regression tests, 15 Node dashboard tests,
nine-registry validation with all 47 intake artifact hashes, separate template validation,
Git history checks and deterministic web export. The PR reports exact final test counts and
GitHub Actions outcomes for its tested head.

The CI matrix covers Linux with Python 3.10, 3.12 and 3.13, and Windows with Python 3.12.
Node is used only for developer tests; normal dashboard use requires no Node/npm.

Browser visual/interactive QA could not complete: the available browser rejected the local
Live Server equivalent with `net::ERR_BLOCKED_BY_CLIENT`. Static shell/accessibility checks,
canonical parsing and rendering tests cover all eight views, including generated synthetic
run data, but do not replace a real viewport inspection.

Registry validation proves structure and local provenance, not the truth of paper prose,
independence of imported human votes or a remote implementation. Recorded bundles seal the
analysis code/schema hashes; future analysis changes require retaining the recorded code revision
for replay or recording a new analysis run. Keep exact local run bundles and captured definitions:
they are ignored by default, and export fails closed when registered artifacts are absent.

No source workbook, synthetic production finding, novelty claim from absent evidence, or
manually entered HTML metric is introduced by this integration.
