import SwiftUI

struct AppleBookCreateSettingsContent<
    JobTypeSection: View,
    TemplateSection: View,
    PromptSection: View,
    MetadataSection: View,
    JobSettingsSection: View,
    NarrationSection: View,
    SubtitleMetadataSection: View,
    YoutubeMetadataSection: View,
    OutputSection: View,
    StatusSection: View,
    SubmitSection: View
>: View {
    let creationMode: AppleCreateMode
    @ViewBuilder let jobTypeSection: () -> JobTypeSection
    @ViewBuilder let templateSection: () -> TemplateSection
    @ViewBuilder let promptSection: () -> PromptSection
    @ViewBuilder let metadataSection: () -> MetadataSection
    @ViewBuilder let jobSettingsSection: () -> JobSettingsSection
    @ViewBuilder let narrationSection: () -> NarrationSection
    @ViewBuilder let subtitleMetadataSection: () -> SubtitleMetadataSection
    @ViewBuilder let youtubeMetadataSection: () -> YoutubeMetadataSection
    @ViewBuilder let outputSection: () -> OutputSection
    @ViewBuilder let statusSection: () -> StatusSection
    @ViewBuilder let submitSection: () -> SubmitSection

    var body: some View {
        jobTypeSection()
        templateSection()
        if creationMode == .generatedBook {
            promptSection()
        }
        if creationMode == .generatedBook || creationMode == .narrateEbook {
            metadataSection()
        }
        jobSettingsSection()
        narrationSection()
        if creationMode == .subtitleJob {
            subtitleMetadataSection()
        }
        if creationMode == .youtubeDub {
            youtubeMetadataSection()
        }
        outputSection()
        statusSection()
        submitSection()
    }
}
