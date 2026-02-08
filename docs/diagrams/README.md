# Diagram Sources

This directory contains [draw.io](https://www.diagrams.net/) source files for
all project diagrams. The exported PNGs live in `docs/images/`.

## Editing

Open any `.drawio` file in:
- **draw.io Desktop** (recommended) - [download](https://github.com/jgraph/drawio-desktop/releases)
- **diagrams.net** - open https://app.diagrams.net and load the file

## Exporting

After editing a diagram, export a PNG to `docs/images/` using the CLI:

```bash
drawio --export --format png --output docs/images/<name>.png --scale 2 docs/diagrams/<name>.drawio
```

Or via the GUI:

1. File > Export as > PNG
2. Settings: **transparent background**, **scale 2x** (for retina)
3. Save to `docs/images/<same-name>.png`

**Convention**: the PNG filename matches the `.drawio` filename (e.g.
`system-overview.drawio` exports to `system-overview.png`).

## Diagram Index

| File | Description | PNG |
|---|---|---|
| `system-overview.drawio` | Full-stack architecture (clients, Docker Compose, monitoring, k3s) | [system-overview.png](../images/system-overview.png) |
| `pipeline-flow.drawio` | EPUB processing pipeline data flow | [pipeline-flow.png](../images/pipeline-flow.png) |
| `player-journey.drawio` | Interactive reader user journey | [player-journey.png](../images/player-journey.png) |
| `frontend-arch.drawio` | React SPA component and view architecture | [frontend-arch.png](../images/frontend-arch.png) |
| `backend-modules.drawio` | Python backend module dependency map | [backend-modules.png](../images/backend-modules.png) |
| `test-architecture.drawio` | Test suite architecture (unit, integration, E2E across 4 platforms) | [test-architecture.png](../images/test-architecture.png) |
