# Literature intake and review

Start with [the easy platform guide](PLATFORM_QUICKSTART.md).

There is one scientific paper contract: `src/jailbreak_eval/schemas/registry.schema.json#/$defs/paper`.
`literature/paper_schema.json` is only a reference to it. The old importer registry and separate
website literature export are superseded.

## Intake

```text
python scripts/literature.py import "literature/my-matrix.xlsx"
python scripts/literature.py import "literature/my-matrix.xlsx" --sheet "Papers" --header-row 2
python scripts/literature.py import "literature/papers.csv" "literature/extra.jsonl"
python scripts/literature.py validate
python scripts/research.py build-web
```

Supported source files: XLSX, CSV, TSV, JSON arrays, JSONL objects. Save old XLS files as XLSX.
Structured research notes use JSON/JSONL. Free-form TXT and PDF are not parsed automatically.
All original columns are preserved, including the original attack-oriented columns and spelling.
No absent venue, year, DOI, benchmark finding, validator behaviour or metric is invented.

Canonical metadata comes only from supplied title, year, venue/identifier and designated paper
links/DOI/arXiv fields. Other matrix contents remain raw, except explicitly personal interpretations
and open questions, which are retained in those categories. Matrix review statuses and claims are
not evidence promotion instructions.

Every intake artifact is addressed by a hash and references its canonical paper ID. It retains
source filename/SHA-256, sheet, row, original column headings and values, cell positions, formulas
and hyperlinks. The source XLSX is not committed. Source paper links remain links, not a claim
that the importer accessed or verified them.

IDs are allocated once and reused from recorded source provenance. Exact-repeat imports are
idempotent. Keep an explicit `paper_id` column for ongoing curation and reordered/changed sources.
A repeated DOI, arXiv ID, designated paper URL or normalized exact title is a duplicate candidate,
never an automatic merge. Different sources with similar titles can stay separate until reviewed.

## Explicit review revisions

A curator note is an array of partial **canonical paper revisions**, not a second scientific schema.
All fields omitted from a revision are copied from the previous version. Prior versions are retained.

This is a **format example only**. Replace its ID, source, claim, dates and reviewer with actual
reviewed information; do not import example statements as paper findings.

```json
[
  {
    "id": "paper:replace-with-your-existing-id",
    "version": "2",
    "timestamp": "2026-09-10T12:00:00Z",
    "evidence_status": "screened",
    "sources": [
      {
        "id": "source:paper-primary",
        "kind": "paper",
        "url": "https://example.invalid/replace-with-the-actual-paper",
        "locator": "Actual paper version and location"
      }
    ],
    "paper_demonstrates": [
      {
        "id": "evidence:keep-a-stable-claim-id",
        "topic": "success_definition",
        "claim": "Replace with the actual source-supported extraction.",
        "source_id": "source:paper-primary",
        "locator": "Actual section, page or table",
        "verification_status": "unverified"
      }
    ],
    "review": {
      "reviewer": "Actual reviewer identifier",
      "reviewed_at": "2026-09-10T12:00:00Z",
      "notes": "Explain what was checked and what remains unchecked.",
      "verified_evidence_ids": []
    }
  }
]
```

```text
python scripts/literature.py review "literature/my-review-notes.json"
python scripts/research.py build-web
```

`--notes` on the import command accepts the same explicit revisions. JSONL works too.

- **listed**: intake only; no `paper_demonstrates` claims.
- **screened**: source metadata and reviewer/date/notes required; limited extracted evidence is allowed.
- **deep-reviewed**: source metadata, extracted evidence and review provenance required.
- **verified**: all supplied evidence claims must be explicitly listed in the current review's
  `verified_evidence_ids` and marked verified. This records a human declaration, not software
  certification of the source's truth or verification of all possible metadata fields.

A changed scientific claim requires a new revision and fresh review provenance. An already verified
claim cannot change silently under the same version. A changed intake artifact alone can be attached
under a new version without overwriting previously curated claims.

The validation-project fields from the old matrix/schema map to source-linked extraction topics:
research problem, benchmark/dataset, domain/subdomain, success definition, validator/judge,
labels/score, evaluation type, execution, human ground truth, metrics, FP/FN evidence and author
limitations. They belong in `paper_demonstrates` with an actual source/locator. Canonical
`benchmark_ids`, `domain_ids` and `validator_ids` link reviewed definitions. Interpretations and
open questions have separate object arrays. An empty extraction means unknown, not false.

Novelty has only manual states: `unassessed`, `under_review`, `prior_work_overlap`. Overlap needs
explicit evidence IDs and rationale. Absence of literature never creates a novelty claim.
