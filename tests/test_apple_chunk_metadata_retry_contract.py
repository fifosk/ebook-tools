from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INTERACTIVE = ROOT / "ios" / "InteractiveReader" / "InteractiveReader" / "Features" / "InteractivePlayer"


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_chunk_metadata_loader_records_retryable_failures() -> None:
    view_model = _source(INTERACTIVE / "InteractivePlayerViewModel.swift")
    loading = _source(INTERACTIVE / "InteractivePlayerViewModel+Loading.swift")

    assert "@Published var chunkMetadataFailures: [String: String] = [:]" in view_model
    assert "chunkMetadataFailures = [:]" in loading
    assert "@discardableResult" in loading
    assert "func loadChunkMetadataIfNeeded(for chunkID: String, force: Bool = false) async -> Bool" in loading
    assert "recordChunkMetadataFailure(chunkID)" in loading
    assert "clearChunkMetadataFailure(chunkID)" in loading
    assert "chunkMetadataLoaded.remove(chunkID)" in loading
    assert "Transcript metadata could not be loaded. Check the connection and try again." in loading


def test_selected_chunk_metadata_retry_prepares_audio_after_success() -> None:
    loading = _source(INTERACTIVE / "InteractivePlayerViewModel+Loading.swift")

    assert "func retrySelectedChunkMetadataLoad(autoPlay: Bool = false)" in loading
    assert "chunkMetadataAttemptedAt[chunkID] = nil" in loading
    assert "let didLoad = await self.loadChunkMetadataIfNeeded(for: chunkID, force: true)" in loading
    assert "self.isTranscriptLoading = false" in loading
    assert "guard didLoad, let updatedChunk = self.selectedChunk, self.isTranscriptReady(for: updatedChunk) else" in loading
    assert "self.synchronizeSelectedAudioTrackForChunkHandoff(for: updatedChunk)" in loading
    assert "let targetIndex = self.recentSingleTrackSentenceAnchorIndex(in: updatedChunk)" in loading
    assert "self.prepareAudio(for: updatedChunk, autoPlay: autoPlay, targetSentenceIndex: targetIndex)" in loading


def test_selected_single_track_metadata_hydration_reprepares_even_when_selection_id_is_stable() -> None:
    loading = _source(INTERACTIVE / "InteractivePlayerViewModel+Loading.swift")
    selection = _source(INTERACTIVE / "InteractivePlayerViewModel+Selection.swift")

    assert """if selectedChunkID == chunkID {
                reassertSelectedAudioTrackAfterContextRebuild()
                reprepareSingleTrackAudioAfterContextRebuildIfNeeded(
                    autoPlay: audioCoordinator.isPlaybackRequested
                )""" in loading
    reprepare_body = """func reprepareSingleTrackAudioAfterContextRebuildIfNeeded(autoPlay: Bool) {
        guard let updatedChunk = selectedChunk,
              let track = requestedSingleTrackMode() else {
            return
        }
        applySingleTrackSelection(track, for: updatedChunk)
        let targetIndex = recentSingleTrackSentenceAnchorIndex(in: updatedChunk)
        if let targetIndex {
            rememberSingleTrackSentenceAnchor(in: updatedChunk, targetIndex: targetIndex)
        }
        prepareAudio("""
    assert reprepare_body in selection
    assert "guard let targetIndex = recentSingleTrackSentenceAnchorIndex(in: updatedChunk)" not in selection
    assert "let didReassertAudioSelection = reassertSelectedAudioTrackAfterContextRebuild()" not in loading
    assert "if didReassertAudioSelection," not in loading


def test_transcript_retry_button_is_wired_to_selected_chunk_retry() -> None:
    frame = _source(INTERACTIVE / "TextPlayerViews.swift")
    transcript = _source(INTERACTIVE / "InteractiveTranscriptView.swift")
    content = _source(INTERACTIVE / "InteractivePlayerView+InteractiveContent.swift")

    assert "var loadErrorMessage: String?" in frame
    assert "var onRetryLoad: (() -> Void)?" in frame
    assert 'Button("Retry")' in frame
    assert '.accessibilityIdentifier("interactiveTranscriptRetryButton")' in frame

    assert "let transcriptLoadError: String?" in transcript
    assert "let onRetryTranscriptLoad: (() -> Void)?" in transcript
    assert "loadErrorMessage: transcriptLoadError" in transcript
    assert "onRetryLoad: onRetryTranscriptLoad" in transcript

    assert "transcriptLoadError: effectiveIsLoading ? nil : viewModel.chunkMetadataFailureMessage(for: chunk.id)" in content
    assert "viewModel.retrySelectedChunkMetadataLoad(autoPlay: audioCoordinator.isPlaybackRequested)" in content
