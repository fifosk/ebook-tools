import Foundation

extension AppleBookCreateView {
    func handleYoutubeBaseDirChange(_ value: String) {
        persistYoutubeBaseDir(value)
    }

    func handleSubtitleSourcePathChange() {
        subtitleMetadataLookupSourceName = subtitleMetadataSourceName
        viewModel.clearSubtitleMetadata()
    }

    func requestDeleteSubtitleSource(_ entry: SubtitleSourceEntry) {
        subtitleSourcePendingDelete = entry
    }

    func deleteSubtitleSource(_ entry: SubtitleSourceEntry) async {
        subtitleSourcePendingDelete = nil
        let didDelete = await viewModel.deleteSubtitleSource(path: entry.path, using: appState)
        guard didDelete else { return }
        if subtitleSourcePath == entry.path {
            subtitleSourcePath = ""
        }
        await refreshSubtitleSources(force: true)
    }

    func handleYoutubeVideoPathChange(_ path: String) {
        youtubeDiscoveryState = nil
        youtubeSubtitleExtractionLanguages = ""
        viewModel.resetYoutubeSubtitleExtractionState()
        viewModel.resetYoutubeMetadataState()
        persistYoutubeSelectionPath(path, field: "video")
    }

    func handleYoutubeSubtitlePathChange(_ path: String) {
        youtubeDiscoveryState = AppleBookCreatePresentation.videoDiscoveryState(
            youtubeDiscoveryState,
            replacingSelectedSubtitlePath: path
        )
        persistYoutubeSelectionPath(path, field: "subtitle")
    }

    func handleLanguagePreferenceChange() {
        persistLanguagePreferences()
    }

    func handleSubtitleShowOriginalChange(_ value: Bool) {
        persistSubtitleShowOriginal(value)
    }

    func refreshPipelineFilesFromSourceSection() {
        Task { await refreshPipelineFiles(force: true) }
    }

    func refreshSubtitleSourcesFromSourceSection() {
        Task { await refreshSubtitleSources(force: true) }
    }

    func refreshYoutubeLibraryFromSourceSection() {
        Task { await refreshYoutubeLibrary(force: true) }
    }

    func chooseNarrateFile() {
        isImportingNarrateEbook = true
    }

    func chooseSubtitleFile() {
        isImportingSubtitleFile = true
    }

    func loadNarrateChapters() {
        Task {
            selectedNarrateStartChapterID = ""
            selectedNarrateEndChapterID = ""
            await viewModel.loadNarrateChapters(inputFile: sourcePath, using: appState)
        }
    }

    func clearNarrateSourceMetadata() {
        sourceBookTitle = ""
        sourceBookAuthor = ""
        sourceBookGenre = ""
        sourceBookSummary = ""
        bookSummary = ""
        bookYear = ""
        bookIsbn = ""
        bookCoverFile = ""
        bookMetadataExtras = [:]
        editedFields.subtract([
            .sourceBookTitle,
            .sourceBookAuthor,
            .sourceBookGenre,
            .sourceBookSummary,
            .bookSummary,
            .bookYear,
            .bookIsbn,
            .bookCoverFile,
        ])
    }

    func refreshPipelineFiles(force: Bool = false) async {
        let files = await viewModel.loadPipelineFiles(
            using: appState,
            cacheKey: creationOptionsLoadKey,
            force: force
        )
        applyPreferredNarrateSource(from: files)
    }

    func searchAcquisitionDiscovery(_ query: String, provider: String) {
        Task {
            _ = await viewModel.loadEbookDiscovery(
                using: appState,
                cacheKey: creationOptionsLoadKey,
                query: query,
                provider: provider,
                force: true
            )
        }
    }

    func applyAcquisitionDiscoveryCandidate(_ candidate: AcquisitionCandidate) {
        if let localPath = candidate.localPath?.trimmingCharacters(in: .whitespacesAndNewlines), !localPath.isEmpty {
            Task {
                guard let preparedPath = await viewModel.prepareEbookDiscoveryCandidate(
                    using: appState,
                    candidate: candidate
                ) else {
                    return
                }
                applyAcquisitionDiscoveryPath(preparedPath)
                _ = applyAcquisitionDiscoveryMetadata(candidate)
            }
            return
        }

        if !candidate.capabilities.contains("acquire") {
            let sourceIds = AppleBookCreatePresentation.internetArchiveSourceIDs(candidate)
            if !sourceIds.isEmpty {
                Task {
                    _ = await viewModel.loadEbookDiscovery(
                        using: appState,
                        cacheKey: creationOptionsLoadKey,
                        query: candidate.title,
                        provider: "internet_archive",
                        sourceIds: sourceIds,
                        force: true
                    )
                }
                return
            }
            _ = applyAcquisitionDiscoveryMetadata(candidate)
            return
        }

        Task {
            guard let acquiredPath = await viewModel.acquireEbookDiscoveryCandidate(
                using: appState,
                candidate: candidate
            ) else {
                return
            }
            applyAcquisitionDiscoveryPath(acquiredPath)
            _ = applyAcquisitionDiscoveryMetadata(candidate)
            _ = await viewModel.loadPipelineFiles(
                using: appState,
                cacheKey: creationOptionsLoadKey,
                force: true
            )
        }
    }

    @discardableResult
    func applyAcquisitionDiscoveryMetadata(_ candidate: AcquisitionCandidate) -> Bool {
        guard let metadataApplication = AppleBookCreatePresentation.bookDiscoveryMetadataApplication(candidate) else {
            return false
        }

        var applied = false
        if let title = metadataApplication.sourceBookTitle {
            sourceBookTitle = title
            editedFields.insert(.sourceBookTitle)
            applied = true
        }
        if let author = metadataApplication.sourceBookAuthor {
            sourceBookAuthor = author
            editedFields.insert(.sourceBookAuthor)
            applied = true
        }
        if let genre = metadataApplication.sourceBookGenre {
            sourceBookGenre = genre
            editedFields.insert(.sourceBookGenre)
            applied = true
        }
        if let summary = metadataApplication.bookSummary {
            bookSummary = summary
            editedFields.insert(.bookSummary)
            applied = true
        }
        if let year = metadataApplication.bookYear {
            bookYear = year
            editedFields.insert(.bookYear)
            applied = true
        }
        if let isbn = metadataApplication.bookIsbn {
            bookIsbn = isbn
            editedFields.insert(.bookIsbn)
            applied = true
        }
        if let cover = metadataApplication.bookCoverFile {
            bookCoverFile = cover
            editedFields.insert(.bookCoverFile)
            applied = true
        }
        bookMetadataExtras = metadataApplication.bookMetadataExtras
        return applied
    }

    func applyAcquisitionDiscoveryPath(_ localPath: String) {
        markEdited(.sourcePath)
        let previousSourcePath = sourcePath
        selectedNarrateFileURL = nil
        selectedNarrateFileName = nil
        clearNarrateChapterSelection()
        clearNarrateSourceMetadata()
        sourcePath = localPath
        refreshNarrateBaseOutputIfNeeded(for: localPath, replacing: previousSourcePath)
    }

    func refreshNarrateBaseOutputIfNeeded(for newSourcePath: String, replacing oldSourcePath: String) {
        guard shouldRefreshNarrateBaseOutput(replacing: oldSourcePath) else {
            return
        }
        sourceBaseOutput = derivedNarrateBaseOutputName(for: newSourcePath)
    }

    func searchYoutubeAcquisitionDiscovery(_ query: String, provider: String) {
        Task {
            _ = await viewModel.loadVideoDiscovery(
                using: appState,
                cacheKey: creationOptionsLoadKey,
                query: query,
                provider: provider,
                force: true
            )
        }
    }

    func applyYoutubeAcquisitionDiscoveryCandidate(_ candidate: AcquisitionCandidate) {
        if AppleBookCreatePresentation.isYoutubeMetadataVideoDiscoveryProviderID(candidate.provider) {
            guard let sourceURL = AppleBookCreatePresentation.youtubeMetadataSourceURL(for: candidate) else {
                viewModel.youtubeMetadataErrorMessage = "Selected YouTube discovery result did not include a reviewable URL."
                return
            }
            youtubeDiscoveryState = AppleBookCreatePresentation.videoDiscoveryStatePayload(
                from: candidate,
                selectedVideoPath: nil,
                selectedSubtitlePath: nil
            )
            viewModel.youtubeMetadataMessage = "Selected YouTube discovery result \(candidate.title). Review metadata before downloading or dubbing."
            Task {
                await viewModel.lookupYoutubeVideoMetadata(
                    sourceName: sourceURL,
                    using: appState
                )
            }
            return
        }

        if candidate.provider == "newznab_torznab" {
            youtubeDiscoveryState = AppleBookCreatePresentation.videoDiscoveryStatePayload(
                from: candidate,
                selectedVideoPath: nil,
                selectedSubtitlePath: nil
            )
            viewModel.youtubeMetadataMessage = "Selected indexer result \(candidate.title). Confirm lawful access before any downloader handoff."
            return
        }

        Task {
            guard let prepared = await viewModel.prepareVideoDiscoveryCandidate(
                using: appState,
                candidate: candidate
            ) else {
                return
            }
            applyPreparedVideoDiscoveryCandidate(prepared, source: candidate)
        }
    }

    func submitDownloadStation(
        sourceURI: String?,
        candidateToken: String?,
        destination: String?,
        confirmed: Bool
    ) {
        Task {
            _ = await viewModel.submitDownloadStationTask(
                using: appState,
                sourceURI: sourceURI,
                candidateToken: candidateToken,
                destination: destination,
                confirmed: confirmed
            )
        }
    }

    func pollDownloadStation() {
        Task {
            let completed = await viewModel.pollDownloadStationTask(using: appState)
            guard completed else {
                return
            }
            let discovery = await viewModel.loadVideoDiscovery(
                using: appState,
                cacheKey: creationOptionsLoadKey,
                provider: "manual_downloads",
                force: true
            )
            _ = await viewModel.loadYoutubeLibrary(
                using: appState,
                cacheKey: youtubeLibraryLoadKey,
                baseDir: youtubeBaseDir,
                force: true
            )
            if let candidate = AppleBookCreatePresentation.downloadStationCompletedCandidate(
                from: discovery,
                job: viewModel.downloadStationJob
            ) {
                applyYoutubeAcquisitionDiscoveryCandidate(candidate)
            }
        }
    }

    func requestDeletePipelineEbook(_ entry: PipelineFileEntry) {
        pipelineEbookPendingDelete = entry
    }

    func deletePipelineEbook(_ entry: PipelineFileEntry) async {
        pipelineEbookPendingDelete = nil
        let didDelete = await viewModel.deletePipelineEbook(path: entry.path, using: appState)
        guard didDelete else { return }
        if sourcePath == entry.path {
            sourcePath = ""
            sourceBaseOutput = ""
            clearNarrateChapterSelection()
            clearNarrateSourceMetadata()
            viewModel.clearNarrateChapters()
        }
        await refreshPipelineFiles(force: true)
    }

    func refreshSubtitleSources(force: Bool = false) async {
        let sources = await viewModel.loadSubtitleSources(
            using: appState,
            cacheKey: creationOptionsLoadKey,
            force: force
        )
        applyPreferredSubtitleSource(from: sources)
    }

    func refreshYoutubeLibrary(force: Bool = false) async {
        let library = await viewModel.loadYoutubeLibrary(
            using: appState,
            cacheKey: youtubeLibraryLoadKey,
            baseDir: youtubeBaseDir,
            force: force
        )
        if trimmed(youtubeBaseDir).isEmpty,
           let resolvedBaseDir = library?.baseDir.nonEmptyValue {
            youtubeBaseDir = resolvedBaseDir
        }
        applyPreferredYoutubeSource(from: library)
    }

    func inspectYoutubeSubtitles() {
        Task {
            guard let response = await viewModel.loadYoutubeSubtitleStreams(
                videoPath: youtubeVideoPath,
                using: appState
            ) else {
                return
            }
            let defaults = AppleBookCreatePresentation.defaultYoutubeInlineSubtitleLanguages(
                from: response.streams
            )
            youtubeSubtitleExtractionLanguages = defaults.joined(separator: ", ")
        }
    }

    func extractYoutubeSubtitles() {
        Task {
            let languages = AppleBookCreatePresentation.normalizedYoutubeInlineSubtitleLanguages(
                youtubeSubtitleExtractionLanguages
            )
            guard let response = await viewModel.extractYoutubeSubtitles(
                videoPath: youtubeVideoPath,
                languages: languages,
                using: appState
            ) else {
                return
            }
            let selectedVideoPath = youtubeVideoPath
            let extractedSubtitlePath = response.extracted.first?.path
            let library = await viewModel.loadYoutubeLibrary(
                using: appState,
                cacheKey: youtubeLibraryLoadKey,
                baseDir: youtubeBaseDir,
                force: true
            )
            if !trimmed(selectedVideoPath).isEmpty {
                youtubeVideoPath = selectedVideoPath
            }
            if let extractedSubtitlePath, !trimmed(extractedSubtitlePath).isEmpty {
                youtubeSubtitlePath = extractedSubtitlePath
            } else {
                applyPreferredYoutubeSource(from: library)
            }
        }
    }

    func clearNarrateChapterSelection() {
        selectedNarrateStartChapterID = ""
        selectedNarrateEndChapterID = ""
        viewModel.clearNarrateChapters()
    }

    private func shouldRefreshNarrateBaseOutput(replacing oldSourcePath: String) -> Bool {
        guard !editedFields.contains(.sourceBaseOutput) else {
            return false
        }
        let currentBaseOutput = trimmed(sourceBaseOutput)
        if currentBaseOutput.isEmpty {
            return true
        }
        let previousSourcePath = trimmed(oldSourcePath)
        guard !previousSourcePath.isEmpty else {
            return false
        }
        return currentBaseOutput == derivedNarrateBaseOutputName(for: previousSourcePath)
    }

    private func derivedNarrateBaseOutputName(for sourcePath: String) -> String {
        if let entry = AppleBookCreatePresentation.selectedPipelineEbook(
            sourcePath: sourcePath,
            files: viewModel.pipelineFiles
        ) {
            return AppleBookCreatePresentation.deriveBaseOutputName(entry.name)
        }
        return AppleBookCreatePresentation.deriveBaseOutputName(sourcePath)
    }

    private func applyPreparedVideoDiscoveryCandidate(
        _ prepared: AcquisitionPreparedArtifactResponse,
        source candidate: AcquisitionCandidate
    ) {
        guard let videoPath = prepared.videoPath?.trimmingCharacters(in: .whitespacesAndNewlines).nonEmptyValue
                ?? prepared.localPath.trimmingCharacters(in: .whitespacesAndNewlines).nonEmptyValue
                ?? candidate.localPath?.trimmingCharacters(in: .whitespacesAndNewlines).nonEmptyValue else {
            return
        }
        let preferredSubtitlePath = prepared.subtitlePath?.trimmingCharacters(in: .whitespacesAndNewlines).nonEmptyValue
            ?? prepared.subtitles.first?.path.trimmingCharacters(in: .whitespacesAndNewlines).nonEmptyValue
            ?? candidate.subtitles.first?.path.trimmingCharacters(in: .whitespacesAndNewlines).nonEmptyValue

        markEdited(.youtubeVideoPath)
        youtubeVideoPath = videoPath
        handleYoutubeVideoPathChange(videoPath)
        youtubeDiscoveryState = AppleBookCreatePresentation.videoDiscoveryStatePayload(
            from: candidate,
            selectedVideoPath: videoPath,
            selectedSubtitlePath: preferredSubtitlePath
        )

        if let subtitlePath = preferredSubtitlePath {
            markEdited(.youtubeSubtitlePath)
            youtubeSubtitlePath = subtitlePath
            handleYoutubeSubtitlePathChange(subtitlePath)
            youtubeDiscoveryState = AppleBookCreatePresentation.videoDiscoveryStatePayload(
                from: candidate,
                selectedVideoPath: videoPath,
                selectedSubtitlePath: subtitlePath
            )
        }
    }

    private func applyPreferredNarrateSource(from files: PipelineFileBrowserResponse?) {
        guard let defaults = AppleBookCreatePresentation.narrateSourceDefaults(
            selectedLocalFile: selectedNarrateFileURL != nil,
            didEditSourcePath: editedFields.contains(.sourcePath),
            sourcePath: sourcePath,
            sourceBaseOutput: sourceBaseOutput,
            didEditBaseOutput: editedFields.contains(.sourceBaseOutput),
            files: files
        ) else {
            return
        }

        if sourcePath != defaults.path {
            sourcePath = defaults.path
            clearNarrateSourceMetadata()
        }
        if let baseOutput = defaults.baseOutput {
            sourceBaseOutput = baseOutput
        }
    }

    private func applyPreferredSubtitleSource(from sources: SubtitleSourceListResponse?) {
        guard let defaults = AppleBookCreatePresentation.subtitleSourceDefaults(
            selectedLocalFile: selectedSubtitleFileURL != nil,
            didEditSourcePath: editedFields.contains(.subtitleSourcePath),
            sourcePath: subtitleSourcePath,
            sources: sources
        ) else {
            return
        }

        subtitleSourcePath = defaults.path
        subtitleMetadataLookupSourceName = defaults.metadataLookupSourceName
    }

    private func applyPreferredYoutubeSource(from library: YoutubeNasLibraryResponse?) {
        guard let defaults = AppleBookCreatePresentation.youtubeSourceDefaults(
            library: library,
            currentStorageScope: youtubeSelectionStorageScope,
            nextStorageScope: youtubeLibraryLoadKey,
            didEditVideoPath: editedFields.contains(.youtubeVideoPath),
            currentVideoPath: youtubeVideoPath,
            didEditSubtitlePath: editedFields.contains(.youtubeSubtitlePath),
            currentSubtitlePath: youtubeSubtitlePath,
            storedVideoPath: storedYoutubeSelectionPath(field: "video"),
            storedSubtitlePath: storedYoutubeSelectionPath(field: "subtitle")
        ) else {
            return
        }

        youtubeSelectionStorageScope = defaults.nextStorageScope
        if let videoPath = defaults.videoPath {
            youtubeVideoPath = videoPath
        }
        if let subtitlePath = defaults.subtitlePath {
            youtubeSubtitlePath = subtitlePath
        }
    }
}
