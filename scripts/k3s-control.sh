#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────
# k3s-control.sh — Start / stop / status for the k3s POC cluster
#
# Usage:
#   scripts/k3s-control.sh start    # boot VM + tunnel + verify
#   scripts/k3s-control.sh stop     # gracefully stop VM
#   scripts/k3s-control.sh status   # show VM + pod health
#   scripts/k3s-control.sh ports    # open port-forwards (frontend, backend, argocd)
#   scripts/k3s-control.sh deploy   # rebuild images, import, helm upgrade
#   scripts/k3s-control.sh teardown # helm uninstall (keeps VM)
#   scripts/k3s-control.sh nuke     # stop VM + delete it entirely
#
# Safe: Does NOT affect Docker Compose deployment in any way.
# ──────────────────────────────────────────────────────────────
set -euo pipefail

VM_NAME="k3s"
KUBECONFIG_PATH="$HOME/.lima/${VM_NAME}/copied-from-guest/kubeconfig.yaml"
SSH_CONFIG="$HOME/.lima/${VM_NAME}/ssh.config"
K8S_NAMESPACE="ebook-tools"
HELM_RELEASE="ebook-tools"
HELM_CHART="helm/ebook-tools"

# Colours
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Colour

# ── Helpers ──────────────────────────────────────────────────

info()  { echo -e "${CYAN}▸${NC} $*"; }
ok()    { echo -e "${GREEN}✔${NC} $*"; }
warn()  { echo -e "${YELLOW}⚠${NC} $*"; }
fail()  { echo -e "${RED}✘${NC} $*"; exit 1; }

vm_running() {
    limactl list --format '{{.Name}} {{.Status}}' 2>/dev/null | grep -q "^${VM_NAME} Running"
}

tunnel_running() {
    pgrep -f "ssh.*-L 6443.*lima-${VM_NAME}" >/dev/null 2>&1
}

kill_tunnel() {
    local pids
    pids=$(pgrep -f "ssh.*-L 6443.*lima-${VM_NAME}" 2>/dev/null || true)
    if [[ -n "$pids" ]]; then
        echo "$pids" | xargs kill 2>/dev/null || true
        ok "SSH tunnel stopped"
    fi
}

kill_port_forwards() {
    local pids
    pids=$(pgrep -f "kubectl.*port-forward.*-n ${K8S_NAMESPACE}" 2>/dev/null || true)
    pids+=" $(pgrep -f "kubectl.*port-forward.*-n argocd" 2>/dev/null || true)"
    pids=$(echo "$pids" | xargs)
    if [[ -n "$pids" ]]; then
        echo "$pids" | xargs kill 2>/dev/null || true
        ok "Port-forwards stopped"
    fi
}

ensure_running() {
    vm_running || fail "Lima VM '${VM_NAME}' is not running. Run: $0 start"
    export KUBECONFIG="$KUBECONFIG_PATH"
}

wait_for_kubectl() {
    info "Waiting for kubectl connectivity..."
    local retries=0
    while ! kubectl cluster-info >/dev/null 2>&1; do
        retries=$((retries + 1))
        if [[ $retries -ge 30 ]]; then
            fail "kubectl cannot reach cluster after 30s"
        fi
        sleep 1
    done
    ok "kubectl connected"
}

# ── Commands ─────────────────────────────────────────────────

cmd_start() {
    if vm_running; then
        ok "Lima VM '${VM_NAME}' already running"
    else
        info "Starting Lima VM '${VM_NAME}'..."
        limactl start "$VM_NAME"
        ok "VM started"
    fi

    export KUBECONFIG="$KUBECONFIG_PATH"

    # Check if kubectl already works (Lima may provide direct socket access)
    if kubectl cluster-info >/dev/null 2>&1; then
        ok "kubectl connected (direct socket)"
    elif tunnel_running; then
        ok "SSH tunnel already active"
        wait_for_kubectl
    else
        info "Opening SSH tunnel (port 6443)..."
        ssh -F "$SSH_CONFIG" -L 6443:127.0.0.1:6443 -N "lima-${VM_NAME}" &
        disown
        sleep 1
        if tunnel_running; then
            ok "SSH tunnel opened"
        else
            warn "SSH tunnel may have failed — check manually"
        fi
        wait_for_kubectl
    fi

    info "Waiting for pods to come up..."
    kubectl -n "$K8S_NAMESPACE" wait --for=condition=ready pod -l app.kubernetes.io/instance="$HELM_RELEASE" --timeout=120s 2>/dev/null || true

    echo ""
    cmd_status

    echo ""
    echo -e "${CYAN}─── Quick reference ───${NC}"
    echo "  export KUBECONFIG=$KUBECONFIG_PATH"
    echo "  $0 ports     # open port-forwards"
    echo "  $0 status    # check health"
    echo "  $0 stop      # shut down"
}

cmd_stop() {
    info "Stopping k3s POC..."

    kill_port_forwards
    kill_tunnel

    if vm_running; then
        info "Stopping Lima VM '${VM_NAME}'..."
        limactl stop "$VM_NAME"
        ok "VM stopped"
    else
        ok "VM already stopped"
    fi

    echo ""
    ok "k3s POC is shut down. Docker Compose is unaffected."
}

cmd_status() {
    echo -e "${CYAN}═══ k3s POC Status ═══${NC}"
    echo ""

    # VM status
    if vm_running; then
        ok "Lima VM: Running"
    else
        warn "Lima VM: Stopped"
        echo "  Run: $0 start"
        return
    fi

    export KUBECONFIG="$KUBECONFIG_PATH"

    # kubectl reachable?
    if kubectl cluster-info >/dev/null 2>&1; then
        ok "kubectl: Connected"
        if tunnel_running; then
            ok "SSH tunnel: Active (port 6443)"
        else
            ok "SSH tunnel: Not needed (direct socket)"
        fi
    else
        warn "kubectl: Cannot reach cluster"
        if ! tunnel_running; then
            warn "SSH tunnel: Not running"
            echo "  Run: $0 start"
        fi
        return
    fi

    echo ""

    # Pods
    echo -e "${CYAN}── Pods ──${NC}"
    kubectl -n "$K8S_NAMESPACE" get pods -o wide 2>/dev/null || warn "No pods in namespace $K8S_NAMESPACE"

    echo ""

    # Argo CD (optional)
    if kubectl get namespace argocd >/dev/null 2>&1; then
        echo -e "${CYAN}── Argo CD ──${NC}"
        kubectl -n argocd get pods --no-headers 2>/dev/null | awk '{printf "  %-45s %s\n", $1, $3}'
    fi

    echo ""

    # Port-forwards
    echo -e "${CYAN}── Port Forwards ──${NC}"
    local pf_pids
    pf_pids=$(pgrep -f "kubectl.*port-forward" 2>/dev/null || true)
    if [[ -n "$pf_pids" ]]; then
        ps -p $(echo "$pf_pids" | tr '\n' ',') -o pid,command 2>/dev/null | grep port-forward | while read -r line; do
            echo "  $line"
        done
    else
        echo "  (none active — run: $0 ports)"
    fi
}

cmd_ports() {
    ensure_running
    export KUBECONFIG="$KUBECONFIG_PATH"

    # Kill existing port-forwards to avoid bind errors
    kill_port_forwards
    sleep 1

    info "Opening port-forwards..."

    kubectl port-forward -n "$K8S_NAMESPACE" svc/${HELM_RELEASE}-frontend 15173:80 >/dev/null 2>&1 &
    disown
    kubectl port-forward -n "$K8S_NAMESPACE" svc/${HELM_RELEASE}-backend 18000:8000 >/dev/null 2>&1 &
    disown

    if kubectl get namespace argocd >/dev/null 2>&1; then
        kubectl port-forward -n argocd svc/argocd-server 8080:443 >/dev/null 2>&1 &
        disown
    fi

    sleep 1
    echo ""
    ok "Port-forwards active:"
    echo "  Frontend : http://localhost:15173"
    echo "  Backend  : http://localhost:18000"
    if kubectl get namespace argocd >/dev/null 2>&1; then
        echo "  Argo CD  : https://localhost:8080"
    fi
}

cmd_deploy() {
    ensure_running
    export KUBECONFIG="$KUBECONFIG_PATH"

    info "Building Docker images..."
    docker compose build backend frontend

    info "Importing images into k3s..."
    docker save ebook-tools-backend:latest | limactl shell "$VM_NAME" sudo k3s ctr images import -
    docker save ebook-tools-frontend:latest | limactl shell "$VM_NAME" sudo k3s ctr images import -
    ok "Images imported"

    info "Deploying via Helm..."
    helm upgrade --install "$HELM_RELEASE" "$HELM_CHART" \
        --namespace "$K8S_NAMESPACE" --create-namespace \
        --set global.imagePullPolicy=Never

    info "Restarting deployments to pick up new images..."
    kubectl -n "$K8S_NAMESPACE" rollout restart deployment/${HELM_RELEASE}-backend
    kubectl -n "$K8S_NAMESPACE" rollout restart deployment/${HELM_RELEASE}-frontend

    info "Waiting for rollout..."
    kubectl -n "$K8S_NAMESPACE" rollout status deployment/${HELM_RELEASE}-backend --timeout=120s
    kubectl -n "$K8S_NAMESPACE" rollout status deployment/${HELM_RELEASE}-frontend --timeout=120s

    echo ""
    ok "Deploy complete"
    cmd_status
}

cmd_teardown() {
    ensure_running
    export KUBECONFIG="$KUBECONFIG_PATH"

    kill_port_forwards

    info "Uninstalling Helm release '${HELM_RELEASE}'..."
    helm uninstall "$HELM_RELEASE" --namespace "$K8S_NAMESPACE" 2>/dev/null || warn "Release not found"
    ok "App removed from k3s (VM still running)"
}

cmd_nuke() {
    info "Full teardown: removing everything..."

    kill_port_forwards
    kill_tunnel

    if vm_running; then
        limactl stop "$VM_NAME" 2>/dev/null || true
    fi

    info "Deleting Lima VM '${VM_NAME}'..."
    limactl delete "$VM_NAME" 2>/dev/null || warn "VM not found"
    ok "Lima VM deleted. k3s POC completely removed."
    echo ""
    ok "Docker Compose deployment is unaffected."
}

# ── Main ─────────────────────────────────────────────────────

case "${1:-help}" in
    start)    cmd_start    ;;
    stop)     cmd_stop     ;;
    status)   cmd_status   ;;
    ports)    cmd_ports    ;;
    deploy)   cmd_deploy   ;;
    teardown) cmd_teardown ;;
    nuke)     cmd_nuke     ;;
    help|--help|-h)
        echo "Usage: $0 {start|stop|status|ports|deploy|teardown|nuke}"
        echo ""
        echo "Commands:"
        echo "  start     Start Lima VM, SSH tunnel, wait for pods"
        echo "  stop      Stop port-forwards, tunnel, and VM"
        echo "  status    Show VM, pod, and port-forward health"
        echo "  ports     Open port-forwards (frontend:15173, backend:18000, argocd:8080)"
        echo "  deploy    Build images, import into k3s, helm upgrade, rollout restart"
        echo "  teardown  Helm uninstall (keeps VM running)"
        echo "  nuke      Stop + delete the Lima VM entirely"
        ;;
    *)
        fail "Unknown command: $1 (try: $0 help)"
        ;;
esac
