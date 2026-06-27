import SwiftUI

extension AppleBookCreateView {
    var canSubmit: Bool {
        AppleBookCreatePresentation.canSubmit(submitState)
    }

    var isIntakeAtCapacity: Bool {
        viewModel.intakeStatus?.acceptingJobs == false
    }

    var submitState: AppleCreateSubmitState {
        AppleCreateSubmitState(
            hasConfiguration: appState.configuration != nil,
            mode: creationMode,
            topic: topic,
            bookName: bookName,
            genre: genre,
            hasNarrateLocalFile: selectedNarrateFileURL != nil,
            sourcePath: sourcePath,
            sourceBaseOutput: sourceBaseOutput,
            hasSubtitleLocalFile: selectedSubtitleFileURL != nil,
            subtitleSourcePath: subtitleSourcePath,
            youtubeVideoPath: youtubeVideoPath,
            youtubeSubtitlePath: youtubeSubtitlePath
        )
    }

    var availableCreateModes: [AppleCreateMode] {
        AppleBookCreatePresentation.availableCreateModes(isTV: Self.isTVPlatform)
    }

    var compatibleCreationTemplates: [CreationTemplateEntry] {
        AppleBookCreateTemplateSettings.compatibleTemplates(
            from: viewModel.creationTemplates,
            for: creationMode
        )
    }

    var sentenceSplitterOptions: [AppleBookSentenceSplitterOption] {
        AppleBookSentenceSplitterOption.options(
            from: viewModel.creationOptions?.sentenceSplitterCapabilities,
            selectedMode: bookSentenceSplitterMode
        )
    }

    var selectedCompatibleTemplateIDBinding: Binding<String> {
        Binding(
            get: {
                AppleBookCreateTemplateSettings.selectedTemplatePickerValue(
                    selectedTemplateID,
                    from: viewModel.creationTemplates,
                    for: creationMode
                )
            },
            set: { selectedTemplateID = $0 }
        )
    }

    var webCreateHandoffURL: URL? {
        AppleBookCreatePresentation.webCreateHandoffURL(
            apiBaseURL: appState.apiBaseURL,
            mode: creationMode,
            templateID: webCreateHandoffTemplateID
        )
    }

    var webCreateHandoffTemplateID: String? {
        AppleBookCreateTemplateSettings.selectedCompatibleTemplateID(
            selectedTemplateID,
            from: viewModel.creationTemplates,
            for: creationMode
        )
    }

    var derivedBaseOutput: String {
        AppleBookCreatePresentation.derivedBaseOutput(
            for: creationMode,
            topic: topic,
            bookName: bookName,
            sourceBaseOutput: sourceBaseOutput,
            subtitleSourcePath: subtitleSourcePath,
            youtubeVideoPath: youtubeVideoPath
        )
    }

    var youtubeMetadataTvSourceName: String {
        AppleBookCreateMetadataSources.youtubeTvSourceName(
            subtitlePath: youtubeSubtitlePath,
            videoPath: youtubeVideoPath
        )
    }

    var youtubeMetadataVideoSourceName: String {
        AppleBookCreateMetadataSources.youtubeVideoSourceName(videoPath: youtubeVideoPath)
    }

    var videoDiscoveryAvailability: AppleBookCreateVideoDiscoveryAvailability {
        AppleBookCreatePresentation.youtubeVideoDiscoveryAvailability(
            providers: viewModel.acquisitionProviders
        )
    }

    var subtitleMetadataSourceName: String {
        AppleBookCreateMetadataSources.subtitleSourceName(
            selectedFileName: selectedSubtitleFileName,
            selectedPath: subtitleSourcePath,
            sources: viewModel.subtitleSources?.sources ?? []
        )
    }

    static var isTVPlatform: Bool {
        #if os(tvOS)
        return true
        #else
        return false
        #endif
    }
}
