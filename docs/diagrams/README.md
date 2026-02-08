# Diagram Sources

This directory contains [draw.io](https://www.diagrams.net/) source files for
all project diagrams. The exported SVGs live in `docs/images/`.

## Editing

Open any `.drawio` file in:
- **draw.io Desktop** (recommended) - [download](https://github.com/jgraph/drawio-desktop/releases)
- **diagrams.net** - open https://app.diagrams.net and load the file

## Exporting

After editing a diagram, export an SVG to `docs/images/`:

1. File > Export as > SVG
2. Settings: **transparent background**, **do not include a copy of the diagram**
3. Save to `docs/images/<same-name>.svg`

**Convention**: the SVG filename matches the `.drawio` filename (e.g.
`system-overview.drawio` exports to `system-overview.svg`).

## Diagram Index

| File | Description | SVG |
|---|---|---|
| `system-overview.drawio` | Full-stack architecture (users, frontend, API, services, storage) | [system-overview.svg](../images/system-overview.svg) |
| `pipeline-flow.drawio` | EPUB processing pipeline data flow | [pipeline-flow.svg](../images/pipeline-flow.svg) |
| `player-journey.drawio` | Interactive reader user journey | [player-journey.svg](../images/player-journey.svg) |
| `frontend-arch.drawio` | React SPA component and view architecture | [frontend-arch.svg](../images/frontend-arch.svg) |
| `backend-modules.drawio` | Python backend module dependency map | [backend-modules.svg](../images/backend-modules.svg) |
| `test-architecture.drawio` | Test suite architecture (unit, integration, E2E across 4 platforms) | [test-architecture.svg](../images/test-architecture.svg) |
