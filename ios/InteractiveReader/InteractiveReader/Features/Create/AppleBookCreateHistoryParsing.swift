import Foundation

private enum AppleBookCreateHistoryParsingConstants {
    static let jobDateFormatter: ISO8601DateFormatter = {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime]
        return formatter
    }()

    static let jobDateFormatterWithFractional: ISO8601DateFormatter = {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return formatter
    }()
}

extension AppleBookCreatePresentation {
    static func narrationStartSentence(
        inputFile: String,
        from jobs: [PipelineStatusResponse]
    ) -> Int? {
        let normalizedInput = normalizedNarrationPath(inputFile)
        guard let normalizedInput, !jobs.isEmpty else { return nil }

        var latest: (createdAt: Date, anchor: Int)?
        for job in jobs where isReusableNarrationJob(job) {
            guard let createdAt = parseJobDate(job.createdAt),
                  let candidate = normalizedNarrationPath(
                    narrationString(job, keys: ["input_file", "inputFile", "base_output_file", "baseOutputFile"])
                  ),
                  candidate == normalizedInput
            else {
                continue
            }
            let anchor = narrationInt(job, keys: ["end_sentence", "endSentence"])
                ?? narrationInt(job, keys: ["start_sentence", "startSentence"])
            guard let anchor else { continue }
            if latest == nil || createdAt > latest!.createdAt {
                latest = (createdAt, anchor)
            }
        }

        guard let latest else { return nil }
        return max(1, latest.anchor - 5)
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

    static func historyStringMap(
        in sources: [[String: JSONValue]],
        keys: [String]
    ) -> [String: String]? {
        for source in sources {
            for key in keys {
                guard let object = source[key]?.objectValue else { continue }
                var result = [String: String]()
                for (entryKey, entryValue) in object {
                    let normalizedKey = normalizedHistoryText(entryKey)
                    guard !normalizedKey.isEmpty else { continue }
                    guard let normalizedValue = entryValue.stringValue?.nonEmptyValue else { continue }
                    result[normalizedKey] = normalizedValue
                }
                if !result.isEmpty {
                    return result
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
            let trimmedValue = normalizedHistoryText(string)
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
        let trimmedValue = normalizedHistoryText(value)
        guard !trimmedValue.isEmpty else { return nil }
        return trimmedValue
            .trimmingCharacters(in: CharacterSet(charactersIn: "/\\"))
            .lowercased()
            .nonEmptyValue
    }

    static func parseJobDate(_ value: String) -> Date? {
        AppleBookCreateHistoryParsingConstants.jobDateFormatterWithFractional.date(from: value)
            ?? AppleBookCreateHistoryParsingConstants.jobDateFormatter.date(from: value)
    }

    static func normalizedHistoryText(_ value: String) -> String {
        value.trimmingCharacters(in: .whitespacesAndNewlines)
    }
}
