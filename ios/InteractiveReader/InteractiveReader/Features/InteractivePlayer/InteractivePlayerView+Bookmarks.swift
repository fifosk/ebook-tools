import SwiftUI

extension InteractivePlayerView {
    @ViewBuilder
    func bookmarkMenu(for chunk: InteractiveChunk) -> some View {
        if canUseBookmarks {
            Menu {
                addBookmarkMenuButton(for: chunk)
                if bookmarks.isEmpty {
                    Text("No bookmarks yet.")
                        .foregroundStyle(.secondary)
                } else {
                    Section("Jump") {
                        ForEach(bookmarks) { bookmark in
                            jumpBookmarkMenuButton(bookmark)
                        }
                    }
                    Section("Remove") {
                        ForEach(bookmarks) { bookmark in
                            removeBookmarkMenuButton(bookmark)
                        }
                    }
                }
            } label: {
                menuLabel("Bookmarks", leadingSystemImage: "bookmark")
            }
            .controlSize(.small)
            .focused($focusedArea, equals: .controls)
        }
    }

    @ViewBuilder
    var bookmarkRibbonPillView: some View {
        if canUseBookmarks, let chunk = viewModel.selectedChunk {
            BookmarkRibbonPillView(
                bookmarkCount: bookmarks.count,
                isTV: isTV,
                sizeScale: infoPillScale,
                bookmarks: bookmarks,
                onAddBookmark: { addBookmark(for: chunk) },
                onJumpToBookmark: jumpToBookmark,
                onRemoveBookmark: removeBookmark,
                onUserInteraction: {}
            )
        }
    }

    func addBookmarkMenuButton(for chunk: InteractiveChunk) -> some View {
        Button("Add Bookmark") {
            addBookmarkMenuAction(for: chunk)
        }
    }

    func jumpBookmarkMenuButton(_ bookmark: PlaybackBookmarkEntry) -> some View {
        Button(bookmark.label) {
            jumpToBookmarkMenuAction(bookmark)
        }
    }

    func removeBookmarkMenuButton(_ bookmark: PlaybackBookmarkEntry) -> some View {
        Button(role: .destructive) {
            removeBookmarkMenuAction(bookmark)
        } label: {
            Text(bookmark.label)
        }
    }

    func addBookmarkMenuAction(for chunk: InteractiveChunk) {
        addBookmark(for: chunk)
    }

    func jumpToBookmarkMenuAction(_ bookmark: PlaybackBookmarkEntry) {
        jumpToBookmark(bookmark)
    }

    func removeBookmarkMenuAction(_ bookmark: PlaybackBookmarkEntry) {
        removeBookmark(bookmark)
    }

    func refreshBookmarks() {
        guard let jobId = resolvedBookmarkJobId else {
            bookmarks = []
            return
        }
        bookmarks = PlaybackBookmarkStore.shared.bookmarks(for: jobId, userId: resolvedBookmarkUserId)
        guard let configuration = appState.configuration else { return }
        startRemoteBookmarkSync(jobId: jobId, configuration: configuration)
    }

    func startRemoteBookmarkSync(jobId: String, configuration: APIClientConfiguration) {
        Task { await syncRemoteBookmarks(jobId: jobId, configuration: configuration) }
    }

    func syncRemoteBookmarks(jobId: String, configuration: APIClientConfiguration) async {
        do {
            let client = APIClient(configuration: configuration)
            let response = try await client.fetchPlaybackBookmarks(jobId: jobId)
            let entries = response.bookmarks.map { payload in
                PlaybackBookmarkEntry(
                    id: payload.id,
                    jobId: payload.jobId,
                    itemType: payload.itemType ?? resolvedBookmarkItemType,
                    kind: payload.kind,
                    createdAt: payload.createdAt,
                    label: payload.label,
                    playbackTime: payload.position,
                    sentenceNumber: payload.sentence,
                    chunkId: payload.chunkId,
                    segmentId: payload.segmentId
                )
            }
            PlaybackBookmarkStore.shared.replaceBookmarks(entries, jobId: jobId, userId: resolvedBookmarkUserId)
        } catch {
            return
        }
    }

    func addBookmark(for chunk: InteractiveChunk) {
        guard let jobId = resolvedBookmarkJobId else { return }
        let playbackTime = viewModel.playbackTime(for: chunk)
        let activeSentence = viewModel.activeSentence(at: viewModel.highlightingTime)
        let activeSentenceNumber = activeSentence.flatMap { sentence -> Int? in
            guard let index = chunk.sentences.firstIndex(where: {
                $0.id == sentence.id && $0.displayIndex == sentence.displayIndex
            }) else { return nil }
            return SentencePositionProvider.sentenceNumber(in: chunk, at: index)
        }
        let sentenceNumber = selectedSentenceID ?? activeSentenceNumber
        let labelParts: [String] = {
            var parts: [String] = []
            if let sentenceNumber, sentenceNumber > 0 {
                parts.append("Sentence \(sentenceNumber)")
            }
            if playbackTime.isFinite {
                parts.append(formatBookmarkTime(playbackTime))
            }
            return parts
        }()
        let label = labelParts.isEmpty ? "Bookmark" : labelParts.joined(separator: " · ")
        let entry = PlaybackBookmarkEntry(
            id: UUID().uuidString,
            jobId: jobId,
            itemType: resolvedBookmarkItemType,
            kind: sentenceNumber != nil ? .sentence : .time,
            createdAt: Date().timeIntervalSince1970,
            label: label,
            playbackTime: playbackTime.isFinite ? playbackTime : nil,
            sentenceNumber: sentenceNumber,
            chunkId: chunk.id,
            segmentId: nil
        )
        storeBookmark(entry)
        guard let configuration = appState.configuration else {
            return
        }
        createRemoteBookmark(entry, jobId: jobId, configuration: configuration)
    }

    func storeBookmark(_ entry: PlaybackBookmarkEntry) {
        PlaybackBookmarkStore.shared.addBookmark(entry, userId: resolvedBookmarkUserId)
    }

    func createRemoteBookmark(
        _ entry: PlaybackBookmarkEntry,
        jobId: String,
        configuration: APIClientConfiguration
    ) {
        Task { await createRemoteBookmarkAsync(entry, jobId: jobId, configuration: configuration) }
    }

    func createRemoteBookmarkAsync(
        _ entry: PlaybackBookmarkEntry,
        jobId: String,
        configuration: APIClientConfiguration
    ) async {
        let client = APIClient(configuration: configuration)
        let payload = PlaybackBookmarkCreateRequest(
            id: entry.id,
            label: entry.label,
            kind: entry.kind,
            createdAt: entry.createdAt,
            position: entry.playbackTime,
            sentence: entry.sentenceNumber,
            mediaType: entry.kind == .sentence ? "text" : "audio",
            mediaId: nil,
            baseId: nil,
            segmentId: entry.segmentId,
            chunkId: entry.chunkId,
            itemType: entry.itemType
        )
        do {
            let response = try await client.createPlaybackBookmark(jobId: jobId, payload: payload)
            removeStoredBookmark(entry, jobId: jobId)
            storeBookmark(
                PlaybackBookmarkEntry(
                    id: response.id,
                    jobId: response.jobId,
                    itemType: response.itemType ?? entry.itemType,
                    kind: response.kind,
                    createdAt: response.createdAt,
                    label: response.label,
                    playbackTime: response.position,
                    sentenceNumber: response.sentence,
                    chunkId: response.chunkId,
                    segmentId: response.segmentId
                )
            )
        } catch {
            return
        }
    }

    func jumpToBookmark(_ bookmark: PlaybackBookmarkEntry) {
        let shouldPlay = audioCoordinator.isPlaybackRequested
        clearHeaderSentenceProgressDraft()
        if let chunkId = bookmark.chunkId,
           let time = bookmark.playbackTime,
           let context = viewModel.jobContext,
           let chunk = context.chunk(withID: chunkId) {
            if let sentence = bookmark.sentenceNumber, sentence > 0 {
                prepareExplicitSentenceJump(to: sentence)
            }
            viewModel.jumpToTime(time, in: chunk, autoPlay: shouldPlay)
            return
        }
        if let sentence = bookmark.sentenceNumber, sentence > 0 {
            prepareExplicitSentenceJump(to: sentence)
            viewModel.jumpToSentence(sentence, autoPlay: shouldPlay)
            return
        }
    }

    func removeBookmark(_ bookmark: PlaybackBookmarkEntry) {
        guard let jobId = resolvedBookmarkJobId else { return }
        guard let configuration = appState.configuration else {
            removeStoredBookmark(bookmark, jobId: jobId)
            return
        }
        deleteRemoteBookmark(bookmark, jobId: jobId, configuration: configuration)
    }

    func removeStoredBookmark(_ bookmark: PlaybackBookmarkEntry, jobId: String) {
        PlaybackBookmarkStore.shared.removeBookmark(
            id: bookmark.id,
            jobId: jobId,
            userId: resolvedBookmarkUserId
        )
    }

    func deleteRemoteBookmark(
        _ bookmark: PlaybackBookmarkEntry,
        jobId: String,
        configuration: APIClientConfiguration
    ) {
        Task { await deleteRemoteBookmarkAsync(bookmark, jobId: jobId, configuration: configuration) }
    }

    func deleteRemoteBookmarkAsync(
        _ bookmark: PlaybackBookmarkEntry,
        jobId: String,
        configuration: APIClientConfiguration
    ) async {
        let client = APIClient(configuration: configuration)
        do {
            let response = try await client.deletePlaybackBookmark(jobId: jobId, bookmarkId: bookmark.id)
            if response.deleted {
                removeStoredBookmark(bookmark, jobId: jobId)
            }
        } catch {
            return
        }
    }

    func formatBookmarkTime(_ seconds: Double) -> String {
        let total = max(0, Int(seconds.rounded()))
        let hours = total / 3600
        let minutes = (total % 3600) / 60
        let remainingSeconds = total % 60
        if hours > 0 {
            return String(format: "%d:%02d:%02d", hours, minutes, remainingSeconds)
        }
        return String(format: "%02d:%02d", minutes, remainingSeconds)
    }
}
