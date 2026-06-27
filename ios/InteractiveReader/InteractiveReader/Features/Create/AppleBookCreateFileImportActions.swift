import Foundation

extension AppleBookCreateView {
    #if os(iOS)
    func handleNarrateEbookImport(_ result: Result<[URL], Error>) {
        switch result {
        case let .success(urls):
            guard let selection = AppleBookCreateFileImport.narrateImportSelection(
                from: urls,
                currentBaseOutput: sourceBaseOutput,
                didEditBaseOutput: editedFields.contains(.sourceBaseOutput)
            ) else { return }
            selectedNarrateFileURL = selection.file.url
            selectedNarrateFileName = selection.file.fileName
            sourcePath = selection.sourcePath
            if selection.shouldClearChapterSelection {
                clearNarrateChapterSelection()
            }
            clearNarrateSourceMetadata()
            markEdited(.sourcePath)
            if let baseOutput = selection.derivedBaseOutput {
                sourceBaseOutput = baseOutput
            }
            importNarrateEbookToServer(selection)
        case let .failure(error):
            selectedNarrateFileURL = nil
            selectedNarrateFileName = nil
            viewModel.errorMessage = error.localizedDescription
        }
    }

    func handleSubtitleFileImport(_ result: Result<[URL], Error>) {
        switch result {
        case let .success(urls):
            guard let selection = AppleBookCreateFileImport.subtitleImportSelection(from: urls) else { return }
            selectedSubtitleFileURL = selection.file.url
            selectedSubtitleFileName = selection.file.fileName
            subtitleMetadataLookupSourceName = selection.metadataLookupSourceName
            if selection.shouldClearMetadata {
                viewModel.clearSubtitleMetadata()
            }
            markEdited(.subtitleSourcePath)
        case let .failure(error):
            selectedSubtitleFileURL = nil
            selectedSubtitleFileName = nil
            viewModel.errorMessage = error.localizedDescription
        }
    }

    func importNarrateEbookToServer(_ selection: AppleBookCreateNarrateImportSelection) {
        Task {
            guard let uploaded = await viewModel.uploadPipelineEbook(
                fileURL: selection.file.url,
                filename: selection.file.fileName,
                using: appState
            ) else {
                return
            }
            sourcePath = uploaded.path
            selectedNarrateFileURL = nil
            selectedNarrateFileName = uploaded.name
            clearNarrateChapterSelection()
            clearNarrateSourceMetadata()
            markEdited(.sourcePath)
            await refreshPipelineFiles(force: true)
        }
    }
    #else
    func handleNarrateEbookImport(_: Result<[URL], Error>) {}

    func handleSubtitleFileImport(_: Result<[URL], Error>) {}
    #endif
}
