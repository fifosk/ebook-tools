from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BROWSE_RESUME_HELPERS = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Shared"
    / "BrowseResumeHelpers.swift"
)
PLAYBACK_RESUME_STORE = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Services"
    / "PlaybackResumeStore.swift"
)
PLAYBACK_RESUME_MANAGER = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Playback"
    / "Shared"
    / "PlaybackResumeManager.swift"
)
JOB_PLAYBACK_RESUME = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Playback"
    / "JobPlaybackView+Resume.swift"
)
LIBRARY_PLAYBACK_RESUME = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Playback"
    / "LibraryPlaybackView+Resume.swift"
)
JOB_PLAYBACK_NOW_PLAYING = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Playback"
    / "JobPlaybackView+NowPlaying.swift"
)
LIBRARY_PLAYBACK_NOW_PLAYING = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Playback"
    / "LibraryPlaybackView+NowPlaying.swift"
)
INTERACTIVE_SELECTION = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "InteractivePlayer"
    / "InteractivePlayerViewModel+Selection.swift"
)
SEQUENCE_CONTROLLER = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Services"
    / "SequencePlaybackController.swift"
)
LIBRARY_VIEW = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Library"
    / "LibraryView.swift"
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
COMBINED_SEARCH_VIEW = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Library"
    / "CombinedSearchView.swift"
)
LIBRARY_ROW_COMPONENTS = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Library"
    / "LibraryRowComponents.swift"
)


def test_browse_resume_status_surfaces_local_cloud_and_synced_badges() -> None:
    source = BROWSE_RESUME_HELPERS.read_text(encoding="utf-8")

    assert "private static func resumeEvidenceStatus(" in source
    assert "let localEntry = availability.hasLocal ? availability.localEntry : nil" in source
    assert "let cloudEntry = availability.hasCloud ? availability.cloudEntry : nil" in source
    assert 'return .local(label: resumeLabel(prefix: "L", entry: local))' in source
    assert 'return .cloud(label: resumeLabel(prefix: "C", entry: cloud))' in source
    assert 'return .both(label: resumeLabel(prefix: "B", entry: freshestEntry(local, cloud)))' in source


def test_browse_resume_status_uses_freshest_synced_entry() -> None:
    source = BROWSE_RESUME_HELPERS.read_text(encoding="utf-8")

    assert "private static func freshestEntry(" in source
    assert "first.updatedAt >= second.updatedAt ? first : second" in source
    assert "private static func freshestAvailableEntry(_ availability: PlaybackResumeAvailability)" in source
    assert "let entry = freshestAvailableEntry(availability)" in source
    assert "return freshestEntry(local, cloud)" in source
    assert "availability.cloudEntry ?? availability.localEntry" not in source


def test_browse_resume_status_surfaces_sentence_offsets() -> None:
    source = BROWSE_RESUME_HELPERS.read_text(encoding="utf-8")

    assert 'return "Resume from Sentence \\(sentence) at \\(formatPlaybackTime(time))"' in source
    assert 'return "\\(prefix):\\(sentence)@\\(formatPlaybackTime(time))"' in source
    assert 'return "Resume from Sentence \\(sentence)"' in source
    assert 'return "\\(prefix):\\(sentence)"' in source


def test_browse_resume_status_surfaces_attention_and_new_badges() -> None:
    helper_source = BROWSE_RESUME_HELPERS.read_text(encoding="utf-8")
    row_source = LIBRARY_ROW_COMPONENTS.read_text(encoding="utf-8")
    library_source = LIBRARY_VIEW.read_text(encoding="utf-8")
    jobs_source = JOBS_VIEW.read_text(encoding="utf-8")
    search_source = COMBINED_SEARCH_VIEW.read_text(encoding="utf-8")

    assert "private static let newlyCompletedWindow: TimeInterval = 7 * 24 * 60 * 60" in helper_source
    assert "static func rowStatus(\n        for item: LibraryItem" in helper_source
    assert "static func rowStatus(\n        for job: PipelineStatusResponse" in helper_source
    assert "if let status = resumeEvidenceStatus" in helper_source
    assert "return .needsAttention()" in helper_source
    assert ".newlyCompleted()" in helper_source
    assert "isRecentlyCompleted(updatedAt: item.updatedAt, createdAt: item.createdAt" in helper_source
    assert "isRecentlyCompleted(updatedAt: job.completedAt, createdAt: job.createdAt" in helper_source
    assert "parseAPIDate(updatedAt) ?? parseAPIDate(createdAt)" in helper_source
    assert "label: \"Newly completed\"" in row_source
    assert "label: \"Needs attention\"" in row_source
    assert "for: item,\n            availabilityByJobID: resumeAvailability" in library_source
    assert "for: job,\n            availabilityByJobID: resumeAvailability" in jobs_source
    assert search_source.count("availabilityByJobID: resumeAvailability") >= 2
    assert "for: item,\n            availabilityByJobID: resumeAvailability" in search_source
    assert "for: job,\n            availabilityByJobID: resumeAvailability" in search_source


def test_browse_resume_refresh_batches_backend_visible_rows() -> None:
    helper_source = BROWSE_RESUME_HELPERS.read_text(encoding="utf-8")
    store_source = PLAYBACK_RESUME_STORE.read_text(encoding="utf-8")
    library_source = LIBRARY_VIEW.read_text(encoding="utf-8")
    jobs_source = JOBS_VIEW.read_text(encoding="utf-8")

    assert "visibleItemTypesByJobID: [String: String] = [:]" in helper_source
    assert "PlaybackResumeStore.shared.refreshFromAPI(" in helper_source
    assert "jobIds: Array(visibleItemTypesByJobID.keys)" in helper_source
    assert "func refreshFromAPI(jobIds: [String], itemTypes: [String: String]) async" in store_source
    assert "client.fetchResumePositions(jobIds: cleanedJobIds)" in store_source
    assert "for apiEntry in response.entries" in store_source
    assert "mergeAPIResumeEntry(apiEntry, itemType: itemType)" in store_source
    assert "visibleItemTypesByJobID: visibleResumeItemTypesByJobID()" in library_source
    assert "viewModel.filteredItems.reduce(into: [:])" in library_source
    assert "visibleItemTypesByJobID: visibleResumeItemTypesByJobID()" in jobs_source
    assert "viewModel.filteredJobs.reduce(into: [:])" in jobs_source


def test_interactive_resume_records_sentence_playback_time() -> None:
    manager_source = PLAYBACK_RESUME_MANAGER.read_text(encoding="utf-8")
    job_resume_source = JOB_PLAYBACK_RESUME.read_text(encoding="utf-8")
    store_source = PLAYBACK_RESUME_STORE.read_text(encoding="utf-8")
    job_now_playing_source = JOB_PLAYBACK_NOW_PLAYING.read_text(encoding="utf-8")
    library_now_playing_source = LIBRARY_PLAYBACK_NOW_PLAYING.read_text(encoding="utf-8")

    assert "lastRecordedSentenceTimeBucket" in manager_source
    assert "func recordInteractiveResume(\n        sentenceIndex: Int,\n        playbackTime: Double? = nil," in manager_source
    assert "playbackTime: normalizedPlaybackTime" in manager_source
    assert "recordInteractiveResume(sentenceIndex: resolvedIndex, playbackTime: highlightTime)" in job_now_playing_source
    assert (
        "resumeManager?.recordInteractiveResume(sentenceIndex: resolvedIndex, playbackTime: highlightTime)"
        in library_now_playing_source
    )
    assert "let position = entry.playbackTime" not in store_source
    assert "position: entry.playbackTime" in store_source
    assert "return (sentenceNumber ?? 0) > 1 || (playbackTime ?? 0) > 1" in store_source
    assert "playbackTime: currentInteractiveResumePlaybackTime()" in job_resume_source


def test_interactive_resume_applies_valid_saved_time_before_sentence_fallback() -> None:
    job_resume_source = JOB_PLAYBACK_RESUME.read_text(encoding="utf-8")
    library_resume_source = LIBRARY_PLAYBACK_RESUME.read_text(encoding="utf-8")
    selection_source = INTERACTIVE_SELECTION.read_text(encoding="utf-8")
    sequence_source = SEQUENCE_CONTROLLER.read_text(encoding="utf-8")

    for source in (job_resume_source, library_resume_source):
        assert "startInteractivePlayback(at: entry.sentenceNumber, playbackTime: entry.playbackTime)" in source
        assert "validatedInteractiveResumePlaybackTime(playbackTime, sentenceNumber: sentence)" in source
        assert "matchingSentenceNumber: sentence" in source
        assert "viewModel.jumpToSentence(sentence, autoPlay: true)" in source

    assert "func jumpToTime(" in selection_source
    assert "matchingSentenceNumber sentenceNumber: Int? = nil" in selection_source
    assert "seekSequencePlaybackWhenReady(" in selection_source
    assert "sequenceController.seekToTime(" in selection_source
    assert "sequenceController.seekToTime(\n                time,\n                sentenceIndex: targetSentenceIndex" in selection_source
    assert "preferredTrack: sequenceController.currentTrack" in selection_source
    assert "selectChunk(id: chunk.id, autoPlay: false)" in selection_source
    assert "func resumePlaybackTime(_ time: Double, matches sentenceNumber: Int, in chunk: InteractiveChunk) -> Bool" in selection_source
    assert "resumeValidationTimingTracks(for: chunk)" in selection_source
    assert "chunk.audioOptions.contains(where: { $0.kind == .combined })" in selection_source
    assert "for candidate in [TextPlayerTimingTrack.original, .translation, .mix]" in selection_source
    assert "SentencePositionProvider.sentenceNumber(" in selection_source
    assert "if resolved == sentenceNumber" in selection_source
    assert "if resolvedAnyTimingTrack" in selection_source
    assert "func seekToTime(" in sequence_source
    assert "findTimeTarget(" in sequence_source
    assert "currentSegmentIndex = target.segmentIndex" in sequence_source
    assert "let preferred = preferredTrack ?? currentTrack" in sequence_source
    assert "if let sentenceIndex, segment.sentenceIndex != sentenceIndex" in sequence_source
    assert "let clamped = min(max(time, match.segment.start), match.segment.end)" in sequence_source
    assert "return (match.segmentIndex, match.segment.track, clamped)" in sequence_source

    exact_time_index = selection_source.index("sequenceController.seekToTime(")
    fallback_index = selection_source.index("Interactive sequence time seek fallback=sentenceStart")
    assert exact_time_index < fallback_index
    assert '"[PlaybackTransport] Interactive sequence time seek accepted sentence=\\(sentenceNumber ?? -1) time=\\(String(format: "%.3f", target.time)) track=\\(target.track.rawValue)"' in selection_source


def test_reader_transport_resume_rebuild_uses_current_sentence_offset() -> None:
    job_now_playing = JOB_PLAYBACK_NOW_PLAYING.read_text(encoding="utf-8")
    library_now_playing = LIBRARY_PLAYBACK_NOW_PLAYING.read_text(encoding="utf-8")
    library_view = (
        ROOT
        / "ios"
        / "InteractiveReader"
        / "InteractiveReader"
        / "Features"
        / "Playback"
        / "LibraryPlaybackView.swift"
    ).read_text(encoding="utf-8")

    for source in (job_now_playing, library_now_playing, library_view):
        assert "playbackTime: currentInteractiveResumePlaybackTime()" in source

    for source in (job_now_playing, library_now_playing):
        assert "restoring narration playback request" in source
        restore_index = source.index("restoring narration playback request")
        offset_index = source.index("playbackTime: currentInteractiveResumePlaybackTime()", restore_index)
        assert restore_index < offset_index
