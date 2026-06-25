import Foundation
#if os(iOS)
import UniformTypeIdentifiers
#endif

struct AppleBookCreateImportedFile: Equatable {
    let url: URL
    let fileName: String

    init(url: URL) {
        self.url = url
        self.fileName = url.lastPathComponent
    }
}

struct AppleBookCreateNarrateImportSelection: Equatable {
    let file: AppleBookCreateImportedFile
    let sourcePath: String
    let shouldClearChapterSelection: Bool
    let derivedBaseOutput: String?
}

struct AppleBookCreateSubtitleImportSelection: Equatable {
    let file: AppleBookCreateImportedFile
    let metadataLookupSourceName: String
    let shouldClearMetadata: Bool
}

enum AppleBookCreateFileImport {
    #if os(iOS)
    static var epubContentType: UTType {
        UTType(filenameExtension: "epub") ?? UTType(importedAs: "org.idpf.epub-container")
    }

    static var subtitleContentTypes: [UTType] {
        [
            UTType(filenameExtension: "srt") ?? UTType(importedAs: "com.subrip.srt"),
            UTType(filenameExtension: "vtt") ?? UTType(importedAs: "org.webvtt"),
            UTType.plainText
        ]
    }
    #endif

    static func importedFile(from urls: [URL]) -> AppleBookCreateImportedFile? {
        urls.first.map(AppleBookCreateImportedFile.init(url:))
    }

    static func derivedNarrateBaseOutput(
        file: AppleBookCreateImportedFile,
        currentBaseOutput _: String,
        didEditBaseOutput: Bool
    ) -> String? {
        guard !didEditBaseOutput else {
            return nil
        }
        return AppleBookCreatePresentation.deriveBaseOutputName(
            file.url.deletingPathExtension().lastPathComponent
        )
    }

    static func narrateImportSelection(
        from urls: [URL],
        currentBaseOutput: String,
        didEditBaseOutput: Bool
    ) -> AppleBookCreateNarrateImportSelection? {
        guard let file = importedFile(from: urls) else {
            return nil
        }
        return AppleBookCreateNarrateImportSelection(
            file: file,
            sourcePath: "",
            shouldClearChapterSelection: true,
            derivedBaseOutput: derivedNarrateBaseOutput(
                file: file,
                currentBaseOutput: currentBaseOutput,
                didEditBaseOutput: didEditBaseOutput
            )
        )
    }

    static func subtitleImportSelection(from urls: [URL]) -> AppleBookCreateSubtitleImportSelection? {
        guard let file = importedFile(from: urls) else {
            return nil
        }
        return AppleBookCreateSubtitleImportSelection(
            file: file,
            metadataLookupSourceName: file.fileName,
            shouldClearMetadata: true
        )
    }
}
