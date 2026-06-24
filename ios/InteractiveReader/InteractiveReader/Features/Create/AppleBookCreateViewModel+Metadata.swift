import Foundation

extension AppleBookCreateViewModel {
    func lookupSubtitleTvMetadata(
        sourceName: String,
        force: Bool = false,
        using appState: AppState
    ) async {
        guard let configuration = appState.configuration else {
            subtitleMetadataErrorMessage = "API configuration is unavailable."
            return
        }
        let trimmedSourceName = sourceName.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmedSourceName.isEmpty else {
            subtitleMetadataErrorMessage = "Choose a subtitle before loading TV metadata."
            return
        }

        isLoadingSubtitleTvMetadata = true
        subtitleMetadataErrorMessage = nil
        subtitleMetadataMessage = nil
        defer { isLoadingSubtitleTvMetadata = false }

        do {
            let client = APIClient(configuration: configuration)
            let request = SubtitleTvMetadataPreviewLookupRequest(sourceName: trimmedSourceName, force: force)
            let response = try await client.lookupSubtitleTvMetadataPreview(request)
            subtitleTvMetadataPreview = response
            if let mediaMetadata = response.mediaMetadata {
                subtitleMediaMetadataDraft = AppleBookCreatePresentation.normalizedSubtitleMediaMetadata(mediaMetadata)
                syncSubtitleMediaMetadataJSONText()
                subtitleMetadataMessage = "Loaded TV metadata for \(response.sourceName ?? trimmedSourceName)."
            } else {
                subtitleMediaMetadataDraft = nil
                syncSubtitleMediaMetadataJSONText()
                subtitleMetadataMessage = "No TV metadata match for \(response.sourceName ?? trimmedSourceName)."
            }
        } catch {
            subtitleTvMetadataPreview = nil
            subtitleMediaMetadataDraft = nil
            syncSubtitleMediaMetadataJSONText()
            subtitleMetadataErrorMessage = error.localizedDescription
        }
    }

    func clearSubtitleMetadata() {
        subtitleTvMetadataPreview = nil
        subtitleMediaMetadataDraft = nil
        syncSubtitleMediaMetadataJSONText()
        subtitleMetadataMessage = nil
        subtitleMetadataErrorMessage = nil
    }

    func clearSubtitleTvMetadataCache(
        query: String,
        using appState: AppState
    ) async {
        guard let configuration = appState.configuration else {
            subtitleMetadataErrorMessage = "API configuration is unavailable."
            return
        }
        let trimmedQuery = query.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmedQuery.isEmpty else {
            subtitleMetadataErrorMessage = "Enter a lookup filename before clearing the cache."
            return
        }

        isClearingSubtitleTvMetadataCache = true
        subtitleMetadataErrorMessage = nil
        subtitleMetadataMessage = nil
        defer { isClearingSubtitleTvMetadataCache = false }

        do {
            let client = APIClient(configuration: configuration)
            let response = try await client.clearSubtitleTvMetadataCache(query: trimmedQuery)
            subtitleMetadataMessage = AppleBookCreateMetadataJSON.cacheClearMessage(
                cleared: response.cleared,
                kind: "TV",
                query: trimmedQuery
            )
        } catch {
            subtitleMetadataErrorMessage = error.localizedDescription
        }
    }

    func updateSubtitleMediaMetadata(section: String?, key: String, value: String) {
        let trimmedValue = value.trimmingCharacters(in: .whitespacesAndNewlines)
        if let section = section?.trimmingCharacters(in: .whitespacesAndNewlines), !section.isEmpty {
            updateSubtitleMetadataSection(section) { sectionDraft in
                if trimmedValue.isEmpty {
                    sectionDraft.removeValue(forKey: key)
                } else {
                    sectionDraft[key] = .string(trimmedValue)
                }
            }
        } else if trimmedValue.isEmpty {
            subtitleMediaMetadataDraft?.removeValue(forKey: key)
        } else {
            ensureSubtitleMediaMetadataDraft()
            subtitleMediaMetadataDraft?[key] = .string(trimmedValue)
        }
        normalizeSubtitleMetadataAfterEdit()
        syncSubtitleMediaMetadataJSONText()
    }

    func updateSubtitleMediaMetadataNumber(section: String, key: String, value: String) {
        let trimmedValue = value.trimmingCharacters(in: .whitespacesAndNewlines)
        updateSubtitleMetadataSection(section) { sectionDraft in
            guard !trimmedValue.isEmpty else {
                sectionDraft.removeValue(forKey: key)
                return
            }
            guard let parsed = Double(trimmedValue), parsed.isFinite, parsed > 0 else {
                return
            }
            sectionDraft[key] = .number(floor(parsed))
        }
        normalizeSubtitleMetadataAfterEdit()
        syncSubtitleMediaMetadataJSONText()
    }

    func updateSubtitleMediaMetadataNestedText(
        section: String,
        nestedKey: String,
        key: String,
        value: String
    ) {
        updateSubtitleMetadataSection(section) { sectionDraft in
            AppleBookCreateMetadataJSON.updateNestedText(
                in: &sectionDraft,
                nestedKey: nestedKey,
                key: key,
                value: value
            )
        }
        normalizeSubtitleMetadataAfterEdit()
        syncSubtitleMediaMetadataJSONText()
    }

    func syncSubtitleMediaMetadataJSONText() {
        subtitleMediaMetadataJSONText = AppleBookCreateMetadataJSON.prettyString(from: subtitleMediaMetadataDraft)
        subtitleMediaMetadataJSONErrorMessage = nil
    }

    func applySubtitleMediaMetadataJSONText() {
        let parsed = AppleBookCreateMetadataJSON.parseObject(subtitleMediaMetadataJSONText)
        if let error = parsed.error {
            subtitleMediaMetadataJSONErrorMessage = error
            return
        }
        subtitleMediaMetadataDraft = AppleBookCreatePresentation.normalizedSubtitleMediaMetadata(parsed.metadata)
        syncSubtitleMediaMetadataJSONText()
        subtitleMetadataMessage = "Applied advanced metadata JSON."
        subtitleMetadataErrorMessage = nil
    }

    func subtitleMediaMetadataText(section: String?, key: String) -> String {
        if let section,
           let sectionDraft = subtitleMediaMetadataDraft?[section]?.objectValue {
            return sectionDraft[key]?.stringValue ?? ""
        }
        return subtitleMediaMetadataDraft?[key]?.stringValue ?? ""
    }

    func subtitleMediaMetadataNestedText(section: String, nestedKey: String, keys: [String]) -> String {
        guard let nested = subtitleMediaMetadataDraft?[section]?.objectValue?[nestedKey]?.objectValue else {
            return ""
        }
        for key in keys {
            if let value = nested[key]?.stringValue {
                return value
            }
        }
        return ""
    }

    func lookupYoutubeTvMetadata(
        sourceName: String,
        force: Bool = false,
        using appState: AppState
    ) async {
        guard let configuration = appState.configuration else {
            youtubeMetadataErrorMessage = "API configuration is unavailable."
            return
        }
        let trimmedSourceName = sourceName.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmedSourceName.isEmpty else {
            youtubeMetadataErrorMessage = "Choose a subtitle before loading TV metadata."
            return
        }

        isLoadingYoutubeTvMetadata = true
        youtubeMetadataErrorMessage = nil
        youtubeMetadataMessage = nil
        defer { isLoadingYoutubeTvMetadata = false }

        do {
            let client = APIClient(configuration: configuration)
            let request = SubtitleTvMetadataPreviewLookupRequest(sourceName: trimmedSourceName, force: force)
            let response = try await client.lookupSubtitleTvMetadataPreview(request)
            youtubeTvMetadataPreview = response
            if let mediaMetadata = response.mediaMetadata {
                mergeYoutubeTvMetadata(mediaMetadata)
                syncYoutubeMediaMetadataJSONText()
                youtubeMetadataMessage = "Loaded TV metadata for \(response.sourceName ?? trimmedSourceName)."
            } else {
                youtubeMetadataMessage = "No TV metadata match for \(response.sourceName ?? trimmedSourceName)."
            }
        } catch {
            youtubeMetadataErrorMessage = error.localizedDescription
        }
    }

    func lookupYoutubeVideoMetadata(
        sourceName: String,
        force: Bool = false,
        using appState: AppState
    ) async {
        guard let configuration = appState.configuration else {
            youtubeMetadataErrorMessage = "API configuration is unavailable."
            return
        }
        let trimmedSourceName = sourceName.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmedSourceName.isEmpty else {
            youtubeMetadataErrorMessage = "Choose a video before loading YouTube metadata."
            return
        }

        isLoadingYoutubeVideoMetadata = true
        youtubeMetadataErrorMessage = nil
        youtubeMetadataMessage = nil
        defer { isLoadingYoutubeVideoMetadata = false }

        do {
            let client = APIClient(configuration: configuration)
            let request = YoutubeVideoMetadataPreviewLookupRequest(sourceName: trimmedSourceName, force: force)
            let response = try await client.lookupYoutubeMetadataPreview(request)
            youtubeVideoMetadataPreview = response
            if let youtubeMetadata = response.youtubeMetadata {
                updateYoutubeMetadataSection("youtube") { section in
                    for (key, value) in youtubeMetadata {
                        section[key] = value
                    }
                }
                syncYoutubeMediaMetadataJSONText()
                youtubeMetadataMessage = "Loaded YouTube metadata for \(response.sourceName ?? trimmedSourceName)."
            } else {
                youtubeMetadataMessage = "No YouTube metadata match for \(response.sourceName ?? trimmedSourceName)."
            }
        } catch {
            youtubeMetadataErrorMessage = error.localizedDescription
        }
    }

    func resetYoutubeMetadataState() {
        youtubeTvMetadataPreview = nil
        youtubeVideoMetadataPreview = nil
        youtubeMetadataMessage = nil
        youtubeMetadataErrorMessage = nil
        youtubeMediaMetadataDraft = ["source": .string("apple")]
        syncYoutubeMediaMetadataJSONText()
    }

    func clearYoutubeTvMetadataCache(
        query: String,
        using appState: AppState
    ) async {
        guard let configuration = appState.configuration else {
            youtubeMetadataErrorMessage = "API configuration is unavailable."
            return
        }
        let trimmedQuery = query.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmedQuery.isEmpty else {
            youtubeMetadataErrorMessage = "Choose a video before clearing TV metadata cache."
            return
        }

        isClearingYoutubeTvMetadataCache = true
        youtubeMetadataErrorMessage = nil
        youtubeMetadataMessage = nil
        defer { isClearingYoutubeTvMetadataCache = false }

        do {
            let client = APIClient(configuration: configuration)
            let response = try await client.clearSubtitleTvMetadataCache(query: trimmedQuery)
            youtubeMetadataMessage = AppleBookCreateMetadataJSON.cacheClearMessage(
                cleared: response.cleared,
                kind: "TV",
                query: trimmedQuery
            )
        } catch {
            youtubeMetadataErrorMessage = error.localizedDescription
        }
    }

    func clearYoutubeVideoMetadataCache(
        query: String,
        using appState: AppState
    ) async {
        guard let configuration = appState.configuration else {
            youtubeMetadataErrorMessage = "API configuration is unavailable."
            return
        }
        let trimmedQuery = query.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmedQuery.isEmpty else {
            youtubeMetadataErrorMessage = "Choose a video before clearing YouTube metadata cache."
            return
        }

        isClearingYoutubeMetadataCache = true
        youtubeMetadataErrorMessage = nil
        youtubeMetadataMessage = nil
        defer { isClearingYoutubeMetadataCache = false }

        do {
            let client = APIClient(configuration: configuration)
            let response = try await client.clearYoutubeMetadataCache(query: trimmedQuery)
            youtubeMetadataMessage = AppleBookCreateMetadataJSON.cacheClearMessage(
                cleared: response.cleared,
                kind: "YouTube",
                query: trimmedQuery
            )
        } catch {
            youtubeMetadataErrorMessage = error.localizedDescription
        }
    }

    func updateYoutubeMediaMetadata(section: String?, key: String, value: String) {
        let trimmedValue = value.trimmingCharacters(in: .whitespacesAndNewlines)
        if let section = section?.trimmingCharacters(in: .whitespacesAndNewlines), !section.isEmpty {
            updateYoutubeMetadataSection(section) { sectionDraft in
                if trimmedValue.isEmpty {
                    sectionDraft.removeValue(forKey: key)
                } else {
                    sectionDraft[key] = .string(trimmedValue)
                }
            }
        } else if trimmedValue.isEmpty {
            youtubeMediaMetadataDraft.removeValue(forKey: key)
        } else {
            youtubeMediaMetadataDraft[key] = .string(trimmedValue)
        }
        youtubeMediaMetadataDraft["source"] = .string("apple")
        syncYoutubeMediaMetadataJSONText()
    }

    func updateYoutubeMediaMetadataNumber(section: String, key: String, value: String) {
        let trimmedValue = value.trimmingCharacters(in: .whitespacesAndNewlines)
        updateYoutubeMetadataSection(section) { sectionDraft in
            guard !trimmedValue.isEmpty else {
                sectionDraft.removeValue(forKey: key)
                return
            }
            guard let parsed = Double(trimmedValue), parsed.isFinite, parsed > 0 else {
                return
            }
            sectionDraft[key] = .number(floor(parsed))
        }
        youtubeMediaMetadataDraft["source"] = .string("apple")
        syncYoutubeMediaMetadataJSONText()
    }

    func updateYoutubeMediaMetadataNestedText(
        section: String,
        nestedKey: String,
        key: String,
        value: String
    ) {
        updateYoutubeMetadataSection(section) { sectionDraft in
            AppleBookCreateMetadataJSON.updateNestedText(
                in: &sectionDraft,
                nestedKey: nestedKey,
                key: key,
                value: value
            )
        }
        youtubeMediaMetadataDraft["source"] = .string("apple")
        syncYoutubeMediaMetadataJSONText()
    }

    func syncYoutubeMediaMetadataJSONText() {
        youtubeMediaMetadataJSONText = AppleBookCreateMetadataJSON.prettyString(from: youtubeMediaMetadataDraft)
        youtubeMediaMetadataJSONErrorMessage = nil
    }

    func applyYoutubeMediaMetadataJSONText() {
        let parsed = AppleBookCreateMetadataJSON.parseObject(youtubeMediaMetadataJSONText)
        if let error = parsed.error {
            youtubeMediaMetadataJSONErrorMessage = error
            return
        }
        youtubeMediaMetadataDraft = AppleBookCreatePresentation.normalizedYoutubeMediaMetadata(parsed.metadata ?? [:])
        syncYoutubeMediaMetadataJSONText()
        youtubeMetadataMessage = "Applied advanced metadata JSON."
        youtubeMetadataErrorMessage = nil
    }

    func youtubeMediaMetadataText(section: String?, key: String) -> String {
        if let section,
           let sectionDraft = youtubeMediaMetadataDraft[section]?.objectValue {
            return sectionDraft[key]?.stringValue ?? ""
        }
        return youtubeMediaMetadataDraft[key]?.stringValue ?? ""
    }

    func youtubeMediaMetadataNestedText(section: String, nestedKey: String, keys: [String]) -> String {
        guard let nested = youtubeMediaMetadataDraft[section]?.objectValue?[nestedKey]?.objectValue else {
            return ""
        }
        for key in keys {
            if let value = nested[key]?.stringValue {
                return value
            }
        }
        return ""
    }

    private func ensureSubtitleMediaMetadataDraft() {
        if subtitleMediaMetadataDraft == nil {
            subtitleMediaMetadataDraft = [:]
        }
    }

    private func normalizeSubtitleMetadataAfterEdit() {
        guard let draft = subtitleMediaMetadataDraft else {
            return
        }
        subtitleMediaMetadataDraft = AppleBookCreatePresentation.normalizedSubtitleMediaMetadata(draft)
    }

    private func updateSubtitleMetadataSection(
        _ section: String,
        mutate: (inout [String: JSONValue]) -> Void
    ) {
        ensureSubtitleMediaMetadataDraft()
        var sectionDraft = subtitleMediaMetadataDraft?[section]?.objectValue ?? [:]
        mutate(&sectionDraft)
        if sectionDraft.isEmpty {
            subtitleMediaMetadataDraft?.removeValue(forKey: section)
        } else {
            subtitleMediaMetadataDraft?[section] = .object(sectionDraft)
        }
    }

    private func mergeYoutubeTvMetadata(_ mediaMetadata: [String: JSONValue]) {
        let preservedYoutube = youtubeMediaMetadataDraft["youtube"]
        youtubeMediaMetadataDraft = mediaMetadata
        if preservedYoutube != nil, youtubeMediaMetadataDraft["youtube"] == nil {
            youtubeMediaMetadataDraft["youtube"] = preservedYoutube
        }
        youtubeMediaMetadataDraft["source"] = .string("apple")
    }

    private func updateYoutubeMetadataSection(
        _ section: String,
        mutate: (inout [String: JSONValue]) -> Void
    ) {
        var sectionDraft = youtubeMediaMetadataDraft[section]?.objectValue ?? [:]
        mutate(&sectionDraft)
        if sectionDraft.isEmpty {
            youtubeMediaMetadataDraft.removeValue(forKey: section)
        } else {
            youtubeMediaMetadataDraft[section] = .object(sectionDraft)
        }
        youtubeMediaMetadataDraft["source"] = .string("apple")
    }
}
