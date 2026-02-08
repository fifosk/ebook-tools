# Kubernetes Deployment Guide

This guide covers the Helm chart POC for deploying ebook-tools to a k3s
cluster, including Lima VM setup on macOS, the `k3s-control.sh` lifecycle
script, image import workflow, and optional Argo CD GitOps integration.

> **Status**: This is a proof-of-concept deployment alongside the primary
> Docker Compose runtime. The monitoring stack (Prometheus, Grafana, PG
> exporter) remains on Docker Compose and scrapes the k3s backend via
> port-forward.

## Architecture

```
macOS Host
├── Docker Compose (primary)
│   ├── backend :8000
│   ├── frontend :5173
│   ├── postgres :5432
│   └── monitoring (Prometheus, Grafana, PG exporter)
│
└── Lima VM (k3s POC)
    └── k3s single-node cluster
        ├── backend Pod (:8000) ──port-forward──> localhost:18000
        ├── frontend Pod (:80)  ──port-forward──> localhost:15173
        ├── postgres StatefulSet (:5432)
        ├── pg-backup CronJob (daily 2 AM)
        └── (optional) Argo CD
```

The k3s cluster runs inside a Lima lightweight Linux VM on macOS. Images are
built with Docker on the host and imported into k3s's containerd via
`docker save | k3s ctr images import`. Port-forwards expose services to
the host for development and Prometheus scraping.

---

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Lima | 0.19+ | `brew install lima` |
| Helm | 3.14+ | `brew install helm` |
| kubectl | 1.28+ | `brew install kubectl` |
| Docker | 24+ | Docker Desktop or `brew install --cask docker` |

---

## Quick Start

```bash
# 1. Create and start the Lima VM with k3s
limactl create --name=k3s template://k3s
limactl start k3s

# 2. Start the VM + SSH tunnel + wait for readiness
scripts/k3s-control.sh start

# 3. Build images and deploy to k3s
scripts/k3s-control.sh deploy

# 4. Open port-forwards to access services
scripts/k3s-control.sh ports
# Frontend: http://localhost:15173
# Backend:  http://localhost:18000
```

---

## Lima VM Setup

The k3s cluster runs in a Lima VM with 4 CPUs, 8 GB RAM, and 60 GB disk
(Ubuntu 24.04). The VM uses `plain` mode with no automatic macOS directory
mounts -- all data lives in VM-local paths under `/data/`.

### Create Data Directories

After creating the VM, initialise the data directories:

```bash
limactl shell k3s sudo mkdir -p \
  /data/databases/ebook-tools/postgres \
  /data/backups/ebook-tools/postgres \
  /data/storage \
  /data/logs \
  /data/config-users \
  /data/nas/ebooks \
  /data/nas/videos \
  /data/nas/subtitles
```

### Kubeconfig

The k3s kubeconfig is automatically copied to the host at
`~/.lima/k3s/copied-from-guest/kubeconfig.yaml`. The `k3s-control.sh`
script sets `KUBECONFIG` automatically. For manual use:

```bash
export KUBECONFIG=~/.lima/k3s/copied-from-guest/kubeconfig.yaml
kubectl get nodes
```

---

## k3s-control.sh Commands

The lifecycle script at `scripts/k3s-control.sh` manages the entire k3s
workflow:

| Command | Description |
|---------|-------------|
| `start` | Boot VM, open SSH tunnel for k8s API (6443), wait for pods |
| `stop` | Kill port-forwards and SSH tunnel, stop VM |
| `status` | Show VM status, pod health, SSH tunnel, port-forwards |
| `ports` | Open port-forwards (frontend :15173, backend :18000, Argo CD :8080) |
| `deploy` | Build Docker images, import into k3s, helm upgrade, rollout restart |
| `teardown` | Helm uninstall (keeps VM running) |
| `nuke` | Full teardown: stop and delete VM (does not affect Docker Compose) |

### Common Workflows

```bash
# Start the day
scripts/k3s-control.sh start
scripts/k3s-control.sh ports

# Deploy code changes
scripts/k3s-control.sh deploy

# Check status
scripts/k3s-control.sh status

# End the day
scripts/k3s-control.sh stop
```

---

## Helm Chart

The Helm chart lives in `helm/ebook-tools/` and deploys four core services:

| Component | Kind | Notes |
|-----------|------|-------|
| PostgreSQL | StatefulSet | PVC-backed, custom `postgresql.conf`, init: `pg_stat_statements` |
| Backend | Deployment | Init container waits for PG, health probes on `/_health` |
| Frontend | Deployment | Nginx serving the React SPA |
| PG Backup | CronJob | Daily at 2 AM, 7-day retention |

### Chart Structure

```
helm/ebook-tools/
├── Chart.yaml                  # Chart metadata (v0.1.0)
├── values.yaml                 # Default values (production paths)
├── values-lima.yaml            # Lima VM overrides (/data/* paths)
└── templates/
    ├── _helpers.tpl            # Template helpers (fullname, labels)
    ├── NOTES.txt               # Post-install instructions
    ├── backend/
    │   ├── deployment.yaml     # Backend pods + init container
    │   ├── service.yaml        # ClusterIP :8000
    │   └── configmap.yaml      # Env vars + config.local.json
    ├── frontend/
    │   ├── deployment.yaml     # Nginx pods
    │   └── service.yaml        # ClusterIP :80
    ├── postgres/
    │   ├── statefulset.yaml    # PG 16 + PVC
    │   ├── service.yaml        # ClusterIP :5432
    │   └── configmap.yaml      # postgresql.conf tuning
    ├── pg-backup/
    │   └── cronjob.yaml        # Daily pg_dump + retention cleanup
    ├── ingress.yaml            # Traefik ingress rules
    └── secrets.yaml            # PG password
```

### Values Overview

Key settings in `values.yaml`:

| Path | Default | Description |
|------|---------|-------------|
| `global.imagePullPolicy` | `IfNotPresent` | `Never` for local imports |
| `postgres.resources.limits.memory` | `1Gi` | PG memory limit |
| `backend.replicas` | `1` | Backend pod count |
| `backend.resources.limits.memory` | `2Gi` | Backend memory limit |
| `backend.tmpfs.sizeLimit` | `1Gi` | RAM-backed temp workspace |
| `frontend.replicas` | `1` | Frontend pod count |
| `pgBackup.schedule` | `0 2 * * *` | Backup cron schedule |
| `pgBackup.retentionDays` | `7` | Backup retention |
| `nas.type` | `hostPath` | `nfs` for multi-node clusters |
| `ingress.enabled` | `true` | Traefik ingress |

### Lima Overrides

`values-lima.yaml` remaps all host paths to VM-local `/data/*` paths and
sets `imagePullPolicy: Never` for locally imported images:

```bash
helm upgrade --install ebook-tools ./helm/ebook-tools \
  -f ./helm/ebook-tools/values-lima.yaml \
  --namespace ebook-tools --create-namespace
```

---

## Makefile Targets

```bash
make k8s-build           # Build Docker images (prerequisite)
make k8s-import-images   # Import images into k3s containerd
make k8s-deploy          # helm upgrade --install
make k8s-status          # kubectl get pods,svc,ingress,pvc,cronjobs
make k8s-logs            # Follow backend pod logs
make k8s-teardown        # helm uninstall
make k8s-lint            # helm lint + helm template validation
```

---

## Image Workflow

Since the k3s cluster runs in a VM without access to the Docker daemon,
images must be exported and imported:

```bash
# Build with Docker Compose
docker compose build backend frontend

# Import into k3s containerd
docker save ebook-tools-backend:latest | \
  limactl shell k3s sudo k3s ctr images import -
docker save ebook-tools-frontend:latest | \
  limactl shell k3s sudo k3s ctr images import -
```

The `deploy` command in `k3s-control.sh` and `make k8s-import-images` handle
this automatically.

**Important**: Set `imagePullPolicy: Never` (via `values-lima.yaml` or
`--set global.imagePullPolicy=Never`) to prevent k3s from trying to pull
images from a registry.

---

## Monitoring Integration

The monitoring stack (Prometheus, Grafana, PG exporter) stays on Docker Compose.
To scrape the k3s backend:

1. Open a port-forward: `scripts/k3s-control.sh ports`
   (exposes backend at `localhost:18000`)
2. Prometheus scrapes `host.docker.internal:18000/metrics` via the
   `k3s-backend` job (configured in `monitoring/prometheus/prometheus.yml`)
3. Dashboard PromQL uses `max without (deployment)` to merge metrics from
   both deployments

The Metrics QA dashboard has a dedicated "k3s POC (Lima VM)" row showing
k3s-specific panels.

---

## Argo CD (Optional GitOps)

Argo CD can be installed in the k3s cluster to enable GitOps-style deployment.
It watches the git repository and auto-syncs the Helm chart to the cluster.

### Setup

```bash
# Install Argo CD
make argocd-install

# Create the Application CR
make argocd-app

# Open the Argo CD UI (blocks terminal)
make argocd-ui
# => https://localhost:8080

# Get the initial admin password
make argocd-password
```

### Application Configuration

The `ApplicationCR` is defined in `helm/argocd/application.yaml`:

- **Source**: `https://github.com/fifosk/ebook-tools.git` at `HEAD`
- **Path**: `helm/ebook-tools`
- **Sync**: Manual by default (click "Sync" in UI or `argocd app sync`)
- **Auto-sync**: Uncomment the `automated` block for true GitOps:

```yaml
syncPolicy:
  automated:
    prune: true       # delete resources removed from git
    selfHeal: true    # revert manual kubectl changes
```

### Makefile Targets

```bash
make argocd-install    # Install Argo CD manifests
make argocd-app        # Create Application CR
make argocd-ui         # Port-forward Argo CD UI to :8080
make argocd-password   # Print initial admin password
make argocd-teardown   # Remove Application CR + Argo CD namespace
```

---

## Comparing Deployments

| Aspect | Docker Compose | k3s (Helm) |
|--------|---------------|------------|
| **Status** | Primary (production) | POC |
| **Runtime** | Docker Engine | Lima VM + k3s |
| **Monitoring** | Integrated | Scraped via port-forward |
| **TLS** | Synology DSM reverse proxy | Traefik ingress (no TLS termination yet) |
| **Storage** | Host bind mounts | hostPath PVs (Lima VM paths) |
| **Image delivery** | Local build | `docker save` + `k3s ctr images import` |
| **GitOps** | Manual `docker compose up` | Optional Argo CD |
| **Access** | `:5173` (frontend), `:8000` (backend) | `:15173`, `:18000` (port-forward) |

---

## Directory Structure

```
helm/
├── ebook-tools/
│   ├── Chart.yaml             # Chart metadata
│   ├── values.yaml            # Default values (production paths)
│   ├── values-lima.yaml       # Lima VM overrides
│   └── templates/             # Kubernetes manifests (10 files)
└── argocd/
    ├── application.yaml       # Argo CD ApplicationCR
    └── README.md              # Quick start guide

scripts/
└── k3s-control.sh             # Lima VM + k3s lifecycle manager
```

---

## Troubleshooting

### VM won't start

```bash
limactl list                    # check VM state
limactl stop k3s && limactl start k3s  # restart
```

### kubectl can't connect

```bash
# Verify SSH tunnel is running
ps aux | grep "ssh.*6443"

# Re-establish tunnel
ssh -f -N -L 6443:127.0.0.1:6443 -F ~/.lima/k3s/ssh.config lima-k3s
```

### Pods stuck in ImagePullBackOff

Images were not imported or `imagePullPolicy` is not `Never`:

```bash
# Re-import images
make k8s-import-images

# Verify images are present
limactl shell k3s sudo k3s ctr images list | grep ebook-tools
```

### Backend pod CrashLoopBackOff

```bash
# Check logs
kubectl logs -n ebook-tools -l app.kubernetes.io/component=backend --previous

# Check if PG is ready
kubectl get pods -n ebook-tools -l app.kubernetes.io/component=postgres
```

### Port-forward disconnects

Port-forwards can drop on network changes. Re-run:

```bash
scripts/k3s-control.sh ports
```
