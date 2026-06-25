from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
API_CLIENT_LIBRARY_JOBS = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Services"
    / "APIClient+LibraryJobs.swift"
)
LIBRARY_JOB_API_MODELS = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Models"
    / "LibraryJobApiModels.swift"
)
JOBS_VIEW = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Jobs"
    / "JobsView.swift"
)
JOBS_VIEW_MODEL = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Jobs"
    / "JobsViewModel.swift"
)
PLAN_DOC = ROOT / "docs" / "plans" / "cross-surface-parity-and-optimization.md"
MAKEFILE = ROOT / "Makefile"


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_apple_jobs_restart_uses_existing_pipeline_action_contract() -> None:
    api_source = _source(API_CLIENT_LIBRARY_JOBS)
    models_source = _source(LIBRARY_JOB_API_MODELS)

    assert "struct PipelineJobActionResponse: Decodable" in models_source
    assert "let job: PipelineStatusResponse" in models_source
    assert "func restartJob(jobId: String) async throws -> PipelineStatusResponse" in api_source
    assert '"/api/pipelines/jobs/\\(encoded)/restart"' in api_source
    assert 'method: "POST"' in api_source
    assert "decode(PipelineJobActionResponse.self, from: data).job" in api_source


def test_apple_jobs_expose_tv_safe_restart_context_menu_action() -> None:
    view_source = _source(JOBS_VIEW)
    view_model_source = _source(JOBS_VIEW_MODEL)

    assert "restartJobAction(for: job)" in view_source
    assert "private func restartJobAction(for job: PipelineStatusResponse) -> some View" in view_source
    assert 'Label("Restart Job", systemImage: "arrow.clockwise")' in view_source
    assert ".disabled(!canRestartJob(job) || viewModel.restartingJobId != nil)" in view_source
    assert "private func canRestartJob(_ job: PipelineStatusResponse) -> Bool" in view_source
    assert "let type = job.jobType.lowercased()" in view_source
    assert 'let supportedType = type == "pipeline" || type == "book"' in view_source
    assert "job.status == .failed || job.status == .cancelled" in view_source
    assert "confirmationDialog(" in view_source
    assert '"Restart job?"' in view_source
    assert 'Text("Generated outputs will be overwritten using the same settings.")' in view_source
    assert "private func handleRestartJobRequest(_ job: PipelineStatusResponse)" in view_source
    assert "private func handleRestartJob(_ job: PipelineStatusResponse) async" in view_source
    assert "refreshResumeStatus()" in view_source

    assert "@Published var restartingJobId: String?" in view_model_source
    assert "func restart(jobId: String, using appState: AppState) async -> Bool" in view_model_source
    assert "let restarted = try await client.restartJob(jobId: jobId)" in view_model_source
    assert "upsert(job: restarted)" in view_model_source
    assert "private func upsert(job: PipelineStatusResponse)" in view_model_source


def test_apple_job_restart_parity_is_documented_and_gated() -> None:
    plan_source = _source(PLAN_DOC)
    makefile_source = _source(MAKEFILE)

    assert "Apple Jobs on iPhone, iPad, and Apple TV now expose a Restart Job" in plan_source
    assert "tests/test_apple_job_restart_contract.py" in makefile_source
