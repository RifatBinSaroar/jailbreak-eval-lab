# Literature ingestion contract

`Excel / structured notes → Python importer → registry.json → website JSON`

Start with [the easy local guide](../docs/LITERATURE_QUICKSTART.md). The scripts
require Python 3.10+ and `requirements-literature.txt`; npm is not used.

## Input formats

- XLSX: all sheets with a `Paper`, `Title` or `Paper title` heading, or one named
  `--sheet`. Header defaults to row 1; use `--header-row` for a preface. Hidden
  sheets with paper headings are included. Guide sheets are reported as skipped.
- CSV/TSV: UTF-8, optional BOM, quoted multiline cells, one header row.
- JSON: an array of paper objects. JSONL: one object on each nonblank line.
- Multiple input files can follow `import`. Duplicate papers are kept and flagged.
- `--notes` accepts JSON/JSONL overrides using an existing `paper_id`. One override
  object per ID; unknown IDs or multiple overrides for one ID stop the import.
- XLS, arbitrary prose/TXT, PDFs and Markdown are not parsed. Save XLS as XLSX;
  convert prose to explicit structured notes yourself. No language model is called.

Headers are matched without case, spaces, underscores or punctuation. Duplicate
normalized headers and conflicting aliases fail rather than discarding cells.
Unknown columns are preserved with a report warning. Every original column,
including blank and attack-oriented columns, remains in `sources[].columns`.
Unheaded columns receive positional names such as `__column_3`.

## Original matrix mappings

| Existing heading | Canonical field or treatment |
| --- | --- |
| Paper | `title`; its web hyperlink can populate `url` |
| Year | `year` |
| Venue | `venue_or_arxiv` |
| Benchmark | `benchmark` |
| Evaluation metric | `metrics` |
| My understnding / My understanding | `our_interpretation` |
| Questions | `open_questions` |
| Catagory, Attack type, white/black box | Original columns only |
| Main idea, Models tested, Main Result | Original columns only |
| Limitation, Future work | Original columns only |
| Code/data | Original column; web links also enter `source_links` |
| how the request is transforemed, SoK relevance, New-method relevance | Original columns only |

All named research fields in `paper_schema.json` are accepted directly. Extra
aliases are `Paper title`, `Paper URL`, `Paper link` and `Link`. `Main idea` is not
assumed to be the research problem. `Catagory` is not assumed to be the validation
domain. `Limitation` is not assumed to be the authors' own limitation. Explicit
curation is needed for these mappings.

## Canonical schema and incompleteness

The existing paper schema is extended to make unavailable research values
nullable and to add `unreviewed` before the existing three review stages. It
adds identifiers (`doi`, `arxiv_id`), `source_links`, `sources`, `missing_fields`,
`warnings` and `review`. No original research field is removed. All canonical
keys must be present; unknown scalar/list fields use `null`, not fabricated text.
`novelty_threat` defaults to `UNKNOWN` and is marked missing. Review requirements
are enforced by the Python validator as well as field types in JSON Schema.

Blank, `unknown`, `not reported`, `not yet checked`, `TBD`, `N/A`, `?` and `-`
mean unknown in mapped fields. Raw cells are retained unchanged. The word `no`
is converted to false only in `executes_code`. `none` is preserved as text.
List fields accept JSON arrays or semicolon/newline-separated text, never split
on commas. Empty lists become `null`; blank/unknown elements in nonempty lists
are rejected. Rich prose and original numerical strings remain in source cells.

Each source records the input basename, SHA-256, sheet, row and cell values,
hyperlink targets and formula flags. Exact workbook bytes remain local. No
absolute local path, import timestamp or inferred publication detail is added.
The importer never evaluates formulas. Literal two-string `HYPERLINK` formulas
can provide their stated label and HTTP(S) destination; other formulas produce
missing canonical values plus warnings.

`source_links` retains discovered HTTP(S) URLs, including code/data links. DOI
and arXiv resolver URLs are mechanically formed from explicitly supplied IDs,
not retrieved or verified. A code link alone never becomes the primary `url`.
Non-web hyperlinks remain only in the source cell and produce a warning.

## Identity and duplicate detection

Explicit `paper_id` values take precedence and must be unique. Otherwise the ID
is a SHA-256-derived 16-hex token using explicit DOI, explicit arXiv ID,
normalized title, then primary URL (in that order). IDs are stable for the same
identity input; metadata added through `--notes` keeps the existing ID. Changing
the identity used at intake can change a generated ID. Set `paper_id` explicitly
for long-lived curator-managed records.

Repeated generated IDs receive `-2`, `-3`, etc. in input order. Those suffixes
are positional, so resolve duplicate rows before attaching long-lived notes.
All rows remain present, even when year or other values conflict. There is no
automatic merge, fuzzy title matching, online DOI lookup or cross-file overwrite.
An import rebuilds a complete snapshot; it is not an incremental database update.

Duplicate candidates share any of:

- a DOI after case/resolver normalization;
- an arXiv ID after removing version and PDF suffix (including legacy IDs);
- a Unicode-normalized title ignoring punctuation/case/spacing;
- an identical explicitly designated paper URL, ignoring a final slash.

Different years/DOIs with a matching title remain candidates for a person to
resolve. Shared generic code/data URLs are not identity matches. A pair can
appear in multiple groups for different reasons; `duplicate_groups` counts
match groups, not unique duplicate papers. Export includes the candidates so
the website must not silently treat them as deduplicated literature counts.

## Review and claim discipline

The importer defaults to `unreviewed` and never infers a review stage from note
length, populated cells or source links. Each higher stage is explicit and
requires provenance described in the quickstart. `verified` is a recorded,
field-specific human check, not an importer claim of independent verification.
Missing fields can coexist with a verified check of a different field.

`review.checks[].value` must exactly match the current canonical field's JSON
value, including type; its `source_url` must be present in `source_links`.
Missing fields and `UNKNOWN` novelty cannot be verified. Dates are validated
as calendar dates. Locators, checker names and review notes must be nonblank.
The software cannot judge the truth or adequacy of the supplied source check.

`paper_demonstrates`, `our_interpretation` and `open_questions` remain distinct.
Imported claims at lower review stages must be displayed with their status;
their presence does not establish truth or novelty.

## Outputs and website contract

The canonical envelope is `{schema_version, records, duplicate_candidates}`.
Website JSON contains the same validated records and adds `summary` with total,
review-stage counts, incomplete-paper count and duplicate-group count. Schema
version `1.0` describes this registry contract, not the project's research version.
All serialization is deterministic UTF-8 JSON with no NaN/Infinity or timestamps.

The intended web asset is `apps/web/public/data/literature.json`, served as
`/data/literature.json` when a future frontend uses that public directory.
There is no frontend implementation in this PR. It should:

- show `null` as “Unknown / not recorded”, never as “No”;
- show review status next to every literature claim;
- show field-level check provenance instead of implying every field is verified;
- link records and claims back to sources, with missing links clearly marked;
- retain the three claim buckets and duplicate warnings;
- render original cell text as text, never HTML or executable formulas;
- use only validated `source_links` as clickable HTTP(S) destinations.

`export` validates again; stale missing-field/duplicate metadata or invalid
review records block output. `--fail-on-duplicates` makes potential duplicates
a nonzero exit. Structural failures return exit code 2. A successful import
with incomplete fields returns 0 and reports them. Existing outputs require
`--replace`; inputs cannot be output targets. All validation finishes before
registry/web writes; replacements are atomic per file, not a multi-file
transaction. If an OS error interrupts writes, rerun after correcting the cause.

The checked-in initial registry comes from the user's available Excel matrix.
It contains 37 supplied titles only, all unreviewed and incomplete. It does not
claim publication metadata, verified findings or a literature search result.
`examples/` contains separately labelled synthetic input for exercising every
stage without implying real paper evidence.
