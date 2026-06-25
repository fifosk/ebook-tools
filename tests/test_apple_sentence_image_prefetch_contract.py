from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INTERACTIVE = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "InteractivePlayer"
)
VIEW_MODEL = INTERACTIVE / "InteractivePlayerViewModel.swift"
LOADING = INTERACTIVE / "InteractivePlayerViewModel+Loading.swift"
MEDIA = INTERACTIVE / "InteractivePlayerViewModel+Media.swift"
PREFETCH = INTERACTIVE / "InteractivePlayerViewModel+Prefetch.swift"
MENU = INTERACTIVE / "InteractivePlayerView+Menu.swift"


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_sentence_image_resolution_is_shared_between_reel_and_prefetch() -> None:
    media = _source(MEDIA)
    menu = _source(MENU)

    assert "func resolveSentenceImageURL(sentence: InteractiveChunk.Sentence, chunk: InteractiveChunk) -> URL?" in media
    assert "func sentenceImagePath(sentence: InteractiveChunk.Sentence, chunk: InteractiveChunk) -> String?" in media
    assert "if let rawPath = sentence.imagePath, let path = rawPath.nonEmptyValue" in media
    assert 'return "media/images/\\(rangeFragment)/sentence_\\(padded).png"' in media

    assert "viewModel.sentenceImagePath(sentence: sentence, chunk: chunk)" in menu
    assert "viewModel.resolveSentenceImageURL(sentence: sentence, chunk: chunk)" in menu
    assert "func resolveSentenceImagePath" not in menu


def test_sentence_image_prefetch_is_bounded_and_near_active_sentence() -> None:
    view_model = _source(VIEW_MODEL)
    loading = _source(LOADING)
    prefetch = _source(PREFETCH)

    assert "var prefetchedImageURLs: Set<URL> = []" in view_model
    assert "prefetchedImageURLs = []" in loading

    assert "private static let imagePrefetchRadius = 3" in prefetch
    assert "private static let maxImagePrefetchPerBatch = 8" in prefetch
    assert "prefetchSentenceImages(" in prefetch
    assert "around: sentenceNumber" in prefetch
    assert "let lowerBound = sentenceNumber - Self.imagePrefetchRadius" in prefetch
    assert "let upperBound = sentenceNumber + Self.imagePrefetchRadius" in prefetch
    assert "urls.count >= Self.maxImagePrefetchPerBatch" in prefetch
    assert "prefetchedImageURLs.formUnion(urls)" in prefetch


def test_sentence_image_prefetch_runs_after_metadata_refresh_and_warms_file_or_http_urls() -> None:
    prefetch = _source(PREFETCH)

    assert "let refreshedChunk = jobContext?.chunk(withID: chunk.id) ?? chunk" in prefetch
    assert "prefetchChunkMediaIfNeeded(for: refreshedChunk)" in prefetch
    assert "jobContext?.chunk(withID: $0.id) ?? $0" in prefetch

    assert "func prefetchImageURL(_ url: URL)" in prefetch
    assert "if url.isFileURL" in prefetch
    assert "Data(contentsOf: url, options: .mappedIfSafe)" in prefetch
    assert "request.cachePolicy = .returnCacheDataElseLoad" in prefetch
    assert "URLSession.shared.data(for: request)" in prefetch
