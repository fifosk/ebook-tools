import Foundation

extension InteractivePlayerViewModel {
    func loadJob(
        jobId: String,
        configuration: APIClientConfiguration,
        origin: MediaOrigin = .job,
        preferLiveMedia: Bool = false,
        mediaOverride: PipelineMediaResponse? = nil,
        timingOverride: JobTimingResponse? = nil,
        resolverOverride: MediaURLResolver? = nil
    ) async {
        let trimmedJobId = jobId.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmedJobId.isEmpty else {
            loadState = .error("Enter a job identifier before loading.")
            return
        }

        loadState = .loading
        self.jobId = trimmedJobId
        apiBaseURL = configuration.apiBaseURL
        authToken = configuration.authToken
        readingBedBaseURL = nil
        apiConfiguration = configuration
        mediaOrigin = origin
        selectedChunkID = nil
        selectedAudioTrackID = nil
        selectedTimingURL = nil
        preferredAudioKind = nil
        audioDurationByURL = [:]
        chunkMetadataLoaded = []
        chunkMetadataLoading = []
        chunkMetadataAttemptedAt = [:]
        lastPrefetchSentenceNumber = nil
        prefetchedAudioURLs = []
        jobContext = nil
        mediaResponse = nil
        timingResponse = nil
        chapterEntries = []
        readingBedCatalog = nil
        readingBedURL = nil
        selectedReadingBedID = nil
        mediaResolver = nil
        audioCoordinator.reset()
        pendingSentenceJump = nil
        isTranscriptLoading = false
        stopLiveUpdates()

        do {
            if let mediaOverride {
                let resolver = try (resolverOverride ?? makeResolver(origin: origin, configuration: configuration))
                let context = try await buildContextInBackground(
                    jobId: trimmedJobId,
                    media: mediaOverride,
                    timing: timingOverride,
                    resolver: resolver
                )
                jobContext = context
                mediaResolver = resolver
                mediaResponse = mediaOverride
                timingResponse = timingOverride
                readingBedCatalog = nil
                selectedReadingBedID = nil
                readingBedURL = nil
                configureDefaultSelections()
                loadState = .loaded
                return
            }

            let client = APIClient(configuration: configuration)
            async let mediaTask: Data = {
                switch origin {
                case .library:
                    return try await client.fetchLibraryMediaData(jobId: trimmedJobId)
                case .job:
                    if preferLiveMedia {
                        return try await client.fetchJobMediaLiveData(jobId: trimmedJobId)
                    }
                    return try await client.fetchJobMediaData(jobId: trimmedJobId)
                }
            }()
            async let timingTask: Data? = client.fetchJobTimingData(jobId: trimmedJobId)
            async let readingBedsTask: ReadingBedListResponse? = {
                do {
                    return try await client.fetchReadingBeds()
                } catch {
                    return nil
                }
            }()
            let (mediaData, timingData) = try await (mediaTask, timingTask)
            let readingBeds = await readingBedsTask
            let resolver = try makeResolver(origin: origin, configuration: configuration)
            let (media, timing, context) = try await decodeAndBuildContextInBackground(
                jobId: trimmedJobId,
                mediaData: mediaData,
                timingData: timingData,
                resolver: resolver
            )
            jobContext = context
            mediaResolver = resolver
            mediaResponse = media
            timingResponse = timing
            readingBedCatalog = readingBeds
            selectedReadingBedID = nil
            readingBedURL = resolveReadingBedURL(from: readingBeds, selectedID: nil)
            configureDefaultSelections()
            loadState = .loaded
        } catch is CancellationError {
            loadState = .idle
        } catch {
            loadState = .error(error.localizedDescription)
        }
    }

    func startLiveUpdates() {
        guard mediaOrigin == .job else { return }
        guard apiConfiguration != nil else { return }
        stopLiveUpdates()
        liveUpdateTask = Task { [weak self] in
            guard let self else { return }
            while !Task.isCancelled {
                await self.refreshLiveMedia()
                if self.mediaResponse?.complete == true {
                    break
                }
                try? await Task.sleep(nanoseconds: liveUpdateInterval)
            }
        }
    }

    func stopLiveUpdates() {
        liveUpdateTask?.cancel()
        liveUpdateTask = nil
    }

    func refreshLiveMedia() async {
        guard mediaOrigin == .job else { return }
        guard let configuration = apiConfiguration, let jobId, let resolver = mediaResolver else { return }
        let client = APIClient(configuration: configuration)
        do {
            let liveMedia = try await client.fetchJobMediaLive(jobId: jobId)
            guard shouldApplyLiveUpdate(current: mediaResponse, incoming: liveMedia) else { return }
            let mergedMedia = mergeLiveMedia(current: mediaResponse, incoming: liveMedia)
            let context = try await buildContextInBackground(
                jobId: jobId,
                media: mergedMedia,
                timing: timingResponse,
                resolver: resolver
            )
            mediaResponse = mergedMedia
            jobContext = context
            if let selectedChunkID, context.chunk(withID: selectedChunkID) != nil {
                return
            }
            configureDefaultSelections()
        } catch {
            return
        }
    }

    func shouldApplyLiveUpdate(current: PipelineMediaResponse?, incoming: PipelineMediaResponse) -> Bool {
        guard let current else { return true }
        if current.complete != incoming.complete {
            return true
        }
        if current.chunks.count != incoming.chunks.count {
            return true
        }
        let currentKeys = Set(current.media.keys)
        let incomingKeys = Set(incoming.media.keys)
        if currentKeys != incomingKeys {
            return true
        }
        for (key, incomingFiles) in incoming.media {
            if (current.media[key]?.count ?? 0) != incomingFiles.count {
                return true
            }
        }
        return false
    }

    func mergeLiveMedia(
        current: PipelineMediaResponse?,
        incoming: PipelineMediaResponse
    ) -> PipelineMediaResponse {
        guard let current else { return incoming }
        var currentByKey: [String: PipelineMediaChunk] = [:]
        for (index, chunk) in current.chunks.enumerated() {
            currentByKey[chunkKey(chunk, fallback: index)] = chunk
        }
        let mergedChunks = incoming.chunks.enumerated().map { index, chunk -> PipelineMediaChunk in
            let key = chunkKey(chunk, fallback: index)
            guard let existing = currentByKey[key],
                  chunk.sentences.isEmpty,
                  !existing.sentences.isEmpty else {
                return chunk
            }
            return PipelineMediaChunk(
                chunkID: chunk.chunkID,
                rangeFragment: chunk.rangeFragment,
                startSentence: chunk.startSentence,
                endSentence: chunk.endSentence,
                files: chunk.files,
                sentences: existing.sentences,
                metadataPath: chunk.metadataPath ?? existing.metadataPath,
                metadataURL: chunk.metadataURL ?? existing.metadataURL,
                sentenceCount: chunk.sentenceCount ?? existing.sentenceCount,
                audioTracks: chunk.audioTracks.isEmpty ? existing.audioTracks : chunk.audioTracks,
                timingTracks: chunk.timingTracks ?? existing.timingTracks
            )
        }
        return PipelineMediaResponse(media: incoming.media, chunks: mergedChunks, complete: incoming.complete)
    }

    func chunkKey(_ chunk: PipelineMediaChunk, fallback: Int) -> String {
        chunk.chunkID
            ?? chunk.rangeFragment
            ?? "chunk-\(fallback)"
    }

    /// Set to true to enable verbose chunk metadata loading logs
    private static let chunkMetadataDebug = false

    func loadChunkMetadataIfNeeded(for chunkID: String, force: Bool = false) async {
        guard let jobId, let resolver = mediaResolver else {
            print("[ChunkMetadata] Skipping: no jobId or resolver")
            return
        }
        guard let currentMediaResponse = mediaResponse else {
            print("[ChunkMetadata] Skipping: no mediaResponse")
            return
        }
        // When force=true, skip the loaded check to allow reloading
        if !force && chunkMetadataLoaded.contains(chunkID) { return }
        guard !chunkMetadataLoading.contains(chunkID) else { return }
        if !force, let lastAttempt = chunkMetadataAttemptedAt[chunkID] {
            if Date().timeIntervalSince(lastAttempt) < metadataRetryInterval {
                return
            }
        }

        guard let index = resolveChunkIndex(chunkID, chunks: currentMediaResponse.chunks) else {
            print("[ChunkMetadata] Skipping: cannot resolve chunk index for \(chunkID)")
            return
        }
        let chunk = currentMediaResponse.chunks[index]
        // Check if existing sentences have complete data (gates and tokens)
        // Only skip loading if data is complete, otherwise we need to fetch full metadata
        if !chunk.sentences.isEmpty && !force {
            let hasCompleteData = chunk.sentences.first.map { first in
                let hasGates = first.startGate != nil || first.originalStartGate != nil
                let hasTokens = first.original.tokens?.isEmpty == false
                return hasGates && hasTokens
            } ?? false
            if hasCompleteData {
                chunkMetadataLoaded.insert(chunkID)
                return
            }
            if Self.chunkMetadataDebug {
                print("[ChunkMetadata] Existing sentences lack complete data, loading for \(chunkID)")
            }
        }
        let metadataURL = chunk.metadataURL?.nonEmptyValue
        let metadataPath = chunk.metadataPath?.nonEmptyValue
        var preferPathFirst = false
        if let metadataURL,
           let url = URL(string: metadataURL),
           url.scheme?.lowercased() == "https",
           let apiBaseURL = apiConfiguration?.apiBaseURL,
           apiBaseURL.scheme?.lowercased() == "http",
           metadataPath != nil {
            preferPathFirst = true
        }
        var candidates: [String] = []
        if preferPathFirst {
            if let metadataPath { candidates.append(metadataPath) }
            if let metadataURL, metadataURL != metadataPath { candidates.append(metadataURL) }
        } else {
            if let metadataURL { candidates.append(metadataURL) }
            if let metadataPath, metadataPath != metadataURL { candidates.append(metadataPath) }
        }
        // If no metadata path candidates, try API fallback directly
        let useAPIFallbackOnly = candidates.isEmpty

        chunkMetadataAttemptedAt[chunkID] = Date()
        chunkMetadataLoading.insert(chunkID)
        defer { chunkMetadataLoading.remove(chunkID) }

        do {
            var payloadData: Data? = nil
            if !useAPIFallbackOnly {
                print("[ChunkMetadata] Loading \(chunkID) with \(candidates.count) candidate paths")
                for candidate in candidates {
                guard let url = resolver.resolvePath(jobId: jobId, relativePath: candidate) else {
                    print("[ChunkMetadata] Could not resolve path: \(candidate)")
                    continue
                }
                print("[ChunkMetadata] Resolved \(candidate) -> \(url.absoluteString)")
                do {
                    if url.isFileURL {
                        let exists = FileManager.default.fileExists(atPath: url.path)
                        print("[ChunkMetadata] File URL exists=\(exists): \(url.path)")
                        if !exists {
                            continue
                        }
                        // Check if iCloud file is downloaded
                        if let resourceValues = try? url.resourceValues(forKeys: [.isUbiquitousItemKey, .ubiquitousItemDownloadingStatusKey]) {
                            if resourceValues.isUbiquitousItem == true {
                                let status = resourceValues.ubiquitousItemDownloadingStatus
                                print("[ChunkMetadata] iCloud status: \(status?.rawValue ?? "unknown")")
                                if status != .current {
                                    print("[ChunkMetadata] Triggering iCloud download for: \(url.lastPathComponent)")
                                    try? FileManager.default.startDownloadingUbiquitousItem(at: url)
                                    continue
                                }
                            }
                        }
                        payloadData = try await Task.detached(priority: .utility) {
                            try Data(contentsOf: url, options: .mappedIfSafe)
                        }.value
                        print("[ChunkMetadata] Loaded \(payloadData?.count ?? 0) bytes from file")
                        break
                    }
                    var request = URLRequest(url: url)
                    request.setValue("application/json", forHTTPHeaderField: "Accept")
                    let (data, response) = try await URLSession.shared.data(for: request)
                    if let httpResponse = response as? HTTPURLResponse,
                       !(200..<300).contains(httpResponse.statusCode) {
                        if Self.chunkMetadataDebug {
                            print("[ChunkMetadata] HTTP \(httpResponse.statusCode) from \(url.lastPathComponent)")
                        }
                        continue
                    }
                    payloadData = data
                    break
                } catch {
                    print("[ChunkMetadata] Error loading \(url.lastPathComponent): \(error.localizedDescription)")
                    continue
                }
                }
            } else {
                print("[ChunkMetadata] No candidate paths for \(chunkID), using API fallback")
            }
            var sentences: [ChunkSentenceMetadata]? = nil
            if let payloadData {
                sentences = try await decodeChunkMetadataInBackground(payloadData)
                if let sentences, !sentences.isEmpty {
                    let first = sentences.first!
                    let hasTokens = first.original.tokens?.isEmpty == false
                    let hasOrigGates = first.originalStartGate != nil && first.originalEndGate != nil
                    let hasTransGates = first.startGate != nil && first.endGate != nil
                    print("[ChunkMetadata] Decoded \(sentences.count) sentences, hasTokens=\(hasTokens), hasOrigGates=\(hasOrigGates), hasTransGates=\(hasTransGates)")
                    if !hasOrigGates || !hasTransGates {
                        print("[ChunkMetadata]   first sentence: originalGates=\(first.originalStartGate.map { String(format: "%.3f", $0) } ?? "nil")..\(first.originalEndGate.map { String(format: "%.3f", $0) } ?? "nil"), translationGates=\(first.startGate.map { String(format: "%.3f", $0) } ?? "nil")..\(first.endGate.map { String(format: "%.3f", $0) } ?? "nil")")
                    }
                } else {
                    print("[ChunkMetadata] Decoded 0 sentences from payloadData")
                }
            }
            if sentences == nil || sentences?.isEmpty == true {
                print("[ChunkMetadata] Trying API fallback for \(chunkID)")
                if let fallbackChunk = await fetchChunkMetadataFromAPI(jobId: jobId, chunkID: chunkID) {
                    sentences = fallbackChunk.sentences
                    print("[ChunkMetadata] API fallback returned \(sentences?.count ?? 0) sentences")
                } else {
                    print("[ChunkMetadata] API fallback returned nil")
                }
            }
            guard let sentences, !sentences.isEmpty else {
                print("[ChunkMetadata] FAILED: No sentences loaded for \(chunkID)")
                return
            }

            guard jobId == self.jobId, let latestMediaResponse = mediaResponse else { return }
            guard let index = resolveChunkIndex(chunkID, chunks: latestMediaResponse.chunks) else { return }
            let latestChunk = latestMediaResponse.chunks[index]
            // Always update with newly loaded sentences - they have more complete data
            // (gates, tokens) than what might be in the initial media response
            var updatedChunks = latestMediaResponse.chunks
            let updatedChunk = PipelineMediaChunk(
                chunkID: latestChunk.chunkID,
                rangeFragment: latestChunk.rangeFragment,
                startSentence: latestChunk.startSentence,
                endSentence: latestChunk.endSentence,
                files: latestChunk.files,
                sentences: sentences,
                metadataPath: latestChunk.metadataPath,
                metadataURL: latestChunk.metadataURL,
                sentenceCount: latestChunk.sentenceCount ?? sentences.count,
                audioTracks: latestChunk.audioTracks,
                timingTracks: latestChunk.timingTracks
            )
            updatedChunks[index] = updatedChunk
            let refreshedMedia = PipelineMediaResponse(
                media: latestMediaResponse.media,
                chunks: updatedChunks,
                complete: latestMediaResponse.complete
            )
            let context = try await buildContextInBackground(
                jobId: jobId,
                media: refreshedMedia,
                timing: timingResponse,
                resolver: resolver
            )
            mediaResponse = refreshedMedia
            jobContext = context
            if let updatedChunk = context.chunk(withID: chunkID) {
                attemptPendingSentenceJump(in: updatedChunk)
            }
            chunkMetadataLoaded.insert(chunkID)
        } catch {
            return
        }
    }

    func resolveChunkIndex(_ chunkID: String, chunks: [PipelineMediaChunk]) -> Int? {
        if let index = chunks.firstIndex(where: { $0.chunkID == chunkID }) {
            return index
        }
        if chunkID.hasPrefix("chunk-") {
            let raw = chunkID.replacingOccurrences(of: "chunk-", with: "")
            if let index = Int(raw), chunks.indices.contains(index) {
                return index
            }
        }
        return nil
    }

    private func decodeAndBuildContextInBackground(
        jobId: String,
        mediaData: Data,
        timingData: Data?,
        resolver: MediaURLResolver
    ) async throws -> (PipelineMediaResponse, JobTimingResponse?, JobContext) {
        try await Task.detached(priority: .userInitiated) { () -> (PipelineMediaResponse, JobTimingResponse?, JobContext) in
            let decoder = JSONDecoder()
            decoder.keyDecodingStrategy = .convertFromSnakeCase
            decoder.dateDecodingStrategy = .iso8601
            let media = try decoder.decode(PipelineMediaResponse.self, from: mediaData)
            let timing = try timingData.map { try decoder.decode(JobTimingResponse.self, from: $0) }
            // Debug: log chunk sentence info after decode
            for (idx, chunk) in media.chunks.enumerated() where idx < 3 || chunk.sentences.count > 0 {
                let hasMetadataPath = chunk.metadataPath?.isEmpty == false || chunk.metadataURL?.isEmpty == false
                if !chunk.sentences.isEmpty {
                    let first = chunk.sentences.first!
                    let hasGates = first.startGate != nil || first.originalStartGate != nil
                    let hasTokens = first.original.tokens?.isEmpty == false
                    print("[MediaDecode] chunk \(chunk.chunkID ?? "nil") has \(chunk.sentences.count) sentences, hasMetadataPath=\(hasMetadataPath), firstHasGates=\(hasGates), firstHasTokens=\(hasTokens)")
                    if !hasTokens {
                        print("[MediaDecode]   original.text='\(first.original.text.prefix(50))', original.tokens=\(first.original.tokens ?? [])")
                    }
                } else if hasMetadataPath {
                    print("[MediaDecode] chunk \(chunk.chunkID ?? "nil") has empty sentences, metadataPath=\(chunk.metadataPath ?? chunk.metadataURL ?? "nil")")
                }
            }
            let context = try JobContextBuilder.build(
                jobId: jobId,
                media: media,
                timing: timing,
                resolver: resolver
            )
            return (media, timing, context)
        }.value
    }

    private func buildContextInBackground(
        jobId: String,
        media: PipelineMediaResponse,
        timing: JobTimingResponse?,
        resolver: MediaURLResolver
    ) async throws -> JobContext {
        try await Task.detached(priority: .userInitiated) {
            try JobContextBuilder.build(
                jobId: jobId,
                media: media,
                timing: timing,
                resolver: resolver
            )
        }.value
    }

    private func decodeChunkMetadataInBackground(_ payloadData: Data) async throws -> [ChunkSentenceMetadata]? {
        await Task.detached(priority: .utility) { () -> [ChunkSentenceMetadata]? in
            let decoder = JSONDecoder()
            decoder.keyDecodingStrategy = .convertFromSnakeCase
            if let payload = try? decoder.decode(ChunkMetadataPayload.self, from: payloadData) {
                return payload.sentences
            }
            if let payload = try? decoder.decode([ChunkSentenceMetadata].self, from: payloadData) {
                return payload
            }
            return nil
        }.value
    }

    private func fetchChunkMetadataFromAPI(jobId: String, chunkID: String) async -> PipelineMediaChunk? {
        guard mediaOrigin == .job else { return nil }
        guard let configuration = apiConfiguration else { return nil }
        let client = APIClient(configuration: configuration)
        do {
            return try await client.fetchJobMediaChunk(jobId: jobId, chunkId: chunkID)
        } catch {
            if Self.chunkMetadataDebug {
                print("[ChunkMetadata] API fallback error: \(error.localizedDescription)")
            }
            return nil
        }
    }

    private func makeResolver(origin: MediaOrigin, configuration: APIClientConfiguration) throws -> MediaURLResolver {
        switch origin {
        case .library:
            return MediaURLResolver(
                origin: .library(apiBaseURL: configuration.apiBaseURL, accessToken: configuration.authToken)
            )
        case .job:
            let storageResolver = try StorageResolver(
                apiBaseURL: configuration.apiBaseURL,
                override: configuration.storageBaseURL
            )
            return MediaURLResolver(
                origin: .storage(
                    apiBaseURL: configuration.apiBaseURL,
                    resolver: storageResolver,
                    accessToken: configuration.authToken
                )
            )
        }
    }
}
