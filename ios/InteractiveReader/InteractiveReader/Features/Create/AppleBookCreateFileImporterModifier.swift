import SwiftUI

struct AppleBookCreateFileImporterModifier: ViewModifier {
    @Binding var isImportingNarrateEbook: Bool
    @Binding var isImportingSubtitleFile: Bool

    let onNarrateImport: (Result<[URL], Error>) -> Void
    let onSubtitleImport: (Result<[URL], Error>) -> Void

    func body(content: Content) -> some View {
        #if os(iOS)
        content
            .fileImporter(
                isPresented: $isImportingNarrateEbook,
                allowedContentTypes: [AppleBookCreateFileImport.epubContentType],
                allowsMultipleSelection: false,
                onCompletion: onNarrateImport
            )
            .fileImporter(
                isPresented: $isImportingSubtitleFile,
                allowedContentTypes: AppleBookCreateFileImport.subtitleContentTypes,
                allowsMultipleSelection: false,
                onCompletion: onSubtitleImport
            )
        #else
        content
        #endif
    }
}
