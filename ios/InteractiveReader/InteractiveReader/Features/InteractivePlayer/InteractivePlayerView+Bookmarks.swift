import SwiftUI

extension InteractivePlayerView {
    @ViewBuilder
    func bookmarkMenu(for chunk: InteractiveChunk) -> some View {
        if canUseBookmarks {
            Menu {
                Button("Add Bookmark") {
                    addBookmark(for: chunk)
                }
                if bookmarks.isEmpty {
                    Text("No bookmarks yet.")
                        .foregroundStyle(.secondary)
                } else {
                    Section("Jump") {
                        ForEach(bookmarks) { bookmark in
                            Button(bookmark.label) {
                                jumpToBookmark(bookmark)
                            }
                        }
                    }
                    Section("Remove") {
                        ForEach(bookmarks) { bookmark in
                            Button(role: .destructive) {
                                removeBookmark(bookmark)
                            } label: {
                                Text(bookmark.label)
                            }
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

    func refreshBookmarks() {
        guard let jobId = resolvedBookmarkJobId else {
            bookmarks = []
            return
        }
        bookmarks = PlaybackBookmarkStore.shared.bookmarks(for: jobId, userId: resolvedBookmarkUserId)
        guard let configuration = appState.configuration else { return }
        Task {
            await syncRemoteBookmarks(jobId: jobId, configuration: configuration)
        }
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
        let sentenceNumber = selectedSentenceID ?? activeSentence?.displayIndex ?? activeSentence?.id
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
        guard let configuration = appState.configuration else {
            PlaybackBookmarkStore.shared.addBookmark(entry, userId: resolvedBookmarkUserId)
            return
        }
        Task {
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
                let stored = PlaybackBookmarkEntry(
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
                PlaybackBookmarkStore.shared.addBookmark(stored, userId: resolvedBookmarkUserId)
            } catch {
                PlaybackBookmarkStore.shared.addBookmark(entry, userId: resolvedBookmarkUserId)
            }
        }
    }

    func jumpToBookmark(_ bookmark: PlaybackBookmarkEntry) {
        if let sentence = bookmark.sentenceNumber, sentence > 0 {
            viewModel.jumpToSentence(sentence, autoPlay: audioCoordinator.isPlaybackRequested)
            return
        }
        guard let chunkId = bookmark.chunkId,
              let time = bookmark.playbackTime,
              let context = viewModel.jobContext,
              let chunk = context.chunk(withID: chunkId) else {
            return
        }
        if viewModel.selectedChunk?.id != chunkId {
            viewModel.selectChunk(id: chunkId, autoPlay: audioCoordinator.isPlaybackRequested)
        }
        DispatchQueue.main.async {
            viewModel.seekPlayback(to: time, in: chunk)
        }
    }

    func removeBookmark(_ bookmark: PlaybackBookmarkEntry) {
        guard let jobId = resolvedBookmarkJobId else { return }
        guard let configuration = appState.configuration else {
            PlaybackBookmarkStore.shared.removeBookmark(
                id: bookmark.id,
                jobId: jobId,
                userId: resolvedBookmarkUserId
            )
            return
        }
        Task {
            let client = APIClient(configuration: configuration)
            do {
                let response = try await client.deletePlaybackBookmark(jobId: jobId, bookmarkId: bookmark.id)
                if response.deleted {
                    PlaybackBookmarkStore.shared.removeBookmark(
                        id: bookmark.id,
                        jobId: jobId,
                        userId: resolvedBookmarkUserId
                    )
                }
            } catch {
                return
            }
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
