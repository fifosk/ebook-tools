import Foundation

extension InteractivePlayerViewModel {
    func resolveMediaURL(for file: PipelineMediaFile) -> URL? {
        guard let jobId, let mediaResolver else { return nil }
        return mediaResolver.resolveFileURL(jobId: jobId, file: file)
    }

    func resolvePath(_ path: String) -> URL? {
        guard let jobId, let mediaResolver else { return nil }
        return mediaResolver.resolvePath(jobId: jobId, relativePath: path)
    }

    func resolveSentenceImageURL(sentence: InteractiveChunk.Sentence, chunk: InteractiveChunk) -> URL? {
        guard let path = sentenceImagePath(sentence: sentence, chunk: chunk) else { return nil }
        return resolvePath(path)
    }

    func sentenceImagePath(sentence: InteractiveChunk.Sentence, chunk: InteractiveChunk) -> String? {
        if let rawPath = sentence.imagePath, let path = rawPath.nonEmptyValue {
            return path
        }
        guard let rangeFragment = chunk.rangeFragment?.nonEmptyValue else { return nil }
        let sentenceNumber = sentence.displayIndex ?? sentence.id
        guard sentenceNumber > 0 else { return nil }
        let padded = String(format: "%05d", sentenceNumber)
        return "media/images/\(rangeFragment)/sentence_\(padded).png"
    }
}
