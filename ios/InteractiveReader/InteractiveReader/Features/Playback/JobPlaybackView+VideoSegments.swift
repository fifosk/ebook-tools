import Foundation

extension JobPlaybackView {
    var videoSegments: [JobVideoSegment] {
        guard let mediaResponse = viewModel.mediaResponse else { return [] }
        if !mediaResponse.chunks.isEmpty {
            return buildSegments(from: mediaResponse.chunks, media: mediaResponse.media)
        }
        let media = mediaResponse.media
        let videoFiles = resolveVideoFiles(from: media)
        let subtitleFiles = resolveSubtitleFiles(from: media)
        let sortedVideos = videoFiles.enumerated().sorted { lhs, rhs in
            let left = sortKey(for: lhs.element, fallback: lhs.offset)
            let right = sortKey(for: rhs.element, fallback: rhs.offset)
            if left == right {
                return lhs.offset < rhs.offset
            }
            return left < right
        }
        let sortedSubtitles = subtitleFiles.enumerated().sorted { lhs, rhs in
            let left = sortKey(for: lhs.element, fallback: lhs.offset)
            let right = sortKey(for: rhs.element, fallback: rhs.offset)
            if left == right {
                return lhs.offset < rhs.offset
            }
            return left < right
        }
        return sortedVideos.map { entry in
            let file = entry.element
            let matched = matchSubtitleFiles(for: file, in: subtitleFiles)
            let resolvedSubtitles: [PipelineMediaFile]
            if matched.isEmpty {
                if sortedSubtitles.count == sortedVideos.count {
                    resolvedSubtitles = [sortedSubtitles[entry.offset].element]
                } else {
                    resolvedSubtitles = subtitleFiles
                }
            } else {
                resolvedSubtitles = matched
            }
            return JobVideoSegment(
                id: segmentID(for: file, chunk: nil, fallback: entry.offset),
                videoFile: file,
                subtitleFiles: resolvedSubtitles,
                chunk: nil
            )
        }
    }

    var activeVideoSegment: JobVideoSegment? {
        guard !videoSegments.isEmpty else { return nil }
        if let activeVideoSegmentID,
           let match = videoSegments.first(where: { $0.id == activeVideoSegmentID }) {
            return match
        }
        return videoSegments.first
    }

    var videoURL: URL? {
        guard let segment = activeVideoSegment else { return nil }
        return viewModel.resolveMediaURL(for: segment.videoFile)
    }

    var subtitleTracks: [VideoSubtitleTrack] {
        guard let segment = activeVideoSegment else { return [] }
        return subtitleTracks(from: segment.subtitleFiles)
    }

    var videoSegmentOptions: [VideoSegmentOption] {
        guard !videoSegments.isEmpty else { return [] }
        return videoSegments.enumerated().map { index, segment in
            VideoSegmentOption(
                id: segment.id,
                label: segmentLabel(for: segment, index: index)
            )
        }
    }

    func subtitleTrackLabel(for file: PipelineMediaFile, fallback: String) -> String {
        let raw = (file.name.nonEmptyValue ?? file.relativePath?.nonEmptyValue ?? file.path?.nonEmptyValue)
        let filename = raw?.split(whereSeparator: { $0 == "/" || $0 == "\\" }).last.map(String.init) ?? fallback
        if let dotIndex = filename.lastIndex(of: ".") {
            let stem = filename[..<dotIndex]
            if !stem.isEmpty {
                return String(stem)
            }
        }
        return filename
    }

    func resolveSubtitleFiles(from media: [String: [PipelineMediaFile]]) -> [PipelineMediaFile] {
        var files: [PipelineMediaFile] = []
        let keys = ["text", "subtitle", "subtitles", "captions"]
        for key in keys {
            files.append(contentsOf: media[key] ?? [])
        }
        if let chunks = viewModel.mediaResponse?.chunks {
            for chunk in chunks {
                files.append(contentsOf: chunk.files.filter { isSubtitleFile($0) })
            }
        }
        return uniqueFiles(files)
    }

    func resolveVideoFiles(from media: [String: [PipelineMediaFile]]) -> [PipelineMediaFile] {
        var files = media["video"] ?? []
        if let chunks = viewModel.mediaResponse?.chunks {
            for chunk in chunks {
                files.append(contentsOf: chunk.files.filter { isVideoFile($0) })
            }
        }
        return uniqueFiles(files)
    }

    func uniqueFiles(_ files: [PipelineMediaFile]) -> [PipelineMediaFile] {
        var seen = Set<String>()
        var deduped: [PipelineMediaFile] = []
        for file in files {
            let signature = fileSignature(file)
            guard !seen.contains(signature) else { continue }
            seen.insert(signature)
            deduped.append(file)
        }
        return deduped
    }

    func fileSignature(_ file: PipelineMediaFile) -> String {
        if let path = file.path?.nonEmptyValue {
            return path
        }
        if let relative = file.relativePath?.nonEmptyValue {
            return relative
        }
        if let url = file.url?.nonEmptyValue {
            return url
        }
        return file.name
    }

    func subtitleTracks(from files: [PipelineMediaFile]) -> [VideoSubtitleTrack] {
        var tracks: [VideoSubtitleTrack] = []
        var seen: Set<String> = []
        for file in files {
            guard let url = viewModel.resolveMediaURL(for: file) else { continue }
            let sourcePath = file.relativePath ?? file.path ?? file.name
            let format = SubtitleParser.format(for: sourcePath)
            let id = subtitleTrackIdentifier(for: file, url: url, sourcePath: sourcePath)
            guard !seen.contains(id) else { continue }
            seen.insert(id)
            let label = subtitleTrackLabel(for: file, fallback: "Subtitle \(tracks.count + 1)")
            tracks.append(VideoSubtitleTrack(id: id, url: url, format: format, label: label))
        }
        return tracks
    }

    func subtitleTrackIdentifier(for file: PipelineMediaFile, url: URL, sourcePath: String) -> String {
        let base = subtitleTrackBase(for: file, url: url, sourcePath: sourcePath)
        var suffixes: [String] = []
        if let chunkID = file.chunkID?.nonEmptyValue {
            suffixes.append("chunk=\(chunkID)")
        }
        if let range = file.rangeFragment?.nonEmptyValue {
            suffixes.append("range=\(range)")
        }
        if let start = file.startSentence {
            if let end = file.endSentence {
                suffixes.append("sent=\(start)-\(end)")
            } else {
                suffixes.append("sent=\(start)")
            }
        }
        if suffixes.isEmpty, let key = segmentKey(for: file) {
            suffixes.append("key=\(key)")
        }
        guard !suffixes.isEmpty else { return base }
        return "\(base)#\(suffixes.joined(separator: "|"))"
    }

    func subtitleTrackBase(for file: PipelineMediaFile, url: URL, sourcePath: String) -> String {
        var base = sourcePath.nonEmptyValue ?? url.absoluteString
        let hasPathSeparator = base.contains("/") || base.contains("\\")
        if !hasPathSeparator, let urlValue = file.url?.nonEmptyValue {
            base = "\(base)#url=\(urlValue)"
        }
        return base
    }

    func matchSubtitleFiles(for video: PipelineMediaFile, in subtitleFiles: [PipelineMediaFile]) -> [PipelineMediaFile] {
        if let chunkID = video.chunkID?.nonEmptyValue {
            let matches = subtitleFiles.filter { $0.chunkID == chunkID }
            if !matches.isEmpty { return matches }
        }
        if let range = video.rangeFragment?.nonEmptyValue {
            let matches = subtitleFiles.filter { $0.rangeFragment == range }
            if !matches.isEmpty { return matches }
        }
        if let start = video.startSentence, let end = video.endSentence {
            let matches = subtitleFiles.filter { file in
                guard let fileStart = file.startSentence, let fileEnd = file.endSentence else { return false }
                return fileStart <= end && fileEnd >= start
            }
            if !matches.isEmpty { return matches }
        }
        if let key = segmentKey(for: video) {
            let matches = subtitleFiles.filter { segmentKey(for: $0) == key }
            if !matches.isEmpty { return matches }
        }
        if let directoryName = fileDirectoryName(for: video) {
            let matches = subtitleFiles.filter { fileDirectoryName(for: $0) == directoryName }
            if !matches.isEmpty { return matches }
        }
        if let stem = fileStem(for: video) {
            let exactMatches = subtitleFiles.filter { fileStem(for: $0) == stem }
            if !exactMatches.isEmpty { return exactMatches }
            let fuzzyMatches = subtitleFiles.filter { file in
                guard let subtitleStem = fileStem(for: file) else { return false }
                return subtitleStem.contains(stem) || stem.contains(subtitleStem)
            }
            if !fuzzyMatches.isEmpty { return fuzzyMatches }
        }
        return []
    }

    func sortKey(for file: PipelineMediaFile, fallback: Int) -> Int {
        if let start = file.startSentence {
            return start
        }
        if let chunkID = file.chunkID, let numeric = Int(chunkID.filter(\.isNumber)) {
            return numeric
        }
        if let stem = fileStem(for: file) {
            let digits = stem.filter(\.isNumber)
            if let numeric = Int(digits), !digits.isEmpty {
                return numeric
            }
        }
        return fallback
    }

    func segmentID(for file: PipelineMediaFile, chunk: PipelineMediaChunk?, fallback: Int) -> String {
        file.chunkID
            ?? chunk?.chunkID
            ?? file.rangeFragment
            ?? chunk?.rangeFragment
            ?? file.name.nonEmptyValue
            ?? "video-\(fallback)"
    }

    func buildSegments(from chunks: [PipelineMediaChunk], media: [String: [PipelineMediaFile]]) -> [JobVideoSegment] {
        let subtitleFiles = resolveSubtitleFiles(from: media)
        let sortedChunks = chunks.enumerated().sorted { lhs, rhs in
            let left = chunkSortKey(for: lhs.element, fallback: lhs.offset)
            let right = chunkSortKey(for: rhs.element, fallback: rhs.offset)
            if left == right {
                return lhs.offset < rhs.offset
            }
            return left < right
        }
        let sortedSubtitles = subtitleFiles.enumerated().sorted { lhs, rhs in
            let left = sortKey(for: lhs.element, fallback: lhs.offset)
            let right = sortKey(for: rhs.element, fallback: rhs.offset)
            if left == right {
                return lhs.offset < rhs.offset
            }
            return left < right
        }
        var segments: [JobVideoSegment] = []
        for (chunkIndex, chunkEntry) in sortedChunks.enumerated() {
            let chunk = chunkEntry.element
            let chunkVideoFiles = chunk.files.filter { isVideoFile($0) }
            guard !chunkVideoFiles.isEmpty else { continue }
            let chunkSubtitleFiles = chunk.files.filter { isSubtitleFile($0) }
            let chunkMatches = matchSubtitleFiles(for: chunk, in: subtitleFiles)
            let sortedVideos = chunkVideoFiles.enumerated().sorted { lhs, rhs in
                let left = sortKey(for: lhs.element, fallback: lhs.offset)
                let right = sortKey(for: rhs.element, fallback: rhs.offset)
                if left == right {
                    return lhs.offset < rhs.offset
                }
                return left < right
            }
            for (videoOffset, videoEntry) in sortedVideos.enumerated() {
                let videoFile = videoEntry.element
                let matched = matchSubtitleFiles(for: videoFile, in: subtitleFiles)
                let resolvedSubtitles: [PipelineMediaFile]
                if !chunkSubtitleFiles.isEmpty {
                    resolvedSubtitles = chunkSubtitleFiles
                } else if !chunkMatches.isEmpty {
                    resolvedSubtitles = chunkMatches
                } else if !matched.isEmpty {
                    resolvedSubtitles = matched
                } else if sortedSubtitles.count == sortedChunks.count,
                          sortedSubtitles.indices.contains(chunkIndex) {
                    resolvedSubtitles = [sortedSubtitles[chunkIndex].element]
                } else {
                    resolvedSubtitles = []
                }
                let fallback = chunkIndex * 100 + videoOffset
                segments.append(
                    JobVideoSegment(
                        id: segmentID(for: videoFile, chunk: chunk, fallback: fallback),
                        videoFile: videoFile,
                        subtitleFiles: resolvedSubtitles,
                        chunk: chunk
                    )
                )
            }
        }
        return segments
    }

    func matchSubtitleFiles(for chunk: PipelineMediaChunk, in subtitleFiles: [PipelineMediaFile]) -> [PipelineMediaFile] {
        if let chunkID = chunk.chunkID?.nonEmptyValue {
            let matches = subtitleFiles.filter { $0.chunkID == chunkID }
            if !matches.isEmpty { return matches }
        }
        if let range = chunk.rangeFragment?.nonEmptyValue {
            let matches = subtitleFiles.filter { $0.rangeFragment == range }
            if !matches.isEmpty { return matches }
        }
        if let start = chunk.startSentence, let end = chunk.endSentence {
            let matches = subtitleFiles.filter { file in
                guard let fileStart = file.startSentence, let fileEnd = file.endSentence else { return false }
                return fileStart <= end && fileEnd >= start
            }
            if !matches.isEmpty { return matches }
        }
        return []
    }

    func chunkSortKey(for chunk: PipelineMediaChunk, fallback: Int) -> Int {
        if let start = chunk.startSentence {
            return start
        }
        if let chunkID = chunk.chunkID, let numeric = Int(chunkID.filter(\.isNumber)) {
            return numeric
        }
        if let range = chunk.rangeFragment?.nonEmptyValue {
            let digits = range.filter(\.isNumber)
            if let numeric = Int(digits), !digits.isEmpty {
                return numeric
            }
        }
        return fallback
    }

    func isVideoFile(_ file: PipelineMediaFile) -> Bool {
        let type = file.type?.lowercased() ?? ""
        if type.contains("video") { return true }
        if ["mp4", "m4v", "mov", "mkv", "webm"].contains(type) { return true }
        let path = (file.relativePath ?? file.path ?? file.name).lowercased()
        if let ext = path.split(separator: ".").last {
            return ["mp4", "m4v", "mov", "mkv", "webm"].contains(String(ext))
        }
        return false
    }

    func isSubtitleFile(_ file: PipelineMediaFile) -> Bool {
        let type = file.type?.lowercased() ?? ""
        if type.contains("subtitle")
            || type.contains("caption")
            || type == "text"
            || type == "subtitles"
            || type == "captions"
            || type == "ass"
            || type == "vtt"
            || type == "srt"
        {
            return true
        }
        let path = file.relativePath ?? file.path ?? file.name
        let format = SubtitleParser.format(for: path)
        return format != .unknown
    }

    func segmentKey(for file: PipelineMediaFile) -> String? {
        if let chunkID = file.chunkID?.nonEmptyValue {
            return "chunk:\(chunkID)"
        }
        if let range = file.rangeFragment?.nonEmptyValue {
            return "range:\(range)"
        }
        if let directory = fileDirectoryPath(for: file) {
            return "dir:\(directory)"
        }
        if let stem = fileStem(for: file) {
            return "stem:\(stem)"
        }
        return nil
    }

    func fileStem(for file: PipelineMediaFile) -> String? {
        let raw = file.relativePath ?? file.path ?? file.name
        let filename = raw.split(whereSeparator: { $0 == "/" || $0 == "\\" }).last.map(String.init) ?? raw
        if let dotIndex = filename.lastIndex(of: ".") {
            let stem = filename[..<dotIndex]
            return stem.isEmpty ? nil : String(stem)
        }
        return filename.nonEmptyValue
    }

    func fileDirectoryPath(for file: PipelineMediaFile) -> String? {
        let raw = file.relativePath ?? file.path ?? file.name
        let parts = raw.split(whereSeparator: { $0 == "/" || $0 == "\\" })
        guard parts.count > 1 else { return nil }
        return parts.dropLast().joined(separator: "/").nonEmptyValue
    }

    func fileDirectoryName(for file: PipelineMediaFile) -> String? {
        guard let directory = fileDirectoryPath(for: file) else { return nil }
        let parts = directory.split(whereSeparator: { $0 == "/" || $0 == "\\" })
        return parts.last.map(String.init)
    }
}
