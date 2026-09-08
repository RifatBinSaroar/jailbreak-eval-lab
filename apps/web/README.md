# Research dashboard — no npm

Open the whole repository in VS Code, right-click `apps/web/index.html`, then choose
**Open with Live Server**. Plain HTML/CSS/JavaScript; no bundler, npm or remote scripts.

The approved PR3 navy sidebar, bright workspace, cards, responsive navigation, keyboard focus,
skip link, history navigation, literature filters and expandable provenance are retained.

Eight views: overview/readiness, literature, validators, benchmarks, domains/subdomains,
experiments, results, and novelty threats/open questions.

Every view consumes one Python-generated canonical export, `data/research.json`:

```text
python -m pip install -e .
python scripts/research.py build-web
```

Press **Refresh data** in the dashboard after rebuilding. Read
[the easy guide](../../docs/PLATFORM_QUICKSTART.md) for importing papers and recording outputs.
The dashboard has no independent scientific records and no provisional WEB-* IDs.

Reviewed extractions display their real stage and verification state. Measured results must
reproduce from registered immutable run bundles. Synthetic previews are conspicuously marked;
templates are rejected. Empty experiments/results stay truthful zeros; failed data shows
unavailable instead of zero. Later validator versions cannot relabel old results.

## Development verification

```text
node --test apps/web/tests/data.test.cjs
node --check apps/web/app.js
node --check apps/web/data.js
node --check apps/web/views.js
```

Node is only for optional developer tests; using the dashboard requires neither Node nor npm.
Python integration tests additionally pass a real canonical synthetic-run export through the JS
parser and all eight view renderers when Node is available.

## Manual visual check

At desktop and phone widths, open all eight navigation views. Check the menu toggle and Escape,
keyboard Tab/skip-link, paper search/status/domain filters, Clear filters, paper deep links,
source/intake links, Refresh data and the zero-results panel. Expand a sourced paper's extraction
and a synthetic preview's provenance/metrics to check long IDs and table scrolling.

In this integration session the cloud browser blocked the local preview URL with
`net::ERR_BLOCKED_BY_CLIENT`. Browser visual/interaction QA is therefore unverified. The completed
checks cover canonical parsing, generated HTML, filtering, links, escaping, empty/error states,
responsive CSS/navigation structure and synthetic result rendering; they are not a substitute for
an actual phone/desktop visual inspection.
