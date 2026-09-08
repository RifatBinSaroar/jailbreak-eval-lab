# Web application

The web interface is a first-class research interface, not a decorative landing page.

## Current technology choice

The first web milestone deliberately uses **plain HTML, CSS, and JavaScript**.

Why:

- no npm or Node.js is required;
- it runs directly in VS Code with Live Server;
- the UI can still be polished and responsive;
- the research data model can be stabilised before introducing a larger frontend toolchain;
- it can later be migrated to React / Next.js without changing the research architecture.

## Run locally with VS Code Live Server

1. Clone or download the repository.
2. Open the repository folder in VS Code.
3. In the Explorer, open `apps/web/index.html`.
4. Right-click `index.html`.
5. Select **Open with Live Server**.
6. The browser should open the dashboard automatically.

If the Live Server command is missing, install the **Live Server** extension by Ritwick Dey from the VS Code Extensions panel.

No terminal command, npm install, or build step is needed for v0.1.

## Current pages / sections

The v0.1 shell exposes the research structure through one responsive dashboard:

- Home / research overview
- Run Evaluation placeholder
- Experiments
- Datasets placeholder
- Validators
- Results
- Visualisations / roadmap
- Reports placeholder
- Documentation placeholder
- Papers & References
- Settings placeholder

## Design direction

The approved visual direction is a polished research dashboard with:

- dark navy left navigation;
- bright, spacious main workspace;
- soft blue / purple / green / peach accent cards;
- strong typography and restrained shadows;
- metric cards and comparison views;
- experiment panels;
- literature and documentation views.

The website must eventually read structured repository artefacts. It must not present unverified claims or illustrative metrics as measured research results.

## Development sequence

1. Build and review the visual shell.
2. Connect structured literature records.
3. Connect experiment and result artefacts.
4. Add evaluator comparison views and charts.
5. Add safe interactive evaluation only after the backend contract is stable.
6. Consider migration to React / Next.js only when the added complexity is justified.
