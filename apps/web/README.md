# Research dashboard

A plain HTML/CSS/JavaScript research workspace. **No npm, Node.js, install command or build step is needed to use it.** The navy sidebar, bright workspace and blue/purple/green/peach cards extend the approved static dashboard.

## Open it in VS Code

1. Open the repository folder in VS Code.
2. If needed, install **Live Server** by Ritwick Dey from Extensions.
3. Find `apps/web/index.html` in the Explorer.
4. Right-click it and choose **Open with Live Server**.
5. Choose a view in the sidebar. On a phone-sized window, use **Menu**.

Do not double-click the HTML file in your file manager. Browsers block JSON fetches from `file://` pages. If a registry cannot load, its view explains the error instead of displaying a false zero.

Python alternative, from the repository folder:

```bash
python -m http.server 8000
```

Open `http://localhost:8000/apps/web/`. Keep that terminal open while using the dashboard. Press Ctrl+C to stop it.

## The eight views

| View | What it provides |
| --- | --- |
| Overview | Counts from loaded records, current working hypothesis and explicit study-readiness tasks |
| Literature explorer | Search by title, ID, method or question; review-stage and domain filters; source links and expandable extraction details |
| Validators | Candidate methods, version, success definition and implementation status |
| Benchmarks | Candidate mappings, version, licence, redistribution and dataset-manifest readiness |
| Domains & subdomains | Parent/child study scope with candidate status and open questions |
| Experiment registry | Registered studies and their metadata, or a useful pre-experiment checklist |
| Results | Supplied run measurements, provenance, split and artifact links; invalid records are withheld |
| Gaps & novelty threats | Source-linked project interpretations, linked reading candidates and unresolved questions |

Navigation supports browser Back/Forward and links such as `#literature/WEB-PAPER-JAWS`. Legacy `#home`, `#papers`, `#run`, `#datasets`, `#visuals` and `#reports` bookmarks route to the relevant new view.

## What the initial data actually means

The included data is a **planning snapshot of the 8 September 2026 control-room synthesis**:

- 10 unreviewed reading-queue entries, with no extracted paper findings and no invented primary-paper URLs;
- 7 planned validator candidates, with zero marked implemented;
- 3 benchmark candidates, with version, licence and reuse permissions unrecorded;
- 1 parent domain and 2 candidate subdomains;
- 4 unresolved evidence/novelty items;
- **0 registered experiments and 0 measured result records**.

This is not an import of the user's Excel matrix. A title appearing in a synthesis does not make it screened, deep-reviewed or verified. The `WEB-*` IDs identify provisional web planning records, not established canonical paper identities. Every planning interpretation links to the exact synthesis commit. The lead candidate follows the later synthesis rather than the earlier README's ransomware candidate.

Readiness items are explicit planning statuses in `project.json`. Counts do not become a readiness percentage or a claim that an experiment is ready to run.

## Update the data

1. Export the relevant canonical registry into the matching file in `apps/web/data/`.
2. Use the shapes in [the data contract](data/README.md). Reconcile the provisional `WEB-*` IDs when replacing the reading queue and update referring IDs together.
3. Save the JSON file, then click **Refresh data** in the dashboard (or reload the page).

The browser only reads these exports. It does not write to canonical registries, import Excel, run models, execute validators or launch experiments. Future Python import/export tools can produce these files without changing the static website. Extra paper fields are preserved in the loaded record; `original_matrix` fields are available in the extraction details.

The eight JSON files are fetched independently and without browser caching. A missing file, invalid JSON, duplicate ID, unsupported schema or invalid paper review status causes an explicit error for that registry. Valid empty arrays remain truthful zero-record registries. Other valid views remain usable.

## Evidence and result rules

Five visible categories separate measured results, paper evidence, project interpretation, unresolved questions and planned experiments. Review stage is always taken from the paper record. Empty fields never promote a record or establish novelty.

A measured result must have a linked experiment and validator, valid ratio values, sample size, success definition, split, versioned run provenance, full code commit and artifact references. Otherwise it is withheld and the reason is shown. Missing or undefined metrics display **Not measured**; actual numeric zero remains zero. ASR differences use percentage points and require an explicit comparison direction. Development and test records are shown separately. No cross-run aggregation, attack ranking, pooled ASR or inferred metric is calculated by this UI.

These checks establish the shape and traceability of the export. They do **not** audit the primary papers or fetch/recompute the linked run artifacts. The exporting pipeline and research review must verify the artifact contents, provenance, denominators and split discipline before publication. The website does not change success definitions, labels, scoring or ground truth.

## Contributor checks (optional; not needed to use the dashboard)

With Node.js already installed, its built-in runner checks the data and rendering functions without npm or downloaded packages:

```bash
node --test apps/web/tests/data.test.cjs
node --check apps/web/data.js
node --check apps/web/views.js
node --check apps/web/app.js
```

The tests use benign in-memory records only. They cover missing/invalid files, duplicate IDs, review-stage discipline, search/filtering, source/HTML safety, truthful zero states, result provenance, actual zero versus null metrics, signed ASR differences and split separation. Synthetic metric fixtures stay in the test file and are never served as production data.

Manual review in Live Server: open every view; search/filter and clear the literature list; open a paper's details and source; follow a record link and use Back; resize to a phone width and use Menu; navigate with Tab and Escape; use browser zoom at 200%; refresh after editing an export. Temporarily renaming one JSON file should show an unavailable state in that view. Restore it and refresh to recover.
