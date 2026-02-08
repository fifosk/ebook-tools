# Argo CD — GitOps for ebook-tools

Optional layer that watches this git repo and auto-syncs the Helm chart to k3s.

## Quick Start

```bash
# 1. Install Argo CD into the cluster
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# 2. Wait for Argo CD to start
kubectl -n argocd wait --for=condition=available deploy/argocd-server --timeout=120s

# 3. Get the admin password
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath='{.data.password}' | base64 -d; echo

# 4. Port-forward the UI
kubectl -n argocd port-forward svc/argocd-server 8080:443 &

# 5. Open https://localhost:8080 (username: admin)

# 6. Register the Application
kubectl apply -f helm/argocd/application.yaml
```

## What It Does

```
Push to git ──→ Argo CD detects change ──→ helm upgrade ──→ cluster updated
                     │
                     └── Dashboard shows: sync status, health, dependency graph
```

## Sync Modes

- **Manual** (default in `application.yaml`): You click "Sync" in the UI or run `argocd app sync ebook-tools`
- **Automated**: Uncomment `automated:` block in `application.yaml` for true GitOps (auto-deploy on push)

## Teardown

```bash
kubectl delete -f helm/argocd/application.yaml
kubectl delete namespace argocd
```
