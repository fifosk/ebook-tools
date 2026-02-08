.PHONY: test test-fast test-audio test-translation test-webapi test-services \
       test-pipeline test-cli test-auth test-library test-render test-media \
       test-config test-metadata test-changed \
       test-e2e test-e2e-headless test-e2e-web test-e2e-web-headless \
       test-e2e-ios test-e2e-iphone test-e2e-ipad test-e2e-tvos \
       test-e2e-all test-e2e-apple-parallel \
       docker-build-backend docker-build-frontend docker-build \
       docker-up docker-down docker-logs docker-status \
       monitoring-up monitoring-down monitoring-logs monitoring-status \
       test-observability \
       k8s-build k8s-import-images k8s-deploy k8s-status k8s-logs k8s-teardown k8s-lint \
       argocd-install argocd-app argocd-ui argocd-password argocd-teardown

# ── Full suite ───────────────────────────────────────────────────────────
test:
	pytest

# ── Skip slow / integration tests ───────────────────────────────────────
test-fast:
	pytest -m "not slow and not integration"

# ── Domain markers ───────────────────────────────────────────────────────
test-audio:
	pytest -m audio

test-translation:
	pytest -m translation

test-webapi:
	pytest -m webapi

test-services:
	pytest -m services

test-pipeline:
	pytest -m pipeline

test-cli:
	pytest -m cli

test-auth:
	pytest -m auth

test-library:
	pytest -m library

test-render:
	pytest -m render

test-media:
	pytest -m media

test-config:
	pytest -m config

test-metadata:
	pytest -m metadata

test-observability:
	pytest -m observability -v

# ── E2E browser tests (Playwright) ────────────────────────────────────
# Artifacts (screenshots, traces) written to test-results/ (gitignored)
E2E_ARGS = -m e2e -o "addopts=-rs" --screenshot=on --full-page-screenshot --tracing=retain-on-failure

# Legacy targets (backward compat)
test-e2e:
	pytest $(E2E_ARGS) --e2e-report --headed --slowmo=200

test-e2e-headless:
	pytest $(E2E_ARGS) --e2e-report

# Named Web targets with custom report title
test-e2e-web:
	pytest $(E2E_ARGS) --headed --slowmo=200 \
		--e2e-report=test-results/web-e2e-report.md \
		--e2e-report-title="Web E2E Test Report"

test-e2e-web-headless:
	pytest $(E2E_ARGS) \
		--e2e-report=test-results/web-e2e-report.md \
		--e2e-report-title="Web E2E Test Report"

# ── Apple E2E tests (XCUITest) ────────────────────────────────────────
XCBUILD = /Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild
XCPROJ = ios/InteractiveReader/InteractiveReader.xcodeproj
JOURNEY_SRC = tests/e2e/journeys/basic_playback.json

# Write config + journey to /tmp (idempotent, parallel-safe)
define WRITE_E2E_CONFIG
python -c "import json; from pathlib import Path; \
	env={}; \
	[env.update(dict([l.strip().split('=',1)])) for l in Path('.env').read_text().splitlines() if '=' in l and not l.startswith('#')]; \
	Path('/tmp/ios_e2e_config.json').write_text(json.dumps({ \
		'username': env.get('E2E_USERNAME',''), \
		'password': env.get('E2E_PASSWORD',''), \
		'api_base_url': env.get('E2E_API_BASE_URL','https://api.langtools.fifosk.synology.me') \
	}))" && cp $(JOURNEY_SRC) /tmp/ios_e2e_journey.json
endef

# ── iPhone E2E ───────────────────────────────────────────────────────
IPHONE_DESTINATION = 'platform=iOS Simulator,name=iPhone 17 Pro'
IPHONE_E2E_RESULT = $(CURDIR)/test-results/iphone-e2e.xcresult

test-e2e-iphone:
	@rm -rf $(IPHONE_E2E_RESULT) test-results/iphone-e2e-attachments
	@$(WRITE_E2E_CONFIG)
	$(XCBUILD) test \
		-project $(XCPROJ) \
		-scheme InteractiveReaderUITests \
		-destination $(IPHONE_DESTINATION) \
		-resultBundlePath $(IPHONE_E2E_RESULT) \
		2>&1 | tail -30
	python scripts/ios_e2e_report.py \
		--xcresult $(IPHONE_E2E_RESULT) \
		--output test-results/iphone-e2e-report.md \
		--title "iPhone E2E Test Report" \
		--screenshot-prefix iphone
	@rm -f /tmp/ios_e2e_config.json /tmp/ios_e2e_journey.json

# ── iPad E2E ─────────────────────────────────────────────────────────
IPAD_DESTINATION = 'platform=iOS Simulator,name=iPad Air 11-inch (M3)'
IPAD_E2E_RESULT = $(CURDIR)/test-results/ipad-e2e.xcresult

test-e2e-ipad:
	@rm -rf $(IPAD_E2E_RESULT) test-results/ipad-e2e-attachments
	@$(WRITE_E2E_CONFIG)
	$(XCBUILD) test \
		-project $(XCPROJ) \
		-scheme InteractiveReaderUITests \
		-destination $(IPAD_DESTINATION) \
		-resultBundlePath $(IPAD_E2E_RESULT) \
		2>&1 | tail -30
	python scripts/ios_e2e_report.py \
		--xcresult $(IPAD_E2E_RESULT) \
		--output test-results/ipad-e2e-report.md \
		--title "iPad E2E Test Report" \
		--screenshot-prefix ipad
	@rm -f /tmp/ios_e2e_config.json /tmp/ios_e2e_journey.json

# ── tvOS E2E ─────────────────────────────────────────────────────────
TVOS_DESTINATION = 'platform=tvOS Simulator,name=Apple TV'
TVOS_E2E_RESULT = $(CURDIR)/test-results/tvos-e2e.xcresult

test-e2e-tvos:
	@rm -rf $(TVOS_E2E_RESULT) test-results/tvos-e2e-attachments
	@$(WRITE_E2E_CONFIG)
	$(XCBUILD) test \
		-project $(XCPROJ) \
		-scheme InteractiveReaderTVUITests \
		-destination $(TVOS_DESTINATION) \
		-resultBundlePath $(TVOS_E2E_RESULT) \
		2>&1 | tail -30
	python scripts/ios_e2e_report.py \
		--xcresult $(TVOS_E2E_RESULT) \
		--output test-results/tvos-e2e-report.md \
		--title "tvOS E2E Test Report" \
		--screenshot-prefix tvos
	@rm -f /tmp/ios_e2e_config.json /tmp/ios_e2e_journey.json

# ── Legacy alias ─────────────────────────────────────────────────────
test-e2e-ios: test-e2e-iphone

# ── Run all platforms sequentially ────────────────────────────────────
# Parallel execution (-j4) corrupts xcresult bundles (Xcode mkstemp bug),
# so we run sequentially.  Use -k to continue on failures.
test-e2e-all:
	@$(WRITE_E2E_CONFIG)
	@$(MAKE) -k \
		test-e2e-web-headless \
		test-e2e-iphone \
		test-e2e-ipad \
		test-e2e-tvos \
		; EXIT=$$?; \
	rm -f /tmp/ios_e2e_config.json /tmp/ios_e2e_journey.json; \
	exit $$EXIT

# ── Docker ──────────────────────────────────────────────────────────
DOCKER_TAG ?= latest
BACKEND_IMAGE = ebook-tools-backend
FRONTEND_IMAGE = ebook-tools-frontend

docker-build-backend:
	docker build -t $(BACKEND_IMAGE):$(DOCKER_TAG) -f docker/backend/Dockerfile .

docker-build-frontend:
	docker build -t $(FRONTEND_IMAGE):$(DOCKER_TAG) -f docker/frontend/Dockerfile \
		--build-arg VITE_API_BASE_URL=https://api.langtools.fifosk.synology.me \
		--build-arg VITE_STORAGE_BASE_URL=https://api.langtools.fifosk.synology.me/storage/jobs \
		.

docker-build: docker-build-backend docker-build-frontend

docker-up:
	docker compose up -d

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f

docker-status:
	@docker compose ps
	@echo ""
	@echo "Backend health:"
	@curl -sf http://localhost:8000/_health 2>/dev/null || echo "  not reachable"
	@echo ""
	@echo "Frontend:"
	@curl -sf -o /dev/null -w "  HTTP %{http_code}" http://localhost:5173/ 2>/dev/null || echo "  not reachable"
	@echo ""
	@echo "Monitoring:"
	@curl -sf http://localhost:9090/-/healthy 2>/dev/null && echo "  Prometheus: healthy" || echo "  Prometheus: not reachable"
	@curl -sf -o /dev/null -w "  Grafana: HTTP %{http_code}\n" http://localhost:3000/api/health 2>/dev/null || echo "  Grafana: not reachable"
	@echo ""

# ── Monitoring ────────────────────────────────────────────────────────────
monitoring-up:
	docker compose up -d prometheus grafana postgres-exporter

monitoring-down:
	docker compose stop prometheus grafana postgres-exporter

monitoring-logs:
	docker compose logs -f prometheus grafana postgres-exporter

monitoring-status:
	@echo "Prometheus:"
	@curl -sf http://localhost:9090/-/healthy 2>/dev/null && echo "  healthy" || echo "  not reachable"
	@echo "Grafana:"
	@curl -sf -o /dev/null -w "  HTTP %{http_code}\n" http://localhost:3000/api/health 2>/dev/null || echo "  not reachable"
	@echo "Postgres Exporter:"
	@curl -sf -o /dev/null -w "  HTTP %{http_code}\n" http://localhost:9187/metrics 2>/dev/null || echo "  not reachable"

# ── Database helpers ──────────────────────────────────────────────────────
db-shell:
	docker exec -it ebook-tools-postgres psql -U ebook_tools -d ebook_tools

db-migrate:
	docker exec ebook-tools-backend alembic upgrade head

# ── Kubernetes / Helm (POC) ──────────────────────────────────────────────
K8S_NAMESPACE ?= ebook-tools
HELM_RELEASE  ?= ebook-tools
HELM_CHART    ?= helm/ebook-tools

k8s-build: docker-build
	@echo "Images built. Import into k3s with: make k8s-import-images"

k8s-import-images:
	docker save ebook-tools-backend:latest | limactl shell k3s sudo k3s ctr images import -
	docker save ebook-tools-frontend:latest | limactl shell k3s sudo k3s ctr images import -
	@echo "Images imported into k3s."

k8s-deploy:
	helm upgrade --install $(HELM_RELEASE) $(HELM_CHART) \
		--namespace $(K8S_NAMESPACE) --create-namespace \
		--set global.imagePullPolicy=Never

k8s-status:
	@echo "=== Pods ==="
	@kubectl -n $(K8S_NAMESPACE) get pods
	@echo ""
	@echo "=== Services ==="
	@kubectl -n $(K8S_NAMESPACE) get svc
	@echo ""
	@echo "=== Ingress ==="
	@kubectl -n $(K8S_NAMESPACE) get ingress
	@echo ""
	@echo "=== PVCs ==="
	@kubectl -n $(K8S_NAMESPACE) get pvc
	@echo ""
	@echo "=== CronJobs ==="
	@kubectl -n $(K8S_NAMESPACE) get cronjobs

k8s-logs:
	kubectl -n $(K8S_NAMESPACE) logs -l app.kubernetes.io/component=backend -f --tail=100

k8s-teardown:
	helm uninstall $(HELM_RELEASE) --namespace $(K8S_NAMESPACE)

k8s-lint:
	helm lint $(HELM_CHART)
	helm template $(HELM_RELEASE) $(HELM_CHART) > /dev/null && echo "Template rendering: OK"

# ── Argo CD (optional GitOps layer) ─────────────────────────────────────
argocd-install:
	kubectl create namespace argocd 2>/dev/null || true
	kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
	@echo "Waiting for Argo CD server..."
	kubectl -n argocd wait --for=condition=available deploy/argocd-server --timeout=180s
	@echo "Argo CD installed. Run 'make argocd-password' for credentials."

argocd-app:
	kubectl apply -f helm/argocd/application.yaml
	@echo "Application registered. Open Argo CD UI with: make argocd-ui"

argocd-ui:
	@echo "Argo CD UI: https://localhost:8080 (admin / $$(make -s argocd-password))"
	kubectl -n argocd port-forward svc/argocd-server 8080:443

argocd-password:
	@kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' 2>/dev/null | base64 -d; echo

argocd-teardown:
	kubectl delete -f helm/argocd/application.yaml 2>/dev/null || true
	kubectl delete namespace argocd 2>/dev/null || true
	@echo "Argo CD removed."
