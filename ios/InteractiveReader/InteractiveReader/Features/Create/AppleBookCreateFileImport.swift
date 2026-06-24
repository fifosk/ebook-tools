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

    static func importedFile(from urls: [URL]) -> AppleBookCreateImportedFile? {
        urls.first.map(AppleBookCreateImportedFile.init(url:))
    }
    #endif

    static func derivedNarrateBaseOutput(
        file: AppleBookCreateImportedFile,
        currentBaseOutput: String,
        didEditBaseOutput: Bool
    ) -> String? {
        guard
            currentBaseOutput.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty,
            !didEditBaseOutput
        else {
            return nil
        }
        return AppleBookCreatePresentation.deriveBaseOutputName(
            file.url.deletingPathExtension().lastPathComponent
        )
    }
}
