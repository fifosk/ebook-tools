from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INTERACTIVE = ROOT / "ios" / "InteractiveReader" / "InteractiveReader" / "Features" / "InteractivePlayer"
PLAYBACK = ROOT / "ios" / "InteractiveReader" / "InteractiveReader" / "Features" / "Playback"
MODELS = ROOT / "ios" / "InteractiveReader" / "InteractiveReader" / "Models"


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_active_job_playback_prefers_live_media_but_falls_back_to_snapshot() -> None:
    loading = _source(INTERACTIVE / "InteractivePlayerViewModel+Loading.swift")

    assert "fetchInitialJobMediaData(" in loading
    assert "preferLiveMedia: preferLiveMedia" in loading
    assert "private func fetchInitialJobMediaData(" in loading
    assert "guard preferLiveMedia else" in loading
    assert "return try await client.fetchJobMediaLiveData(jobId: jobId)" in loading
    assert "catch is CancellationError" in loading
    assert "return try await client.fetchJobMediaData(jobId: jobId)" in loading


def test_job_playback_still_uses_live_media_for_active_online_jobs() -> None:
    loading = _source(PLAYBACK / "JobPlaybackView+Loading.swift")

    assert "preferLiveMedia: currentJob.status.isActive" in loading
    assert "viewModel.startLiveUpdates()" in loading
    assert "if currentJob.status.isActive" in loading
    assert "viewModel.stopLiveUpdates()" in loading


def test_pipeline_media_decoder_requires_manifest_shape() -> None:
    source = _source(MODELS / "PipelineMediaApiModels.swift")

    assert "media = try container.decode([String: [PipelineMediaFile]].self, forKey: .media)" in source
    assert "chunks = try container.decode([PipelineMediaChunk].self, forKey: .chunks)" in source
    assert "complete = try container.decode(Bool.self, forKey: .complete)" in source
    assert "diagnostics = try container.decode(PipelineMediaDiagnostics.self, forKey: .diagnostics)" in source
    assert "name = try container.decode(String.self, forKey: .name)" in source
    assert "source = try container.decode(String.self, forKey: .source)" in source
    assert "files = try container.decode([PipelineMediaFile].self, forKey: .files)" in source
    assert "sentences = try container.decode([ChunkSentenceMetadata].self, forKey: .sentences)" in source
    assert "audioTracks = try container.decode([String: AudioTrackMetadata].self, forKey: .audioTracks)" in source
    assert "?? [:]" not in source
    assert "?? []" not in source
