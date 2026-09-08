# Research Platform v0.1 — easy start

You need **Python 3.10 or newer, Git, VS Code and Live Server**. You do not need npm.
Everything below works locally. These commands do not call models or execute generated code.

## 1. Open the project

For a new copy:

```text
git clone --branch feat/research-platform-v0.1-integration https://github.com/RifatBinSaroar/jailbreak-eval-lab.git
cd jailbreak-eval-lab
```

Open this folder in VS Code. Select **Terminal → New Terminal**. Run:

```text
python -m pip install -e .
```

On a Mac/Linux computer where `python` is not found, use `python3` in each command.
The installation needs internet once. Import, validation, recording and export then work offline.

## 2. Open the dashboard

In VS Code, find `apps/web/index.html`. Right-click it and choose **Open with Live Server**.
Keep the whole repository open as the VS Code workspace so source-artifact links work.

You should see **47 listed reading entries, 7 planned validator candidates, 3 benchmark candidates,
3 domain/subdomain entries, 0 experiments and 0 measured results**. The entries consist of the
37 workbook titles and 10 separate synthesis reading candidates. These are listings, not verified
papers or completed reviews. No automatic duplicate group was found by the conservative exact
identifier/title rules; that is not proof that the list is complete or duplicate-free.

The eight navigation views work without a build tool. Do not double-click the HTML file in your
file manager: browsers usually block its JSON requests under `file://`.

## 3. Import your literature

Put your workbook somewhere on your computer, then use its path. For example:

```text
python scripts/literature.py import "literature/my-matrix.xlsx"
python scripts/research.py validate
python scripts/research.py build-web
```

Click **Refresh data** on the dashboard. That is the complete update workflow.

CSV, TSV, JSON and JSONL also work:

```text
python scripts/literature.py import "literature/papers.csv"
python scripts/literature.py import "literature/papers.json"
```

For a particular Excel sheet:

```text
python scripts/literature.py import "literature/my-matrix.xlsx" --sheet "Literature Review"
```

The importer preserves original headings, blank cells, cell positions, formulas, hyperlinks,
sheet/row, filename and the source file's SHA-256. It stores traceable JSON intake artifacts.
It does not execute formulas, look up metadata, infer findings or commit the source workbook.
Workbook files are ignored by Git.

New papers start at **listed**. Review stages written in ordinary matrix cells do not promote a
paper. Raw matrix claims stay in intake provenance. Personal interpretation and questions can be
shown in their own categories.

The importer prints the new `paper:...` IDs. For long-term work, add a **paper_id** column to your
matrix and copy each paper's displayed ID into its row. Keep that ID when you correct the title,
add metadata, move the row or change source files. It identifies the paper, not its row number.
Exact repeat imports reuse the recorded identity. Changed or ambiguous rows require explicit IDs.
Duplicate candidates remain separate records; `--fail-on-duplicates` can block an import for review.

## 4. Update a paper after reviewing it

Keep the existing ID. Create a JSON file of explicit curator revisions using the format in
[LITERATURE_QUICKSTART.md](LITERATURE_QUICKSTART.md). Give the revision a **new version**, a later
**timestamp**, and current **review provenance**. Then run:

```text
python scripts/literature.py review "literature/my-review-notes.json"
python scripts/research.py build-web
```

Each prior version remains in the registry. The dashboard shows the newest version. A paper may
move from listed → screened → deep-reviewed → verified without changing its ID. Screened and
deep-reviewed evidence is visible with its real review state.

If you only attach a changed intake row, add `version` and `timestamp` columns as well as `paper_id`.
This preserves the new cells without overwriting the paper's curated scientific content.

## 5. Record outputs collected elsewhere

Do this only when you already have a capture manifest, dataset manifest, predictions and human
reference CSVs. This command **records existing decisions**; it cannot generate model responses.
The file format is explained in [EXPERIMENT_FRAMEWORK.md](EXPERIMENT_FRAMEWORK.md).

```text
python scripts/experiment.py validate --manifest "my-input/manifest.json" --dataset "my-input/dataset_manifest.json" --predictions "my-input/predictions.csv" --labels "my-input/human_labels.csv"
python scripts/experiment.py record --manifest "my-input/manifest.json" --dataset "my-input/dataset_manifest.json" --predictions "my-input/predictions.csv" --labels "my-input/human_labels.csv"
python scripts/experiment.py verify results/runs/RUN-YOUR-ID
python scripts/research.py build-web
```

Replace `RUN-YOUR-ID` with your capture's `run_id`. The recorder creates:

```text
results/runs/RUN-YOUR-ID/manifest.json
results/runs/RUN-YOUR-ID/canonical_inputs.json
results/runs/RUN-YOUR-ID/dataset_manifest.json
results/runs/RUN-YOUR-ID/predictions.csv
results/runs/RUN-YOUR-ID/human_labels.csv
results/runs/RUN-YOUR-ID/metrics.json
results/runs/RUN-YOUR-ID/errors.json
```

It also populates the canonical dataset, validator, experiment, run, human-label and result
registries. It checks the captured inputs, computes metrics and preserves all checksums.
The web build reproduces the metrics and checks registry equality before displaying results.
**Never type measured metrics into HTML or edit a recorded run.** Use a new run ID for corrected
capture inputs. Keep the previous run for provenance.

Use `split: "pilot"` and `purpose: "pilot"` for the planned kill-test. A final test needs
`split: "test"`, `purpose: "final_evaluation"` and a frozen protocol. Existing pilot/development
cases, grouping IDs and response hashes cannot be relabelled as final test, even under a new
dataset version or alias.

## 6. If something goes wrong

- **Missing module**: run `python -m pip install -e .` again in the repository folder.
- **Changed intake row**: add the existing `paper_id`, plus a new `version` and later `timestamp`.
- **Duplicate candidates**: inspect the returned groups. Do not silently merge them.
- **Run already exists**: use a new run ID. The old bundle stays immutable.
- **Registry publication interrupted after recording**: run
  `python scripts/experiment.py sync results/runs/RUN-YOUR-ID`, then rebuild the web data.
- **Interrupted registry directory swap**: preserve both directories. Restore the sibling
  `.registries-backup` as `registries` if the latter is missing, remove the stale write lock only
  after confirming no writer is running, then retry. A missing/partial directory fails closed.
- **Dashboard says unavailable**: use Live Server, rebuild the data, and press Refresh data.
- **Missing local run artifacts after cloning**: restore the exact local bundles. Web builds
  fail closed if a registered run cannot be reproduced. Raw run folders are ignored by default.

All build aliases use the same exporter. Prefer `python scripts/research.py build-web`.

## Optional developer checks

```text
python -m pip install -e ".[dev]"
python -m pytest -q
python -m jailbreak_eval.registry validate --artifact-root .
python scripts/research.py build-web
```

If Node is available, `node --test apps/web/tests/data.test.cjs` checks dashboard parsing and
rendering. Node/npm is not needed to use the dashboard. CI runs these developer checks for you.
