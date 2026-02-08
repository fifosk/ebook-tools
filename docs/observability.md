# Observability Guide

This guide covers the monitoring and observability stack for ebook-tools,
including Prometheus metrics collection, Grafana dashboards, PostgreSQL
monitoring, and the observability test suite.

## Architecture

```
Backend (:8000/metrics) ──(10s)──> Prometheus (:9090) ──> Grafana (:3000)
PostgreSQL (:5432)      ──(30s)──> PG Exporter (:9187) ─┘
```

Three services form the monitoring stack:

| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| **Prometheus** | `prom/prometheus:v2.51.0` | 9090 | Metrics collection and storage |
| **Grafana** | `grafana/grafana-oss:11.0.0` | 3000 | Dashboard visualisation |
| **PostgreSQL Exporter** | `prometheuscommunity/postgres-exporter:v0.15.0` | 9187 | Database metrics bridge |

All three run alongside the application containers in `docker-compose.yml` and
are managed through dedicated Makefile targets.

### Access URLs

| Service | URL | Credentials |
|---------|-----|-------------|
| Grafana | `https://grafana.langtools.fifosk.synology.me` | `admin` / `$GRAFANA_ADMIN_PASSWORD` |
| Prometheus | `https://prometheus.langtools.fifosk.synology.me` | none |
| Backend metrics | `http://localhost:8000/metrics` | none |

---

## Starting the Monitoring Stack

```bash
# Start monitoring services (alongside existing app containers)
make monitoring-up

# Check health of all monitoring services
make monitoring-status

# Follow monitoring logs
make monitoring-logs

# Stop monitoring services (app containers unaffected)
make monitoring-down
```

The monitoring services are independent of the application. Starting or stopping
them does not affect the backend, frontend, or PostgreSQL containers.

---

## Metrics

### Backend Metrics (`/metrics`)

The backend exposes a Prometheus endpoint at `GET /metrics`. Metrics are
defined in `modules/webapi/metrics.py` and collected in two ways:

1. **HTTP auto-instrumentation** via `prometheus-fastapi-instrumentator` --
   request duration, count, and in-progress gauges per handler.
2. **Application metrics** -- custom counters, gauges, and histograms updated
   by application code and a 15-second periodic collector.

#### Custom Metrics Reference

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `ebook_tools_up` | Gauge | -- | Backend availability (1=up) |
| `ebook_tools_health_status` | Gauge | -- | Health (1=ok, 0.5=degraded, 0=unhealthy) |
| `ebook_tools_jobs_total` | Gauge | `status` | Jobs by status |
| `ebook_tools_jobs_active` | Gauge | -- | Currently running jobs |
| `ebook_tools_jobs_queue_depth` | Gauge | -- | Pending + running jobs |
| `ebook_tools_job_duration_seconds` | Histogram | `job_type`, `status` | Job execution duration |
| `ebook_tools_jobs_backpressure_rejections_total` | Counter | -- | Rejected jobs (backpressure) |
| `ebook_tools_jobs_backpressure_delays_total` | Counter | -- | Delayed jobs (backpressure) |
| `ebook_tools_library_items_total` | Gauge | `item_type` | Library items (book/video/subtitle) |
| `ebook_tools_users_total` | Gauge | `role` | Users by role |
| `ebook_tools_sessions_active` | Gauge | -- | Non-expired sessions |
| `ebook_tools_auth_attempts_total` | Counter | `method`, `result` | Auth attempts |
| `ebook_tools_pipeline_stage_duration_seconds` | Histogram | `stage` | Pipeline stage timing |
| `ebook_tools_worker_pool_utilization` | Gauge | -- | Active / max workers |
| `ebook_tools_errors_total` | Counter | `error_type`, `endpoint` | Application errors |
| `ebook_tools_job_failures_total` | Counter | `error_type` | Job failures by type |

#### HTTP Auto-Instrumentation

| Metric | Type | Labels |
|--------|------|--------|
| `http_request_duration_seconds` | Histogram | `handler`, `status` |
| `http_requests_total` | Counter | `handler`, `method`, `status` |
| `ebook_tools_http_requests_inprogress` | Gauge | `handler`, `method` |

The `/metrics` and `/_health` endpoints are excluded from HTTP instrumentation.

### PostgreSQL Exporter Metrics

The `postgres-exporter` service scrapes PostgreSQL system views and exposes
them as Prometheus metrics. In addition to the built-in PG metrics, five
custom queries are defined in `monitoring/postgres-exporter/queries.yaml`:

| Custom Metric | Type | Description |
|---------------|------|-------------|
| `ebook_tools_library_items` | Gauge | Library items by type |
| `ebook_tools_users` | Gauge | Users by role |
| `ebook_tools_active_sessions` | Gauge | Non-expired sessions |
| `ebook_tools_bookmarks` | Gauge | Total bookmarks |
| `ebook_tools_resume_positions` | Gauge | Total resume positions |

Built-in PG metrics include connection counts, cache hit ratio, transaction
rate, table sizes, and dead tuple counts.

---

## Adding New Metrics

1. **Define** the metric in `modules/webapi/metrics.py`:

   ```python
   MY_COUNTER = Counter("ebook_tools_my_counter", "Description", ["label"])
   ```

2. **Instrument** at the call site with a lazy import:

   ```python
   def my_function():
       try:
           from modules.webapi.metrics import MY_COUNTER
           MY_COUNTER.labels(label="value").inc()
       except Exception:
           pass
   ```

3. For **gauge-style metrics** that need periodic refresh, add a collector
   function in `_periodic_gauge_update()`.

4. **Verify** the metric appears:

   ```bash
   curl -s http://localhost:8000/metrics | grep ebook_tools_my_counter
   ```

5. **Update dashboards** if the metric should be visualised (see below).

6. **Run observability tests** to validate:

   ```bash
   pytest -m observability -v
   ```

---

## Dashboards

Four auto-provisioned Grafana dashboards are available in the "ebook-tools"
folder. They are JSON files in `monitoring/grafana/dashboards/` and are
loaded automatically by the Grafana provisioning system.

### Overview Dashboard

**UID**: `ebook-tools-overview` | **Refresh**: 30s

High-level system health at a glance:

- Backend availability and health status
- Active jobs and sessions
- Request rate and 5xx error rate
- Request rate over time (timeseries)
- Job status distribution (pie chart)
- Queue depth over time

### Backend Dashboard

**UID**: `ebook-tools-backend` | **Refresh**: 30s

Detailed backend performance metrics:

- **HTTP**: Request rate and error rate by handler
- **Latency**: p50, p95, p99 request duration
- **Pipeline**: Stage duration at p95
- **Jobs**: State distribution, duration by type
- **Workers & Auth**: Pool utilization, auth attempts, library items

### Database Dashboard

**UID**: `ebook-tools-database` | **Refresh**: 30s

PostgreSQL health and performance:

- **Connections**: Active database connections
- **Cache**: Buffer cache hit ratio
- **Transactions**: Commit and rollback rate, temp bytes
- **Tables**: Size by table, dead tuples (autovacuum indicator)
- **App metrics**: Active sessions, library items, bookmarks

### Metrics QA Dashboard

**UID**: `ebook-tools-metrics-qa` | **Refresh**: 10s | **Window**: 15 minutes

One panel per metric for visual smoke-testing. Verifies that every defined
metric is being scraped and populated. Includes a dedicated row for k3s POC
metrics when a k3s deployment is running.

### Editing Dashboards

Dashboards are editable in the Grafana UI. To persist changes:

1. Edit the dashboard in the Grafana UI.
2. Export via **Share > Export > Save to file**.
3. Copy the JSON to the corresponding file in `monitoring/grafana/dashboards/`.
4. Commit the updated JSON.

The provisioning system reloads dashboards every 30 seconds.

---

## Prometheus Configuration

Prometheus is configured in `monitoring/prometheus/prometheus.yml`.

### Scrape Jobs

| Job | Target | Interval | Labels |
|-----|--------|----------|--------|
| `ebook-tools-backend` | `backend:8000` | 10s | `service="backend"` |
| `postgres-exporter` | `postgres-exporter:9187` | 30s | `service="postgres"` |
| `k3s-backend` | `host.docker.internal:18000` | 15s | `service="backend"`, `deployment="k3s"` |
| `prometheus` | `localhost:9090` | 60s | self-monitoring |

The `k3s-backend` job is only active when a k3s port-forward is running
(`kubectl port-forward svc/ebook-tools-backend 18000:8000`). Dashboard
PromQL uses `max without (deployment)` to merge Docker Compose and k3s
metrics seamlessly.

### Retention

- **Time**: 90 days
- **Size**: 20 GB
- **Data directory**: `/Volumes/Data/Monitoring/prometheus`

---

## Grafana Provisioning

Grafana is auto-configured via provisioning files:

| File | Purpose |
|------|---------|
| `monitoring/grafana/provisioning/datasources/prometheus.yml` | Prometheus datasource (UID: `prometheus`, default) |
| `monitoring/grafana/provisioning/dashboards/default.yml` | Dashboard folder ("ebook-tools"), reload every 30s |
| `monitoring/grafana/dashboards/*.json` | Dashboard definitions (4 files) |

Data is persisted to `/Volumes/Data/Monitoring/grafana`.

---

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `GRAFANA_ADMIN_USER` | `admin` | Grafana admin username |
| `GRAFANA_ADMIN_PASSWORD` | `ebook_tools_grafana` | Grafana admin password |
| `POSTGRES_PASSWORD` | `ebook_tools_dev` | Shared with postgres-exporter connection |

---

## Observability Tests

The test suite validates the entire observability pipeline end-to-end.

```bash
pytest -m observability -v       # ~26 tests
make test-observability          # same via Makefile
```

### Test Layers

| Layer | Tests | Validates |
|-------|-------|-----------|
| **Metric presence** | 16 | Every `ebook_tools_*` metric exists in `/metrics` with correct type |
| **Label cardinality** | 5 | Labelled metrics expose expected label names |
| **Dashboard coverage** | 1 | Every PromQL expression in dashboards references an existing metric |
| **HTTP auto-instrumentation** | 2 | Traffic generates `http_request_duration_seconds`; `/metrics` is excluded |
| **Auth counter** | 1 | Failed login increments `ebook_tools_auth_attempts_total{result="failure"}` |
| **Dashboard JSON structure** | 1 | All 4 dashboards have valid Grafana JSON with correct datasource UIDs |

The dashboard coverage test is particularly valuable: it reads all PromQL
expressions from all 4 dashboard JSON files and verifies that every referenced
metric name exists in either the `/metrics` endpoint output or a known list of
external metrics (e.g., `pg_stat_*`).

---

## First-Time Setup

```bash
# Create persistent storage directories on the host
mkdir -p /Volumes/Data/Monitoring/prometheus
mkdir -p /Volumes/Data/Monitoring/grafana
chown -R 472:472 /Volumes/Data/Monitoring/grafana

# Enable pg_stat_statements (already in docker-compose command args)
make db-shell
# => CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

# Start the full stack
docker compose up -d --build
make monitoring-up
```

---

## Directory Structure

```
monitoring/
├── prometheus/
│   └── prometheus.yml                     # Scrape config (3 jobs + self)
├── grafana/
│   ├── provisioning/
│   │   ├── datasources/prometheus.yml     # Auto-provision Prometheus datasource
│   │   └── dashboards/default.yml         # Dashboard provider config
│   └── dashboards/
│       ├── overview.json                  # System overview (9 panels)
│       ├── backend.json                   # Backend performance (13 panels)
│       ├── database.json                  # PostgreSQL health (13 panels)
│       └── metrics-qa.json               # One-panel-per-metric QA (38 panels)
└── postgres-exporter/
    └── queries.yaml                       # 5 custom app-specific queries
```
