# Import your literature matrix

You need Python 3.10 or newer, Git and VS Code. You do not need npm,
Node.js, an API key or a running website. The importer does not search the
internet or fill in missing facts.

## 1. Get the code

Open a terminal in the folder where you keep your projects. Run:

```text
git clone https://github.com/RifatBinSaroar/jailbreak-eval-lab.git
cd jailbreak-eval-lab
git switch feat/literature-ingestion-pipeline
```

If you already have the repository, open its folder in VS Code, choose
**Terminal → New Terminal**, then run:

```text
git fetch origin
git switch feat/literature-ingestion-pipeline
```

This branch is used while the PR is open. After it is merged, use `main`.
If Git says your own changes would be overwritten, save your work before switching.

## 2. Set up Python once

In the VS Code terminal, run these commands **one line at a time**.

Windows:

```text
py -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-literature.txt
```

Mac or Linux:

```text
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-literature.txt
```

You do not need to activate the environment. The remaining commands use
Windows spelling. On Mac/Linux, replace `.venv\Scripts\python.exe` with
`.venv/bin/python`.

Dependency installation needs internet access once. Importing, exporting and
testing run locally. The development package also exposes these dependencies
as `.[literature]` for people using editable installs.

## 3. Put your Excel file in the input folder

Create a folder named `literature/input` in VS Code. Copy your workbook into it.
Keep its name `Jalibreak Literature Matrix.xlsx` for the command below.
Save your latest Excel edits before importing.

The existing `Matrix` sheet is supported as it is, including headings such as
`Catagory`, `My understnding` and `how the request is transforemed`.
The separate `Sheet1` column guide is skipped automatically. Your workbook is
read only; the importer does not edit it.

## 4. Import it

```text
.venv\Scripts\python.exe scripts/literature.py import "literature/input/Jalibreak Literature Matrix.xlsx" --replace
```

`--replace` rebuilds the generated files below from your current input. It
does not append to them. The repository includes a first import of the available
37-title workbook, so replacement is explicit. Without `--replace`, existing
output files are protected.

| File | What it contains |
| --- | --- |
| `literature/registry.json` | Canonical paper records, original columns and provenance |
| `literature/import_report.json` | Missing fields, warnings, skipped sheets and duplicate candidates |
| `apps/web/public/data/literature.json` | Validated records and counts for the future website |

Open the report in VS Code. A missing year, validator or source link is shown as
missing. It is not guessed. `null` means unknown. For example,
`executes_code: null` does not mean that a paper never executes code.

The supplied workbook contains only 37 titles; every other literature cell is
blank. Its first import therefore has 37 unreviewed, incomplete records and no
duplicate candidates. No paper facts have been checked as part of this import.
The original workbook is not committed. Each record includes its filename,
SHA-256, sheet and row so you can identify the exact source version.

## 5. Add your research notes

You can add columns with the exact field names from
`literature/paper_schema.json` to Excel. For detailed reviews, a JSON notes file
is easier. Keep your notes outside the generated registry so you can reuse them.

1. Open `literature/registry.json` and find a paper.
2. Copy its `paper_id`.
3. Create `literature/input/notes.json` and start with this shape:

```json
[
  {
    "paper_id": "PASTE_THE_EXISTING_PAPER_ID_HERE",
    "url": null,
    "success_definition": null,
    "validator": null,
    "evaluation_type": null,
    "executes_code": null,
    "human_ground_truth": null,
    "paper_demonstrates": null,
    "our_interpretation": null,
    "open_questions": null,
    "evidence_status": "unreviewed"
  }
]
```

Replace the ID with the real ID you copied. Fill in only things you know.
Leave unknowns as `null`. Lists use JSON arrays, such as
`"open_questions": ["Does the paper report manual agreement?"]`.
Then import the same workbook with the notes:

```text
.venv\Scripts\python.exe scripts/literature.py import "literature/input/Jalibreak Literature Matrix.xlsx" --notes literature/input/notes.json --replace
```

Notes update only the named paper ID. Unlisted fields keep the Excel value.
An explicit `null` in notes clears the canonical field; the original source cell
is still retained. Keep using `--notes` on future imports or those enrichments
will not be included. Do not edit generated JSON as your main notes workflow.

For runnable synthetic examples, see `literature/examples/papers.json` and
`literature/examples/review_notes.json`. These are test examples, not real papers.

## 6. Record review progress honestly

| Status | Meaning and required record |
| --- | --- |
| `unreviewed` | Imported only. No human screening is asserted. This is the default. |
| `screened` | A person screened the entry. Supply `reviewed_by`, `reviewed_at` and `notes` in `review`. |
| `deep-reviewed` | A person extracted paper evidence. Also supply a primary paper URL/DOI/arXiv ID and `paper_demonstrates`. |
| `verified` | Source checks are recorded for named fields. Also supply at least one `review.checks` entry with the exact value, source URL, locator, checker and date. |

Dates use `YYYY-MM-DD`. Review metadata records **your declaration**. Validation
checks its structure and consistency; it does not prove you read the source.
`verified` applies only to fields listed in `review.checks`, not every field in
the paper. Other fields can still be missing or unchecked. A changed checked
value makes the old check invalid until you recheck it.

Keep `paper_demonstrates`, `our_interpretation` and `open_questions` separate.
Legacy `Main Result`, `Limitation` and attack columns stay in their original
source rows. The importer does not turn these into verified paper claims.

## 7. Validate, export and test

Check the canonical registry:

```text
.venv\Scripts\python.exe scripts/literature.py validate
```

Regenerate only the website JSON:

```text
.venv\Scripts\python.exe scripts/literature.py export --replace
```

Run the automated tests:

```text
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The tests create small, harmless files in temporary folders. They need no npm,
test service, paper downloads or API calls. The website itself is still a
scaffold: exporting JSON prepares its data and does not deploy a website.

## If something goes wrong

- **Python not found:** try `py` on Windows or `python3` on Mac/Linux in step 2.
- **Module not found:** rerun the dependency install with the same environment's Python.
- **No paper rows:** check the sheet and header row. You can add
  `--sheet "Matrix" --header-row 1` to the import command.
- **Invalid year:** use a four-digit integer or leave it blank. Do not write `2024?`.
- **Duplicate candidates:** inspect the IDs and sources in the report. They are
  possible matches, not proven duplicates. Correct the input or combine notes
  deliberately, then rebuild. No row is silently merged or deleted.
- **Fail on duplicates:** add `--fail-on-duplicates` to import, validate or export
  when you want any match to block the operation.
- **Wrong notes ID:** copy the ID from a fresh import. IDs derived from titles
  can change when a title is corrected. Set an explicit `paper_id` column if you
  need permanent curator-controlled IDs.
- **Formula warning:** use a literal value in the canonical field. Formulas are
  retained but not calculated. Simple literal `HYPERLINK` formulas are supported.
- **Failed import:** fix the reported problem. Validation errors leave the last
  good registry and website JSON intact; the report records the error. An operating
  system write failure can interrupt the sequence between files, so rerun the
  import or export after fixing it. Each individual file is replaced atomically.

For exact mappings, ID rules and the web contract, see
[`literature/README.md`](../literature/README.md).
