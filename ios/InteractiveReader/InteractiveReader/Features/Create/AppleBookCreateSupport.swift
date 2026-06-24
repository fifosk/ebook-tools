import Foundation

enum AppleBookCreatePresentation {
    static func resolvedDefaults(
        from options: BookCreationOptionsResponse,
        editedFields: Set<AppleBookCreateEditedField>,
        currentSentenceCount: Int
    ) -> AppleCreateResolvedDefaults {
        AppleCreateResolvedDefaults(
            topic: editedFields.contains(.topic) ? nil : trimmed(options.defaults.topic).nonEmptyValue,
            bookName: editedFields.contains(.bookName) ? nil : trimmed(options.defaults.bookName).nonEmptyValue,
            genre: editedFields.contains(.genre) ? nil : trimmed(options.defaults.genre).nonEmptyValue,
            author: editedFields.contains(.author)
                ? nil
                : (trimmed(options.defaults.author).nonEmptyValue ?? "Me"),
            sentenceCount: clampSentenceCount(
                editedFields.contains(.sentenceCount) ? currentSentenceCount : options.sentenceBounds.default,
                bounds: options.sentenceBounds
            ),
            inputLanguage: editedFields.contains(.inputLanguage)
                ? nil
                : AppleBookCreateLanguage(backendValue: options.defaults.inputLanguage),
            targetLanguage: editedFields.contains(.targetLanguage)
                ? nil
                : targetLanguageDefaults(from: options.defaults).primary,
            additionalTargetLanguages: editedFields.contains(.additionalTargetLanguages)
                ? nil
                : targetLanguageDefaults(from: options.defaults).additionalTargets,
            voice: editedFields.contains(.voice)
                ? nil
                : AppleBookCreateVoiceOption(backendValue: options.defaults.voice),
            generateAudio: editedFields.contains(.generateAudio)
                ? nil
                : options.pipelineDefaults.generateAudio,
            audioMode: editedFields.contains(.audioMode)
                ? nil
                : normalizedMode(options.pipelineDefaults.audioMode, fallback: "4"),
            audioBitrateKbps: editedFields.contains(.audioBitrateKbps)
                ? nil
                : options.pipelineDefaults.audioBitrateKbps.map { "\($0)" } ?? "",
            writtenMode: editedFields.contains(.writtenMode)
                ? nil
                : normalizedMode(options.pipelineDefaults.writtenMode, fallback: "4"),
            tempo: editedFields.contains(.tempo)
                ? nil
                : clampTempo(options.pipelineDefaults.tempo),
            bookSentencesPerOutputFile: editedFields.contains(.bookSentencesPerOutputFile)
                ? nil
                : clampBookSentencesPerOutputFile(options.pipelineDefaults.sentencesPerOutputFile),
            stitchFull: editedFields.contains(.stitchFull)
                ? nil
                : options.pipelineDefaults.stitchFull,
            includeTransliteration: editedFields.contains(.includeTransliteration)
                ? nil
                : options.pipelineDefaults.includeTransliteration,
            bookTranslationProvider: editedFields.contains(.bookTranslationProvider)
                ? nil
                : AppleSubtitleTranslationProvider(backendValue: options.pipelineDefaults.translationProvider),
            bookTranslationBatchSize: editedFields.contains(.bookTranslationBatchSize)
                ? nil
                : clampSubtitleTranslationBatchSize(options.pipelineDefaults.translationBatchSize),
            bookTransliterationMode: editedFields.contains(.bookTransliterationMode)
                ? nil
                : AppleSubtitleTransliterationMode(backendValue: options.pipelineDefaults.transliterationMode),
            enableLookupCache: editedFields.contains(.enableLookupCache)
                ? nil
                : options.pipelineDefaults.enableLookupCache,
            bookLookupCacheBatchSize: editedFields.contains(.bookLookupCacheBatchSize)
                ? nil
                : clampSubtitleTranslationBatchSize(options.pipelineDefaults.lookupCacheBatchSize),
            outputHtml: editedFields.contains(.outputHtml)
                ? nil
                : options.pipelineDefaults.outputHtml,
            outputPdf: editedFields.contains(.outputPdf)
                ? nil
                : options.pipelineDefaults.outputPdf,
            includeImages: editedFields.contains(.includeImages)
                ? nil
                : options.generatedSourceDefaults.addImages,
            imagePromptPipeline: editedFields.contains(.imagePromptPipeline)
                ? nil
                : (
                    AppleGeneratedBookImagePromptPipeline(
                        backendValue: options.generatedSourceDefaults.imagePromptPipeline
                    ) ?? .promptPlan
                ),
            imageStyleTemplate: editedFields.contains(.imageStyleTemplate)
                ? nil
                : (
                    AppleGeneratedBookImageStyleTemplate(
                        backendValue: options.generatedSourceDefaults.imageStyleTemplate
                    ) ?? .wireframe
                ),
            imagePromptContextSentences: editedFields.contains(.imagePromptContextSentences)
                ? nil
                : clampImagePromptContextSentences(options.generatedSourceDefaults.imagePromptContextSentences),
            imageWidth: editedFields.contains(.imageWidth)
                ? nil
                : normalizedImageDimension(options.generatedSourceDefaults.imageWidth),
            imageHeight: editedFields.contains(.imageHeight)
                ? nil
                : normalizedImageDimension(options.generatedSourceDefaults.imageHeight),
            subtitleTranslationProvider: editedFields.contains(.subtitleTranslationProvider)
                ? nil
                : AppleSubtitleTranslationProvider(backendValue: options.pipelineDefaults.translationProvider),
            subtitleWorkerCount: editedFields.contains(.subtitleWorkerCount)
                ? nil
                : options.subtitleDefaults.map { clampSubtitleWorkerCount($0.workerCount) },
            subtitleBatchSize: editedFields.contains(.subtitleBatchSize)
                ? nil
                : options.subtitleDefaults.map { clampSubtitleBatchSize($0.batchSize) },
            subtitleTranslationBatchSize: editedFields.contains(.subtitleTranslationBatchSize)
                ? nil
                : (
                    options.subtitleDefaults.map { clampSubtitleTranslationBatchSize($0.translationBatchSize) }
                        ?? options.youtubeDubDefaults.map { clampSubtitleTranslationBatchSize($0.translationBatchSize) }
                ),
            subtitleAssFontSize: editedFields.contains(.subtitleAssFontSize)
                ? nil
                : options.subtitleDefaults.map { clampAssFontSize($0.assFontSize) },
            subtitleAssEmphasisScale: editedFields.contains(.subtitleAssEmphasisScale)
                ? nil
                : options.subtitleDefaults.map { clampAssEmphasisScale($0.assEmphasisScale) },
            youtubeOriginalMixPercent: editedFields.contains(.youtubeOriginalMixPercent)
                ? nil
                : options.youtubeDubDefaults.map { clampYoutubeOriginalMixPercent($0.originalMixPercent) },
            youtubeFlushSentences: editedFields.contains(.youtubeFlushSentences)
                ? nil
                : options.youtubeDubDefaults.map { clampYoutubeFlushSentences($0.flushSentences) },
            youtubeTargetHeight: editedFields.contains(.youtubeTargetHeight)
                ? nil
                : options.youtubeDubDefaults.flatMap { AppleYoutubeDubTargetHeight(rawValue: $0.targetHeight) },
            youtubePreserveAspectRatio: editedFields.contains(.youtubePreserveAspectRatio)
                ? nil
                : options.youtubeDubDefaults?.preserveAspectRatio,
            youtubeSplitBatches: editedFields.contains(.youtubeSplitBatches)
                ? nil
                : options.youtubeDubDefaults?.splitBatches,
            youtubeStitchBatches: editedFields.contains(.youtubeStitchBatches)
                ? nil
                : options.youtubeDubDefaults?.stitchBatches
        )
    }

    static func clampSentenceCount(
        _ value: Int,
        bounds: BookCreationSentenceBounds
    ) -> Int {
        max(bounds.min, min(bounds.max, value))
    }

    static func clampImagePromptContextSentences(_ value: Int) -> Int {
        clamp(value, to: 0...50)
    }

    static func clampImagePromptBatchSize(_ value: Int) -> Int {
        clamp(value, to: 1...50)
    }

    static func clampBookSentencesPerOutputFile(_ value: Int) -> Int {
        clamp(value, to: AppleBookOutputChunking.sentencesPerOutputFileRange)
    }

    static func normalizedImageDimension(_ value: String) -> String {
        let trimmedValue = trimmed(value)
        guard let parsed = Double(trimmedValue), parsed.isFinite else {
            return "512"
        }
        return "\(max(64, Int(parsed.rounded(.down))))"
    }

    static func normalizedImageSteps(_ value: String) -> Int? {
        let trimmedValue = trimmed(value)
        guard !trimmedValue.isEmpty,
              let parsed = Double(trimmedValue),
              parsed.isFinite else {
            return nil
        }
        return max(1, Int(parsed.rounded(.down)))
    }

    static func normalizedImageCfgScale(_ value: String) -> Double? {
        let trimmedValue = trimmed(value)
        guard !trimmedValue.isEmpty,
              let parsed = Double(trimmedValue),
              parsed.isFinite else {
            return nil
        }
        return max(0, parsed)
    }

    static func normalizedPositiveInteger(_ value: String) -> Int? {
        let trimmedValue = trimmed(value)
        guard !trimmedValue.isEmpty,
              let parsed = Double(trimmedValue),
              parsed.isFinite else {
            return nil
        }
        return max(1, Int(parsed.rounded(.down)))
    }

    static func normalizedImageApiBaseURLs(_ value: String) -> [String] {
        var urls = [String]()
        var seen = Set<String>()
        let separators = CharacterSet(charactersIn: ",\n")
        for component in value.components(separatedBy: separators) {
            let normalized = component.trimmingCharacters(in: .whitespacesAndNewlines)
                .replacingOccurrences(of: #"/+$"#, with: "", options: .regularExpression)
            guard !normalized.isEmpty, !seen.contains(normalized) else {
                continue
            }
            seen.insert(normalized)
            urls.append(normalized)
        }
        return urls
    }

    static func normalizedEndSentence(_ value: String, startSentence: Int) -> Int? {
        let trimmedValue = trimmed(value)
        guard !trimmedValue.isEmpty else { return nil }
        let isOffset = trimmedValue.hasPrefix("+")
        let numericValue = isOffset ? trimmed(String(trimmedValue.dropFirst())) : trimmedValue
        guard let parsed = normalizedPositiveInteger(numericValue) else { return nil }
        let candidate = isOffset ? startSentence + parsed - 1 : parsed
        return max(startSentence, candidate)
    }

    static func normalizedPositiveNumber(_ value: String) -> Double? {
        let trimmedValue = trimmed(value)
        guard !trimmedValue.isEmpty,
              let parsed = Double(trimmedValue),
              parsed.isFinite else {
            return nil
        }
        return max(1, parsed)
    }

    static func normalizedMode(_ value: String, fallback: String) -> String {
        let trimmedValue = trimmed(value)
        guard !trimmedValue.isEmpty else { return fallback }
        return trimmedValue
    }

    static func normalizedAudioBitrate(_ value: String) -> Int? {
        let trimmedValue = trimmed(value)
        guard !trimmedValue.isEmpty,
              let parsed = Double(trimmedValue),
              parsed.isFinite else {
            return nil
        }
        return max(32, Int(parsed.rounded(.down)))
    }

    static func clampTempo(_ value: Double) -> Double {
        guard value.isFinite else { return 1.0 }
        return min(2.0, max(0.5, value))
    }

    static func availableInputLanguages(
        from options: BookCreationOptionsResponse?
    ) -> [AppleBookCreateLanguage] {
        availableLanguages(options?.supportedInputLanguages ?? [])
    }

    static func availableTargetLanguages(
        from options: BookCreationOptionsResponse?
    ) -> [AppleBookCreateLanguage] {
        availableLanguages(options?.supportedOutputLanguages ?? [])
    }

    static func availableVoices(
        from options: BookCreationOptionsResponse?,
        selected: AppleBookCreateVoiceOption?
    ) -> [AppleBookCreateVoiceOption] {
        availableVoices(
            from: options,
            inventory: nil,
            language: "",
            selected: selected
        )
    }

    static func availableVoices(
        from options: BookCreationOptionsResponse?,
        inventory: AppleBookCreateVoiceInventory?,
        language: String,
        selected: AppleBookCreateVoiceOption?
    ) -> [AppleBookCreateVoiceOption] {
        let baseOptions = AppleBookCreateVoiceOption.options(
            from: options?.supportedVoices ?? [],
            selected: selected
        )
        let inventoryOptions = voiceInventoryOptions(from: inventory, language: language)
        return mergedVoiceOptions(baseOptions + inventoryOptions, selected: selected)
    }

    static func voiceInventoryOptions(
        from inventory: AppleBookCreateVoiceInventory?,
        language: String
    ) -> [AppleBookCreateVoiceOption] {
        guard let inventory else { return [] }
        let normalizedLanguage = normalizedVoiceLanguage(language)
        let baseLanguage = baseVoiceLanguage(normalizedLanguage)
        guard !baseLanguage.isEmpty else { return [] }

        var options = [AppleBookCreateVoiceOption]()
        var seen = Set<String>()

        for entry in inventory.gtts where voiceLanguageMatches(entry.code, normalizedLanguage: normalizedLanguage) {
            let identifier = "gTTS-\(baseVoiceLanguage(entry.code))"
            appendVoiceOption(identifier, to: &options, seen: &seen)
        }

        for voice in inventory.macos.sorted(by: { $0.name < $1.name })
            where voiceLanguageMatches(voice.lang, normalizedLanguage: normalizedLanguage) {
            appendVoiceOption(macOSVoiceIdentifier(voice), to: &options, seen: &seen)
        }

        for voice in inventory.piper.sorted(by: { $0.name < $1.name })
            where voiceLanguageMatches(voice.lang, normalizedLanguage: normalizedLanguage) {
            appendVoiceOption(voice.name, to: &options, seen: &seen)
        }

        return options
    }

    static func sampleSentence(language: String, fallbackLabel: String) -> String {
        let code = normalizedVoiceLanguage(language)
        let base = baseVoiceLanguage(code)
        switch base {
        case "ar":
            return "مرحبا! هذه جملة نموذجية لتحويل النص إلى كلام."
        case "de":
            return "Hallo! Dies ist ein Beispielsatz für Text-zu-Sprache."
        case "en":
            return "Hello! This is a sample sentence for text-to-speech."
        case "es":
            return "¡Hola! Esta es una frase de muestra para texto a voz."
        case "fr":
            return "Bonjour ! Ceci est une phrase d'exemple pour la synthese vocale."
        case "sk":
            return "Ahoj! Toto je ukazkova veta pre prevod textu na rec."
        default:
            let label = trimmed(fallbackLabel).nonEmptyValue ?? language
            return "Sample narration for \(label)."
        }
    }

    static func voicePreviewKey(language: String) -> String {
        normalizedVoiceLanguage(language).lowercased()
    }

    private static func mergedVoiceOptions(
        _ options: [AppleBookCreateVoiceOption],
        selected: AppleBookCreateVoiceOption?
    ) -> [AppleBookCreateVoiceOption] {
        var seen = Set<String>()
        var merged = [AppleBookCreateVoiceOption]()
        for option in options where seen.insert(option.backendValue.lowercased()).inserted {
            merged.append(option)
        }
        if let selected, !seen.contains(selected.backendValue.lowercased()) {
            merged.insert(selected, at: 0)
        }
        return merged.isEmpty ? AppleBookCreateVoiceOption.fallbackOptions : merged
    }

    private static func appendVoiceOption(
        _ value: String,
        to options: inout [AppleBookCreateVoiceOption],
        seen: inout Set<String>
    ) {
        guard let option = AppleBookCreateVoiceOption(backendValue: value),
              seen.insert(option.backendValue.lowercased()).inserted else {
            return
        }
        options.append(option)
    }

    private static func macOSVoiceIdentifier(_ voice: AppleBookCreateVoiceInventory.MacOSVoice) -> String {
        let quality = trimmed(voice.quality ?? "").nonEmptyValue ?? "Default"
        let gender = trimmed(voice.gender ?? "").nonEmptyValue.map { " - \(capitalizedFirst($0))" } ?? ""
        return "\(voice.name) - \(voice.lang) - (\(quality))\(gender)"
    }

    private static func capitalizedFirst(_ value: String) -> String {
        guard let first = value.first else { return value }
        return first.uppercased() + value.dropFirst()
    }

    private static func voiceLanguageMatches(
        _ candidate: String,
        normalizedLanguage: String
    ) -> Bool {
        let normalizedCandidate = normalizedVoiceLanguage(candidate)
        guard !normalizedCandidate.isEmpty, !normalizedLanguage.isEmpty else { return false }
        if normalizedCandidate == normalizedLanguage {
            return true
        }
        return baseVoiceLanguage(normalizedCandidate) == baseVoiceLanguage(normalizedLanguage)
    }

    private static func normalizedVoiceLanguage(_ value: String) -> String {
        let normalized = trimmed(value)
            .replacingOccurrences(of: "_", with: "-")
            .lowercased()
        let languageMap = [
            "english": "en",
            "arabic": "ar",
            "spanish": "es",
            "french": "fr",
            "german": "de",
            "slovak": "sk"
        ]
        return languageMap[normalized] ?? normalized
    }

    private static func baseVoiceLanguage(_ value: String) -> String {
        normalizedVoiceLanguage(value)
            .split(separator: "-", omittingEmptySubsequences: true)
            .first
            .map(String.init) ?? ""
    }

    static func latestNarrationJob(from jobs: [PipelineStatusResponse]) -> PipelineStatusResponse? {
        var latest: (job: PipelineStatusResponse, createdAt: Date)?
        for job in jobs where isReusableNarrationJob(job) {
            guard let createdAt = parseJobDate(job.createdAt),
                  job.parameters?.objectValue != nil
            else {
                continue
            }
            if latest == nil || createdAt > latest!.createdAt {
                latest = (job, createdAt)
            }
        }
        return latest?.job
    }

    static func latestGeneratedBookJob(from jobs: [PipelineStatusResponse]) -> PipelineStatusResponse? {
        latestJob(from: jobs) { job in
            jobHasBookGeneration(job)
        }
    }

    static func latestSubtitleJob(from jobs: [PipelineStatusResponse]) -> PipelineStatusResponse? {
        latestJob(from: jobs) { job in
            job.jobType.lowercased() == "subtitle"
        }
    }

    static func latestYoutubeJob(from jobs: [PipelineStatusResponse]) -> PipelineStatusResponse? {
        latestJob(from: jobs) { job in
            job.jobType.lowercased() == "youtube_dub"
        }
    }

    static func latestJob(
        from jobs: [PipelineStatusResponse],
        matching predicate: (PipelineStatusResponse) -> Bool
    ) -> PipelineStatusResponse? {
        var latest: (job: PipelineStatusResponse, createdAt: Date)?
        for job in jobs where predicate(job) {
            guard let createdAt = parseJobDate(job.createdAt),
                  job.parameters?.objectValue != nil
            else {
                continue
            }
            if latest == nil || createdAt > latest!.createdAt {
                latest = (job, createdAt)
            }
        }
        return latest?.job
    }

    static func isReusableNarrationJob(_ job: PipelineStatusResponse) -> Bool {
        let jobType = job.jobType.lowercased()
        return !jobType.contains("subtitle") && jobType != "youtube_dub" && !jobHasBookGeneration(job)
    }

    static func jobHasBookGeneration(_ job: PipelineStatusResponse) -> Bool {
        guard let parameters = job.parameters?.objectValue else { return false }
        if parameters["book_generation"]?.objectValue != nil {
            return true
        }
        if let request = parameters["request"]?.objectValue,
           request["book_generation"]?.objectValue != nil {
            return true
        }
        return false
    }

    static func narrationString(
        _ job: PipelineStatusResponse,
        keys: [String]
    ) -> String? {
        guard let parameters = job.parameters?.objectValue else { return nil }
        return narrationString(in: parameters, keys: keys)
    }

    static func narrationString(
        in parameters: [String: JSONValue],
        keys: [String]
    ) -> String? {
        let sources = narrationParameterSources(parameters)
        for source in sources {
            for key in keys {
                if let value = source[key]?.stringValue?.nonEmptyValue {
                    return value
                }
            }
        }
        return nil
    }

    static func historyString(
        in sources: [[String: JSONValue]],
        keys: [String]
    ) -> String? {
        for source in sources {
            for key in keys {
                if let value = source[key]?.stringValue?.nonEmptyValue {
                    return value
                }
            }
        }
        return nil
    }

    static func narrationStringArray(
        _ job: PipelineStatusResponse,
        keys: [String]
    ) -> [String]? {
        guard let parameters = job.parameters?.objectValue else { return nil }
        let sources = narrationParameterSources(parameters)
        for source in sources {
            for key in keys {
                guard let value = source[key] else { continue }
                if let array = value.arrayValue {
                    let strings = array.compactMap { $0.stringValue?.nonEmptyValue }
                    if !strings.isEmpty {
                        return strings
                    }
                }
                if let string = value.stringValue?.nonEmptyValue {
                    let strings = normalizedLanguageList(string.split(separator: ",").map(String.init))
                    if !strings.isEmpty {
                        return strings
                    }
                }
            }
        }
        return nil
    }

    static func historyStringArray(
        in sources: [[String: JSONValue]],
        keys: [String]
    ) -> [String]? {
        for source in sources {
            for key in keys {
                guard let value = source[key] else { continue }
                if let array = value.arrayValue {
                    let strings = array.compactMap { $0.stringValue?.nonEmptyValue }
                    if !strings.isEmpty {
                        return strings
                    }
                }
                if let string = value.stringValue?.nonEmptyValue {
                    let strings = normalizedLanguageList(string.split(separator: ",").map(String.init))
                    if !strings.isEmpty {
                        return strings
                    }
                }
            }
        }
        return nil
    }

    static func narrationInt(
        _ job: PipelineStatusResponse,
        keys: [String]
    ) -> Int? {
        guard let parameters = job.parameters?.objectValue else { return nil }
        let sources = narrationParameterSources(parameters)
        for source in sources {
            for key in keys {
                if let value = source[key]?.intValue {
                    return value
                }
            }
        }
        return nil
    }

    static func historyInt(
        in sources: [[String: JSONValue]],
        keys: [String]
    ) -> Int? {
        for source in sources {
            for key in keys {
                if let value = source[key]?.intValue {
                    return value
                }
            }
        }
        return nil
    }

    static func historyDouble(
        _ job: PipelineStatusResponse,
        keys: [String]
    ) -> Double? {
        guard let parameters = job.parameters?.objectValue else { return nil }
        let sources = narrationParameterSources(parameters)
        for source in sources {
            for key in keys {
                guard let value = source[key] else { continue }
                if let doubleValue = historyDouble(from: value) {
                    return doubleValue
                }
            }
        }
        return nil
    }

    static func historyDouble(
        in sources: [[String: JSONValue]],
        keys: [String]
    ) -> Double? {
        for source in sources {
            for key in keys {
                guard let value = source[key] else { continue }
                if let doubleValue = historyDouble(from: value) {
                    return doubleValue
                }
            }
        }
        return nil
    }

    static func narrationBool(
        _ job: PipelineStatusResponse,
        keys: [String]
    ) -> Bool? {
        guard let parameters = job.parameters?.objectValue else { return nil }
        let sources = narrationParameterSources(parameters)
        for source in sources {
            for key in keys {
                guard let value = source[key] else { continue }
                if case let .bool(boolValue) = value {
                    return boolValue
                }
                if let string = value.stringValue?.lowercased() {
                    if ["1", "true", "yes", "on"].contains(string) {
                        return true
                    }
                    if ["0", "false", "no", "off"].contains(string) {
                        return false
                    }
                }
            }
        }
        return nil
    }

    static func historyBool(
        in sources: [[String: JSONValue]],
        keys: [String]
    ) -> Bool? {
        for source in sources {
            for key in keys {
                guard let value = source[key] else { continue }
                if case let .bool(boolValue) = value {
                    return boolValue
                }
                if let string = value.stringValue?.lowercased() {
                    if ["1", "true", "yes", "on"].contains(string) {
                        return true
                    }
                    if ["0", "false", "no", "off"].contains(string) {
                        return false
                    }
                }
            }
        }
        return nil
    }

    static func historyOffset(
        _ job: PipelineStatusResponse,
        stringKeys: [String],
        secondsKeys: [String],
        allowRelative: Bool
    ) -> String? {
        if let seconds = historyDouble(job, keys: secondsKeys) {
            return formatHistorySeconds(seconds)
        }

        guard let rawValue = narrationString(job, keys: stringKeys) else {
            return nil
        }
        if allowRelative {
            return SubtitleTimecodeInput.normalize(rawValue, allowRelative: true)
        }
        return normalizeYoutubeOffset(rawValue)
    }

    static func historyDouble(from value: JSONValue) -> Double? {
        switch value {
        case let .number(number):
            guard number.isFinite else { return nil }
            return number
        case let .string(string):
            let trimmedValue = trimmed(string)
            guard let parsed = Double(trimmedValue), parsed.isFinite else {
                return nil
            }
            return parsed
        case let .bool(bool):
            return bool ? 1 : 0
        case let .array(values):
            for value in values {
                if let doubleValue = historyDouble(from: value) {
                    return doubleValue
                }
            }
            return nil
        default:
            return nil
        }
    }

    static func formatHistorySeconds(_ value: Double) -> String? {
        guard value.isFinite, value >= 0 else { return nil }
        let totalSeconds = Int(value.rounded(.down))
        let hours = totalSeconds / 3600
        let minutes = (totalSeconds % 3600) / 60
        let seconds = totalSeconds % 60
        if hours > 0 {
            return [hours, minutes, seconds].map(formatTimecodeComponent).joined(separator: ":")
        }
        return "\(formatTimecodeComponent(minutes)):\(formatTimecodeComponent(seconds))"
    }

    static func formatTimecodeComponent(_ value: Int) -> String {
        String(format: "%02d", value)
    }

    static func generatedBookParameterSources(
        _ parameters: [String: JSONValue]
    ) -> [[String: JSONValue]] {
        var sources = [[String: JSONValue]]()
        appendGeneratedBookSources(from: parameters, to: &sources)
        if let request = parameters["request"]?.objectValue {
            appendGeneratedBookSources(from: request, to: &sources)
        }
        sources.append(parameters)
        return sources
    }

    static func appendGeneratedBookSources(
        from parameters: [String: JSONValue],
        to sources: inout [[String: JSONValue]]
    ) {
        if let bookGeneration = parameters["book_generation"]?.objectValue {
            sources.append(bookGeneration)
        }
        if let inputs = parameters["inputs"]?.objectValue {
            sources.append(inputs)
            if let bookMetadata = inputs["book_metadata"]?.objectValue {
                sources.append(bookMetadata)
            }
        }
        if let pipelineOverrides = parameters["pipeline_overrides"]?.objectValue {
            sources.append(pipelineOverrides)
        }
        if let config = parameters["config"]?.objectValue {
            sources.append(config)
        }
    }

    static func narrationParameterSources(
        _ parameters: [String: JSONValue]
    ) -> [[String: JSONValue]] {
        var sources = [parameters]
        if let inputs = parameters["inputs"]?.objectValue {
            sources.insert(inputs, at: 0)
        }
        if let request = parameters["request"]?.objectValue {
            sources.append(request)
            if let requestInputs = request["inputs"]?.objectValue {
                sources.insert(requestInputs, at: 0)
            }
        }
        return sources
    }

    static func normalizedNarrationPath(_ value: String?) -> String? {
        guard let value else { return nil }
        let trimmedValue = trimmed(value)
        guard !trimmedValue.isEmpty else { return nil }
        return trimmedValue
            .trimmingCharacters(in: CharacterSet(charactersIn: "/\\"))
            .lowercased()
            .nonEmptyValue
    }

    static func parseJobDate(_ value: String) -> Date? {
        jobDateFormatterWithFractional.date(from: value) ?? jobDateFormatter.date(from: value)
    }

    private static let jobDateFormatter: ISO8601DateFormatter = {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime]
        return formatter
    }()

    private static let jobDateFormatterWithFractional: ISO8601DateFormatter = {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return formatter
    }()

    static func targetLanguageDefaults(
        from defaults: BookCreationDefaults
    ) -> AppleCreateTargetLanguageDefaults {
        let targetCandidates = defaults.targetLanguages?.isEmpty == false
            ? defaults.targetLanguages ?? []
            : (
                defaults.outputLanguages?.isEmpty == false
                    ? defaults.outputLanguages ?? []
                    : [defaults.outputLanguage]
            )
        let normalized = normalizedLanguageList(targetCandidates)
        guard let first = normalized.first else {
            return AppleCreateTargetLanguageDefaults(
                primary: AppleBookCreateLanguage(backendValue: defaults.outputLanguage),
                additionalTargets: ""
            )
        }
        let primary = AppleBookCreateLanguage(backendValue: first)
        let additionalTargets = normalized.dropFirst().joined(separator: ", ")
        return AppleCreateTargetLanguageDefaults(primary: primary, additionalTargets: additionalTargets)
    }

    static func languagePreferences(
        inputLanguage: AppleBookCreateLanguage,
        targetLanguage: AppleBookCreateLanguage,
        additionalTargetLanguages: String,
        enableLookupCache: Bool
    ) -> AppleCreateLanguagePreferences {
        AppleCreateLanguagePreferences(
            inputLanguage: inputLanguage.backendValue,
            targetLanguages: normalizedTargetLanguages(
                primary: targetLanguage.backendValue,
                additionalTargets: additionalTargetLanguages
            ),
            enableLookupCache: enableLookupCache
        )
    }

    static func resolvedLanguagePreferences(
        from preferences: AppleCreateLanguagePreferences?
    ) -> AppleCreateResolvedLanguagePreferences? {
        guard let preferences else { return nil }
        let normalizedTargets = normalizedLanguageList(preferences.targetLanguages)
        let targetLanguage = normalizedTargets.first.flatMap(AppleBookCreateLanguage.init(backendValue:))
        let additionalTargets = normalizedTargets.dropFirst().joined(separator: ", ")
        let inputLanguage = preferences.inputLanguage
            .flatMap { AppleBookCreateLanguage(backendValue: $0) }
        guard
            inputLanguage != nil
                || targetLanguage != nil
                || !additionalTargets.isEmpty
                || preferences.enableLookupCache != nil
        else {
            return nil
        }

        return AppleCreateResolvedLanguagePreferences(
            inputLanguage: inputLanguage,
            targetLanguage: targetLanguage,
            additionalTargetLanguages: additionalTargets.isEmpty ? nil : additionalTargets,
            enableLookupCache: preferences.enableLookupCache
        )
    }

    static func voiceOverrides(
        targetLanguages: [String],
        targetVoice: AppleBookCreateVoiceOption?,
        languageVoiceOverrides: [String: String] = [:]
    ) -> [String: String] {
        var overrides = [String: String]()
        var normalizedTargets = Set<String>()
        for targetLanguage in targetLanguages {
            let language = trimmed(targetLanguage)
            guard !language.isEmpty else { continue }
            normalizedTargets.insert(language.lowercased())
            if let targetVoice {
                overrides[language] = targetVoice.backendValue
            }
        }

        for (targetLanguage, voice) in languageVoiceOverrides {
            let language = trimmed(targetLanguage)
            let voiceValue = trimmed(voice)
            guard !language.isEmpty, !voiceValue.isEmpty else { continue }
            guard normalizedTargets.contains(language.lowercased()) else { continue }
            overrides[language] = voiceValue
        }
        return overrides
    }

    static func voiceOverridePipelineValue(_ voiceOverrides: [String: String]) -> JSONValue? {
        var normalized = [String: JSONValue]()
        for (key, value) in voiceOverrides {
            let language = trimmed(key)
            let voice = trimmed(value)
            guard !language.isEmpty, !voice.isEmpty else { continue }
            normalized[language] = .string(voice)
        }
        guard !normalized.isEmpty else { return nil }
        return .object(normalized)
    }

    static func normalizedTargetLanguages(
        primary: String,
        additionalTargets: String
    ) -> [String] {
        let primaryTarget = trimmed(primary)
        guard !primaryTarget.isEmpty else { return [] }

        var seen = Set<String>()
        seen.insert(primaryTarget.lowercased())
        var targetLanguages = [primaryTarget]

        for candidate in additionalTargets.components(separatedBy: CharacterSet(charactersIn: ",\n")) {
            let target = trimmed(candidate)
            guard !target.isEmpty else { continue }

            let lookupKey = target.lowercased()
            guard !seen.contains(lookupKey) else { continue }

            seen.insert(lookupKey)
            targetLanguages.append(target)
        }
        return targetLanguages
    }

    static func normalizedLanguageList(_ languages: [String]) -> [String] {
        var normalized = [String]()
        var seen = Set<String>()
        for language in languages {
            let value = trimmed(language)
            guard !value.isEmpty else { continue }
            let lookupKey = value.lowercased()
            guard !seen.contains(lookupKey) else { continue }
            seen.insert(lookupKey)
            normalized.append(value)
        }
        return normalized
    }

    static func normalizedBookGenres(_ value: String) -> [String] {
        var genres = [String]()
        var seen = Set<String>()
        for component in value.split(separator: ",") {
            let genre = trimmed(String(component))
            guard !genre.isEmpty else { continue }
            let lookupKey = genre.lowercased()
            guard seen.insert(lookupKey).inserted else { continue }
            genres.append(genre)
        }
        return genres
    }

    static func contentIndexChapters(from value: JSONValue?) -> [AppleCreateChapterOption] {
        guard case let .object(root) = value,
              case let .array(chapterValues)? = root["chapters"] else {
            return []
        }
        var chapters = [AppleCreateChapterOption]()
        chapters.reserveCapacity(chapterValues.count)
        for (index, chapterValue) in chapterValues.enumerated() {
            guard case let .object(chapter) = chapterValue else { continue }
            let start = chapter["start_sentence"]?.intValue
                ?? chapter["startSentence"]?.intValue
                ?? chapter["start"]?.intValue
            guard let start, start > 0 else { continue }
            let sentenceCount = chapter["sentence_count"]?.intValue ?? chapter["sentenceCount"]?.intValue
            var end = chapter["end_sentence"]?.intValue
                ?? chapter["endSentence"]?.intValue
                ?? chapter["end"]?.intValue
            if end == nil, let sentenceCount {
                end = start + max(sentenceCount - 1, 0)
            }
            if let endValue = end, endValue < start {
                end = start
            }
            let id = chapter["id"]?.stringValue ?? "chapter-\(index + 1)"
            let title = chapter["title"]?.stringValue
                ?? chapter["toc_label"]?.stringValue
                ?? chapter["tocLabel"]?.stringValue
                ?? chapter["name"]?.stringValue
                ?? "Chapter \(index + 1)"
            chapters.append(
                AppleCreateChapterOption(
                    id: id,
                    title: title,
                    startSentence: start,
                    endSentence: end
                )
            )
        }
        return chapters
    }

    static func chapterRangeSelection(
        chapters: [AppleCreateChapterOption],
        startChapterID: String,
        endChapterID: String
    ) -> AppleCreateChapterRangeSelection? {
        guard let startIndex = chapters.firstIndex(where: { $0.id == startChapterID }) else {
            return nil
        }
        let requestedEndIndex = chapters.firstIndex(where: { $0.id == endChapterID }) ?? startIndex
        let endIndex = max(startIndex, requestedEndIndex)
        let startChapter = chapters[startIndex]
        let endChapter = chapters[endIndex]
        let endSentence = endChapter.endSentence ?? endChapter.startSentence
        return AppleCreateChapterRangeSelection(
            startIndex: startIndex,
            endIndex: endIndex,
            startSentence: startChapter.startSentence,
            endSentence: max(startChapter.startSentence, endSentence),
            count: endIndex - startIndex + 1,
            label: startIndex == endIndex ? startChapter.title : "\(startChapter.title) - \(endChapter.title)"
        )
    }

    static func submitButtonPresentation(
        for mode: AppleCreateMode,
        isSubmitting: Bool
    ) -> AppleCreateSubmitPresentation {
        if isSubmitting {
            return AppleCreateSubmitPresentation(title: "Submitting", systemImage: "hourglass")
        }
        switch mode {
        case .generatedBook:
            return AppleCreateSubmitPresentation(title: "Generate Audiobook", systemImage: "sparkles")
        case .narrateEbook:
            return AppleCreateSubmitPresentation(title: "Narrate EPUB", systemImage: "book")
        case .subtitleJob:
            return AppleCreateSubmitPresentation(title: "Create Subtitles", systemImage: "captions.bubble")
        case .youtubeDub:
            return AppleCreateSubmitPresentation(title: "Create Dub", systemImage: "video")
        }
    }

    static func intakeStatusPresentation(for status: PipelineIntakeStatusResponse) -> AppleCreateIntakePresentation {
        let detailLines = [
            "Delayed jobs: \(status.delayCount)",
            status.softLimit.map { "Slowdown starts at \($0) pending" },
            status.hardLimit.map { "Capacity limit is \($0) pending" },
        ].compactMap { $0 }

        if !status.acceptingJobs {
            let limit = status.hardLimit.map { " of \($0)" } ?? ""
            return AppleCreateIntakePresentation(
                label: "Queue at capacity: \(status.queueDepth) pending\(limit). Wait for jobs to clear.",
                detailLines: detailLines
            )
        }

        if status.isUnderPressure {
            return AppleCreateIntakePresentation(
                label: "Queue pressure: \(status.queueDepth) pending, \(status.activeCount) running. New jobs may start more slowly.",
                detailLines: detailLines
            )
        }

        return AppleCreateIntakePresentation(
            label: "Job intake available: \(status.queueDepth) pending, \(status.activeCount) running.",
            detailLines: detailLines
        )
    }

    static func canSubmit(_ state: AppleCreateSubmitState) -> Bool {
        guard state.hasConfiguration else { return false }
        switch state.mode {
        case .generatedBook:
            return !trimmed(state.topic).isEmpty
                && !trimmed(state.bookName).isEmpty
                && !trimmed(state.genre).isEmpty
        case .narrateEbook:
            return (state.hasNarrateLocalFile || !trimmed(state.sourcePath).isEmpty)
                && !trimmed(state.sourceBaseOutput).isEmpty
        case .subtitleJob:
            return state.hasSubtitleLocalFile || !trimmed(state.subtitleSourcePath).isEmpty
        case .youtubeDub:
            return !trimmed(state.youtubeVideoPath).isEmpty
                && !trimmed(state.youtubeSubtitlePath).isEmpty
        }
    }

    static func derivedBaseOutput(
        for mode: AppleCreateMode,
        topic: String,
        bookName: String,
        sourceBaseOutput: String,
        subtitleSourcePath: String,
        youtubeVideoPath: String
    ) -> String {
        switch mode {
        case .generatedBook:
            return deriveBaseOutputName(bookName.isEmpty ? topic : bookName)
        case .narrateEbook:
            return trimmed(sourceBaseOutput)
        case .subtitleJob:
            return deriveBaseOutputName(subtitleSourcePath)
        case .youtubeDub:
            return deriveBaseOutputName(youtubeVideoPath)
        }
    }

    static func subtitleModelLabel(_ model: String) -> String {
        let trimmedModel = trimmed(model)
        return trimmedModel.isEmpty ? "Backend default" : trimmedModel
    }

    static func subtitleTransliterationModelLabel(_ model: String) -> String {
        let trimmedModel = trimmed(model)
        return trimmedModel.isEmpty ? "Use translation model" : trimmedModel
    }

    static func availableSubtitleLlmModels(
        selected: String,
        inventory: [String]
    ) -> [String] {
        let selectedModel = trimmed(selected)
        var seen = Set<String>()
        var options: [String] = []

        if !selectedModel.isEmpty {
            seen.insert(selectedModel.lowercased())
            options.append(selectedModel)
        }

        for model in inventory {
            let trimmedModel = trimmed(model)
            guard !trimmedModel.isEmpty else { continue }
            if seen.insert(trimmedModel.lowercased()).inserted {
                options.append(trimmedModel)
            }
        }

        return options.isEmpty ? [""] : options
    }

    static func availableSubtitleTransliterationModels(
        selected: String,
        translationModel: String,
        inventory: [String]
    ) -> [String] {
        var seen = Set<String>()
        var options = [""]
        seen.insert("")

        for model in [selected, translationModel] + inventory {
            let trimmedModel = trimmed(model)
            guard !trimmedModel.isEmpty else { continue }
            if seen.insert(trimmedModel.lowercased()).inserted {
                options.append(trimmedModel)
            }
        }
        return options
    }

    static func formattedAssEmphasisScale(_ value: Double) -> String {
        clampAssEmphasisScale(value).formatted(.number.precision(.fractionLength(2)))
    }

    static func formattedYoutubeOriginalMixPercent(_ value: Double) -> String {
        "\(Int(clampYoutubeOriginalMixPercent(value).rounded()))%"
    }

    static func formatDurationLabel(seconds: Double) -> String {
        let totalSeconds = max(0, Int(seconds.rounded(.down)))
        let hours = totalSeconds / 3_600
        let minutes = (totalSeconds % 3_600) / 60
        let seconds = totalSeconds % 60
        return String(format: "%02d:%02d:%02d", hours, minutes, seconds)
    }

    static func estimatedAudioDurationLabel(sentenceCount: Int?) -> String? {
        guard let sentenceCount, sentenceCount > 0 else {
            return nil
        }
        let seconds = Double(sentenceCount) * AppleCreateEstimatedAudio.secondsPerSentence
        let sentenceLabel = sentenceCount == 1 ? "sentence" : "sentences"
        return "Estimated audio duration: ~\(formatDurationLabel(seconds: seconds)) (\(sentenceCount) \(sentenceLabel), 6.4s/sentence)"
    }

    static func estimatedNarrateSentenceCount(startSentence: String, endSentence: String) -> Int? {
        let normalizedStart = normalizedPositiveInteger(startSentence) ?? 1
        guard let normalizedEnd = normalizedEndSentence(endSentence, startSentence: normalizedStart) else {
            return nil
        }
        let count = normalizedEnd - normalizedStart + 1
        return count > 0 ? count : nil
    }

    static func clampAssFontSize(_ value: Int) -> Int {
        clamp(value, to: AppleSubtitleAssTypography.fontSizeRange)
    }

    static func clampAssEmphasisScale(_ value: Double) -> Double {
        clamp(value, to: AppleSubtitleAssTypography.emphasisScaleRange)
    }

    static func clampSubtitleTranslationBatchSize(_ value: Int) -> Int {
        clamp(value, to: AppleSubtitleTuning.translationBatchSizeRange)
    }

    static func clampSubtitleWorkerCount(_ value: Int) -> Int {
        clamp(value, to: AppleSubtitleTuning.workerCountRange)
    }

    static func clampSubtitleBatchSize(_ value: Int) -> Int {
        clamp(value, to: AppleSubtitleTuning.batchSizeRange)
    }

    static func clampYoutubeOriginalMixPercent(_ value: Double) -> Double {
        min(100, max(0, value))
    }

    static func clampYoutubeFlushSentences(_ value: Int) -> Int {
        min(200, max(1, value))
    }

    static func normalizeYoutubeOffset(_ value: String) -> String? {
        let trimmedValue = trimmed(value)
        if trimmedValue.isEmpty {
            return ""
        }
        if let seconds = Int(trimmedValue), seconds >= 0 {
            return "\(seconds)"
        }
        return SubtitleTimecodeInput.normalize(trimmedValue)
    }

    static func normalizedSubtitleTimeRange(
        start: String,
        end: String
    ) -> Result<AppleCreateTimeRange, AppleCreateValidationError> {
        guard let normalizedStart = SubtitleTimecodeInput.normalize(
            start,
            emptyValue: "00:00"
        ) else {
            return .failure(.subtitleStartTime)
        }
        guard let normalizedEnd = SubtitleTimecodeInput.normalize(
            end,
            allowRelative: true
        ) else {
            return .failure(.subtitleEndTime)
        }
        return .success(AppleCreateTimeRange(start: normalizedStart, end: normalizedEnd))
    }

    static func normalizedYoutubeOffsetRange(
        start: String,
        end: String
    ) -> Result<AppleCreateOffsetRange, AppleCreateValidationError> {
        guard let normalizedStart = normalizeYoutubeOffset(start) else {
            return .failure(.youtubeStartOffset)
        }
        guard let normalizedEnd = normalizeYoutubeOffset(end) else {
            return .failure(.youtubeEndOffset)
        }
        return .success(AppleCreateOffsetRange(start: normalizedStart, end: normalizedEnd))
    }

    static func generatedBookDraft(
        topic: String,
        bookName: String,
        genre: String,
        author: String,
        summary: String,
        year: String,
        isbn: String,
        coverFile: String,
        sourceBookTitle: String,
        sourceBookAuthor: String,
        sourceBookGenre: String,
        sourceBookSummary: String,
        sentenceCount: Int,
        inputLanguage: AppleBookCreateLanguage,
        targetLanguage: AppleBookCreateLanguage,
        additionalTargetLanguages: String,
        voice: AppleBookCreateVoiceOption,
        targetVoice: AppleBookCreateVoiceOption?,
        languageVoiceOverrides: [String: String] = [:],
        baseOutput: String,
        generateAudio: Bool,
        audioMode: String,
        audioBitrateKbps: String,
        writtenMode: String,
        tempo: Double,
        sentencesPerOutputFile: Int,
        stitchFull: Bool,
        includeTransliteration: Bool,
        translationProvider: AppleSubtitleTranslationProvider,
        llmModel: String,
        translationBatchSize: Int,
        transliterationMode: AppleSubtitleTransliterationMode,
        transliterationModel: String,
        enableLookupCache: Bool,
        lookupCacheBatchSize: Int,
        outputHtml: Bool,
        outputPdf: Bool,
        includeImages: Bool,
        imagePromptPipeline: AppleGeneratedBookImagePromptPipeline,
        imageStyleTemplate: AppleGeneratedBookImageStyleTemplate,
        imagePromptBatchingEnabled: Bool,
        imagePromptBatchSize: Int,
        imagePromptPlanBatchSize: Int,
        imagePromptContextSentences: Int,
        imageWidth: String,
        imageHeight: String,
        imageSteps: String,
        imageCfgScale: String,
        imageSamplerName: String,
        imageSeedWithPreviousImage: Bool,
        imageBlankDetectionEnabled: Bool,
        imageApiBaseURLs: String,
        imageConcurrency: String,
        imageApiTimeoutSeconds: String,
        threadCount: String,
        queueSize: String,
        jobMaxWorkers: String,
        pipelineDefaults: BookCreationPipelineDefaults?,
        generatedSourceDefaults: BookCreationGeneratedSourceDefaults?
    ) -> AppleBookCreateDraft {
        let targetLanguageValue = targetLanguage.backendValue
        let targetLanguages = normalizedTargetLanguages(
            primary: targetLanguageValue,
            additionalTargets: additionalTargetLanguages
        )
        return AppleBookCreateDraft(
            topic: trimmed(topic),
            bookName: trimmed(bookName),
            genre: trimmed(genre),
            author: trimmed(author).nonEmptyValue ?? "Me",
            summary: trimmed(summary).nonEmptyValue,
            year: trimmed(year).nonEmptyValue,
            isbn: trimmed(isbn).nonEmptyValue,
            coverFile: trimmed(coverFile).nonEmptyValue,
            sourceBookTitle: trimmed(sourceBookTitle).nonEmptyValue,
            sourceBookAuthor: trimmed(sourceBookAuthor).nonEmptyValue,
            sourceBookGenre: trimmed(sourceBookGenre).nonEmptyValue,
            sourceBookSummary: trimmed(sourceBookSummary).nonEmptyValue,
            sentenceCount: sentenceCount,
            inputLanguage: inputLanguage.backendValue,
            targetLanguage: targetLanguageValue,
            targetLanguages: targetLanguages,
            voice: voice.backendValue,
            voiceOverrides: voiceOverrides(
                targetLanguages: targetLanguages,
                targetVoice: targetVoice,
                languageVoiceOverrides: languageVoiceOverrides
            ),
            baseOutput: baseOutput,
            generateAudio: generateAudio,
            audioMode: normalizedMode(audioMode, fallback: "4"),
            audioBitrateKbps: normalizedAudioBitrate(audioBitrateKbps),
            writtenMode: normalizedMode(writtenMode, fallback: "4"),
            tempo: clampTempo(tempo),
            sentencesPerOutputFile: clampBookSentencesPerOutputFile(sentencesPerOutputFile),
            stitchFull: stitchFull,
            includeTransliteration: includeTransliteration,
            translationProvider: translationProvider.backendValue,
            llmModel: translationProvider == .llm ? trimmed(llmModel).nonEmptyValue : nil,
            translationBatchSize: clampSubtitleTranslationBatchSize(translationBatchSize),
            transliterationMode: includeTransliteration ? transliterationMode.backendValue : "default",
            transliterationModel: includeTransliteration && transliterationMode.allowsModelOverride
                ? trimmed(transliterationModel).nonEmptyValue
                : nil,
            enableLookupCache: enableLookupCache,
            lookupCacheBatchSize: clampSubtitleTranslationBatchSize(lookupCacheBatchSize),
            outputHtml: outputHtml,
            outputPdf: outputPdf,
            includeImages: includeImages,
            imagePromptPipeline: imagePromptPipeline.backendValue,
            imageStyleTemplate: imageStyleTemplate.backendValue,
            imagePromptBatchingEnabled: imagePromptBatchingEnabled,
            imagePromptBatchSize: clampImagePromptBatchSize(imagePromptBatchSize),
            imagePromptPlanBatchSize: clampImagePromptBatchSize(imagePromptPlanBatchSize),
            imagePromptContextSentences: clampImagePromptContextSentences(imagePromptContextSentences),
            imageWidth: normalizedImageDimension(imageWidth),
            imageHeight: normalizedImageDimension(imageHeight),
            imageSteps: normalizedImageSteps(imageSteps),
            imageCfgScale: normalizedImageCfgScale(imageCfgScale),
            imageSamplerName: trimmed(imageSamplerName).nonEmptyValue,
            imageSeedWithPreviousImage: imageSeedWithPreviousImage,
            imageBlankDetectionEnabled: imageBlankDetectionEnabled,
            imageApiBaseURLs: normalizedImageApiBaseURLs(imageApiBaseURLs),
            imageConcurrency: normalizedPositiveInteger(imageConcurrency),
            imageApiTimeoutSeconds: normalizedPositiveNumber(imageApiTimeoutSeconds),
            threadCount: normalizedPositiveInteger(threadCount),
            queueSize: normalizedPositiveInteger(queueSize),
            jobMaxWorkers: normalizedPositiveInteger(jobMaxWorkers),
            pipelineDefaults: pipelineDefaults,
            generatedSourceDefaults: generatedSourceDefaults
        )
    }

    static func narrateEbookDraft(
        inputFile: String,
        baseOutput: String,
        title: String,
        author: String,
        genre: String,
        summary: String,
        year: String,
        isbn: String,
        coverFile: String,
        startSentence: String,
        endSentence: String,
        inputLanguage: AppleBookCreateLanguage,
        targetLanguage: AppleBookCreateLanguage,
        additionalTargetLanguages: String,
        voice: AppleBookCreateVoiceOption,
        targetVoice: AppleBookCreateVoiceOption?,
        languageVoiceOverrides: [String: String] = [:],
        generateAudio: Bool,
        audioMode: String,
        audioBitrateKbps: String,
        writtenMode: String,
        tempo: Double,
        sentencesPerOutputFile: Int,
        stitchFull: Bool,
        includeTransliteration: Bool,
        translationProvider: AppleSubtitleTranslationProvider,
        llmModel: String,
        translationBatchSize: Int,
        transliterationMode: AppleSubtitleTransliterationMode,
        transliterationModel: String,
        enableLookupCache: Bool,
        lookupCacheBatchSize: Int,
        outputHtml: Bool,
        outputPdf: Bool,
        threadCount: String,
        queueSize: String,
        jobMaxWorkers: String,
        pipelineDefaults: BookCreationPipelineDefaults?
    ) -> AppleNarrateEbookDraft {
        let normalizedStart = normalizedPositiveInteger(startSentence) ?? 1
        let targetLanguageValue = targetLanguage.backendValue
        let targetLanguages = normalizedTargetLanguages(
            primary: targetLanguageValue,
            additionalTargets: additionalTargetLanguages
        )
        return AppleNarrateEbookDraft(
            inputFile: trimmed(inputFile),
            baseOutput: trimmed(baseOutput),
            title: trimmed(title).nonEmptyValue,
            author: trimmed(author).nonEmptyValue,
            genre: trimmed(genre).nonEmptyValue,
            summary: trimmed(summary).nonEmptyValue,
            year: trimmed(year).nonEmptyValue,
            isbn: trimmed(isbn).nonEmptyValue,
            coverFile: trimmed(coverFile).nonEmptyValue,
            startSentence: normalizedStart,
            endSentence: normalizedEndSentence(endSentence, startSentence: normalizedStart),
            inputLanguage: inputLanguage.backendValue,
            targetLanguage: targetLanguageValue,
            targetLanguages: targetLanguages,
            voice: voice.backendValue,
            voiceOverrides: voiceOverrides(
                targetLanguages: targetLanguages,
                targetVoice: targetVoice,
                languageVoiceOverrides: languageVoiceOverrides
            ),
            generateAudio: generateAudio,
            audioMode: normalizedMode(audioMode, fallback: "4"),
            audioBitrateKbps: normalizedAudioBitrate(audioBitrateKbps),
            writtenMode: normalizedMode(writtenMode, fallback: "4"),
            tempo: clampTempo(tempo),
            sentencesPerOutputFile: clampBookSentencesPerOutputFile(sentencesPerOutputFile),
            stitchFull: stitchFull,
            includeTransliteration: includeTransliteration,
            translationProvider: translationProvider.backendValue,
            llmModel: translationProvider == .llm ? trimmed(llmModel).nonEmptyValue : nil,
            translationBatchSize: clampSubtitleTranslationBatchSize(translationBatchSize),
            transliterationMode: includeTransliteration ? transliterationMode.backendValue : "default",
            transliterationModel: includeTransliteration && transliterationMode.allowsModelOverride
                ? trimmed(transliterationModel).nonEmptyValue
                : nil,
            enableLookupCache: enableLookupCache,
            lookupCacheBatchSize: clampSubtitleTranslationBatchSize(lookupCacheBatchSize),
            outputHtml: outputHtml,
            outputPdf: outputPdf,
            threadCount: normalizedPositiveInteger(threadCount),
            queueSize: normalizedPositiveInteger(queueSize),
            jobMaxWorkers: normalizedPositiveInteger(jobMaxWorkers),
            pipelineDefaults: pipelineDefaults
        )
    }

    static func subtitleJobDraft(
        sourcePath: String,
        mediaMetadata: [String: JSONValue]?,
        inputLanguage: AppleBookCreateLanguage,
        targetLanguage: AppleBookCreateLanguage,
        outputFormat: AppleSubtitleOutputFormat,
        startTime: String,
        endTime: String,
        enableTransliteration: Bool,
        highlight: Bool,
        showOriginal: Bool,
        generateAudioBook: Bool,
        mirrorBatchesToSourceDir: Bool,
        translationProvider: AppleSubtitleTranslationProvider,
        llmModel: String,
        transliterationMode: AppleSubtitleTransliterationMode,
        transliterationModel: String,
        workerCount: Int,
        batchSize: Int,
        translationBatchSize: Int,
        assFontSize: Int,
        assEmphasisScale: Double
    ) -> AppleSubtitleJobDraft {
        AppleSubtitleJobDraft(
            sourcePath: trimmed(sourcePath).nonEmptyValue,
            mediaMetadata: normalizedSubtitleMediaMetadata(mediaMetadata),
            inputLanguage: inputLanguage.backendValue,
            targetLanguage: targetLanguage.backendValue,
            outputFormat: outputFormat.rawValue,
            startTime: startTime,
            endTime: endTime.nonEmptyValue,
            enableTransliteration: enableTransliteration,
            highlight: highlight,
            showOriginal: showOriginal,
            generateAudioBook: generateAudioBook,
            mirrorBatchesToSourceDir: mirrorBatchesToSourceDir,
            translationProvider: translationProvider.backendValue,
            llmModel: translationProvider == .llm ? trimmed(llmModel).nonEmptyValue : nil,
            transliterationMode: enableTransliteration ? transliterationMode.backendValue : nil,
            transliterationModel: enableTransliteration && transliterationMode.allowsModelOverride
                ? trimmed(transliterationModel).nonEmptyValue
                : nil,
            workerCount: clampSubtitleWorkerCount(workerCount),
            batchSize: clampSubtitleBatchSize(batchSize),
            translationBatchSize: clampSubtitleTranslationBatchSize(translationBatchSize),
            assFontSize: outputFormat == .ass ? clampAssFontSize(assFontSize) : nil,
            assEmphasisScale: outputFormat == .ass ? clampAssEmphasisScale(assEmphasisScale) : nil
        )
    }

    static func normalizedSubtitleMediaMetadata(_ value: [String: JSONValue]?) -> [String: JSONValue]? {
        guard var metadata = value, !metadata.isEmpty else {
            return nil
        }
        metadata["source"] = .string("apple")
        return metadata
    }

    static func youtubeDubDraft(
        videoPath: String,
        subtitlePath: String,
        sourceLanguage: AppleBookCreateLanguage,
        subtitleLanguage: String?,
        targetLanguage: AppleBookCreateLanguage,
        voice: AppleBookCreateVoiceOption,
        mediaMetadata: [String: JSONValue],
        startTimeOffset: String,
        endTimeOffset: String,
        originalMixPercent: Double,
        flushSentences: Int,
        translationProvider: AppleSubtitleTranslationProvider,
        llmModel: String,
        translationBatchSize: Int,
        transliterationMode: AppleSubtitleTransliterationMode,
        transliterationModel: String,
        splitBatches: Bool,
        stitchBatches: Bool,
        includeTransliteration: Bool,
        targetHeight: AppleYoutubeDubTargetHeight,
        preserveAspectRatio: Bool,
        enableLookupCache: Bool
    ) -> AppleYoutubeDubDraft {
        AppleYoutubeDubDraft(
            videoPath: trimmed(videoPath),
            subtitlePath: trimmed(subtitlePath),
            mediaMetadata: normalizedYoutubeMediaMetadata(mediaMetadata),
            sourceLanguage: subtitleLanguage?.nonEmptyValue ?? sourceLanguage.backendValue,
            targetLanguage: targetLanguage.backendValue,
            voice: voice.backendValue,
            startTimeOffset: startTimeOffset.nonEmptyValue,
            endTimeOffset: endTimeOffset.nonEmptyValue,
            originalMixPercent: clampYoutubeOriginalMixPercent(originalMixPercent),
            flushSentences: clampYoutubeFlushSentences(flushSentences),
            llmModel: translationProvider == .llm ? trimmed(llmModel).nonEmptyValue : nil,
            translationProvider: translationProvider.backendValue,
            translationBatchSize: clampSubtitleTranslationBatchSize(translationBatchSize),
            transliterationMode: includeTransliteration ? transliterationMode.backendValue : nil,
            transliterationModel: includeTransliteration && transliterationMode.allowsModelOverride
                ? trimmed(transliterationModel).nonEmptyValue
                : nil,
            splitBatches: splitBatches,
            stitchBatches: splitBatches && stitchBatches,
            includeTransliteration: includeTransliteration,
            targetHeight: targetHeight.backendValue,
            preserveAspectRatio: preserveAspectRatio,
            enableLookupCache: enableLookupCache
        )
    }

    static func normalizedYoutubeMediaMetadata(_ value: [String: JSONValue]) -> [String: JSONValue] {
        var metadata = value
        metadata["source"] = .string("apple")
        return metadata
    }

    static func deriveBaseOutputName(_ value: String) -> String {
        let trimmedValue = trimmed(value)
        let withoutExtension = trimmedValue.replacingOccurrences(
            of: #"\.[^/.]+$"#,
            with: "",
            options: .regularExpression
        )
        let scalars = withoutExtension.unicodeScalars.map { scalar -> Character in
            CharacterSet.alphanumerics.contains(scalar) ? Character(scalar) : "-"
        }
        let collapsed = String(scalars)
            .split(separator: "-", omittingEmptySubsequences: true)
            .joined(separator: "-")
            .lowercased()
        return collapsed.nonEmptyValue ?? withoutExtension.nonEmptyValue ?? "generated-book"
    }

    private static func trimmed(_ value: String) -> String {
        value.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private static func availableLanguages(_ supported: [String]) -> [AppleBookCreateLanguage] {
        AppleBookCreateLanguage.options(from: supported)
    }

    private static func clamp<T: Comparable>(_ value: T, to range: ClosedRange<T>) -> T {
        min(range.upperBound, max(range.lowerBound, value))
    }
}
