import Foundation

extension AppleBookCreatePresentation {
    static func downloadStationCompletedFiles(from job: AcquisitionJobStatusResponse?) -> [String] {
        guard let job else {
            return []
        }
        let topLevel = normalizedDownloadStationMetadataStrings(job.completedFiles)
        if !topLevel.isEmpty {
            return topLevel
        }
        let metadata = job.metadata ?? [:]
        for key in ["completed_files", "completed_paths", "files"] {
            let values = normalizedDownloadStationMetadataStrings(metadata[key])
            if !values.isEmpty {
                return values
            }
        }
        return normalizedDownloadStationMetadataStrings(
            metadata["completed_file"] ?? metadata["completed_path"] ?? metadata["local_path"]
        )
    }

    static func downloadStationCompletedCandidate(
        from discovery: AcquisitionDiscoveryResponse?,
        job: AcquisitionJobStatusResponse?
    ) -> AcquisitionCandidate? {
        let completedNames = Set(
            downloadStationCompletedFileHints(from: job).flatMap(downloadStationNameKeys)
        )
        guard !completedNames.isEmpty else {
            return nil
        }
        return discovery?.candidates.first { candidate in
            guard candidate.localPath?.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty == false else {
                return false
            }
            return downloadStationCandidateNameSet(candidate).contains { completedNames.contains($0) }
        }
    }

    static func isDownloadStationHandoffCandidate(_ candidate: AcquisitionCandidate) -> Bool {
        guard candidate.provider == "newznab_torznab" else {
            return false
        }
        if candidate.metadata?["handoff_provider"]?.stringValue?
            .trimmingCharacters(in: .whitespacesAndNewlines)
            .localizedCaseInsensitiveCompare("download_station") == .orderedSame {
            return true
        }
        return candidate.metadata?["has_download_url"]?.stringValue?
            .trimmingCharacters(in: .whitespacesAndNewlines)
            .localizedCaseInsensitiveCompare("true") == .orderedSame
    }

    private static func normalizedDownloadStationMetadataStrings(_ values: [String]) -> [String] {
        values.compactMap { $0.trimmingCharacters(in: .whitespacesAndNewlines).nonEmptyValue }
    }

    private static func normalizedDownloadStationMetadataStrings(_ value: JSONValue?) -> [String] {
        if let array = value?.arrayValue {
            return array.compactMap {
                $0.stringValue?.trimmingCharacters(in: .whitespacesAndNewlines).nonEmptyValue
            }
        }
        return value?.stringValue?
            .trimmingCharacters(in: .whitespacesAndNewlines)
            .nonEmptyValue
            .map { [$0] } ?? []
    }

    private static func downloadStationCompletedFileHints(
        from job: AcquisitionJobStatusResponse?
    ) -> [String] {
        guard let job else {
            return []
        }
        var hints = normalizedDownloadStationMetadataStrings(job.completedFiles)
        let metadata = job.metadata ?? [:]
        for key in ["completed_file", "completed_path", "local_path", "filename"] {
            hints.append(contentsOf: normalizedDownloadStationMetadataStrings(metadata[key]))
        }
        for key in ["completed_files", "completed_paths", "files"] {
            hints.append(contentsOf: normalizedDownloadStationMetadataStrings(metadata[key]))
        }
        return hints
    }

    private static func downloadStationCandidateNameSet(_ candidate: AcquisitionCandidate) -> Set<String> {
        Set(
            [
                candidate.localPath,
                candidate.title.nonEmptyValue,
                candidate.sourceUrl?.nonEmptyValue
            ]
            .compactMap { $0 }
            .flatMap(downloadStationNameKeys)
        )
    }

    private static func downloadStationNameKeys(for value: String) -> [String] {
        let name = downloadStationLastPathComponent(value)
        let trimmed = name.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else {
            return []
        }
        let normalized = trimmed.lowercased()
        let stem = downloadStationFileStem(normalized)
        return stem == normalized ? [normalized] : [normalized, stem]
    }

    private static func downloadStationLastPathComponent(_ value: String) -> String {
        let separators: Set<Character> = ["/", "\\"]
        if let index = value.lastIndex(where: { separators.contains($0) }) {
            return String(value[value.index(after: index)...])
        }
        return value
    }

    private static func downloadStationFileStem(_ filename: String) -> String {
        guard let dot = filename.lastIndex(of: "."),
              dot > filename.startIndex else {
            return filename
        }
        return String(filename[..<dot])
    }
}
