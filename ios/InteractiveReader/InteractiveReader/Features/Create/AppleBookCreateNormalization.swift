import Foundation

extension AppleBookCreatePresentation {
    static func clampSentenceCount(
        _ value: Int,
        bounds: BookCreationSentenceBounds
    ) -> Int {
        max(bounds.min, min(bounds.max, value))
    }

    static func clampImagePromptContextSentences(_ value: Int) -> Int {
        bounded(value, to: 0...50)
    }

    static func clampImagePromptBatchSize(_ value: Int) -> Int {
        bounded(value, to: 1...50)
    }

    static func clampBookSentencesPerOutputFile(_ value: Int) -> Int {
        bounded(value, to: AppleBookOutputChunking.sentencesPerOutputFileRange)
    }

    static func normalizedImageDimension(_ value: String) -> String {
        let trimmedValue = normalizedNormalizationText(value)
        guard let parsed = Double(trimmedValue), parsed.isFinite else {
            return "512"
        }
        return "\(max(64, Int(parsed.rounded(.down))))"
    }

    static func normalizedImageSteps(_ value: String) -> Int? {
        let trimmedValue = normalizedNormalizationText(value)
        guard !trimmedValue.isEmpty,
              let parsed = Double(trimmedValue),
              parsed.isFinite else {
            return nil
        }
        return max(1, Int(parsed.rounded(.down)))
    }

    static func normalizedImageCfgScale(_ value: String) -> Double? {
        let trimmedValue = normalizedNormalizationText(value)
        guard !trimmedValue.isEmpty,
              let parsed = Double(trimmedValue),
              parsed.isFinite else {
            return nil
        }
        return max(0, parsed)
    }

    static func normalizedPositiveInteger(_ value: String) -> Int? {
        let trimmedValue = normalizedNormalizationText(value)
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
        let trimmedValue = normalizedNormalizationText(value)
        guard !trimmedValue.isEmpty else { return nil }
        let isOffset = trimmedValue.hasPrefix("+")
        let numericValue = isOffset ? normalizedNormalizationText(String(trimmedValue.dropFirst())) : trimmedValue
        guard let parsed = normalizedPositiveInteger(numericValue) else { return nil }
        let candidate = isOffset ? startSentence + parsed - 1 : parsed
        return max(startSentence, candidate)
    }

    static func normalizedPositiveNumber(_ value: String) -> Double? {
        let trimmedValue = normalizedNormalizationText(value)
        guard !trimmedValue.isEmpty,
              let parsed = Double(trimmedValue),
              parsed.isFinite else {
            return nil
        }
        return max(1, parsed)
    }

    static func normalizedMode(_ value: String, fallback: String) -> String {
        let trimmedValue = normalizedNormalizationText(value)
        guard !trimmedValue.isEmpty else { return fallback }
        return trimmedValue
    }

    static func normalizedAudioBitrate(_ value: String) -> Int? {
        let trimmedValue = normalizedNormalizationText(value)
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

    static func clampAssFontSize(_ value: Int) -> Int {
        bounded(value, to: AppleSubtitleAssTypography.fontSizeRange)
    }

    static func clampAssEmphasisScale(_ value: Double) -> Double {
        bounded(value, to: AppleSubtitleAssTypography.emphasisScaleRange)
    }

    static func clampSubtitleTranslationBatchSize(_ value: Int) -> Int {
        bounded(value, to: AppleSubtitleTuning.translationBatchSizeRange)
    }

    static func clampSubtitleWorkerCount(_ value: Int) -> Int {
        bounded(value, to: AppleSubtitleTuning.workerCountRange)
    }

    static func clampSubtitleBatchSize(_ value: Int) -> Int {
        bounded(value, to: AppleSubtitleTuning.batchSizeRange)
    }

    static func clampYoutubeOriginalMixPercent(_ value: Double) -> Double {
        min(100, max(0, value))
    }

    static func clampYoutubeFlushSentences(_ value: Int) -> Int {
        min(200, max(1, value))
    }

    static func normalizeYoutubeOffset(_ value: String) -> String? {
        let trimmedValue = normalizedNormalizationText(value)
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

    private static func normalizedNormalizationText(_ value: String) -> String {
        value.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private static func bounded<T: Comparable>(_ value: T, to range: ClosedRange<T>) -> T {
        min(range.upperBound, max(range.lowerBound, value))
    }
}
