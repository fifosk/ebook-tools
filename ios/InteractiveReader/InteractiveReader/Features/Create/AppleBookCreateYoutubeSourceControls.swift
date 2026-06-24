import Foundation
import SwiftUI

struct AppleBookCreateYoutubeSourceControls: View {
    @Binding var youtubeBaseDir: String
    @Binding var youtubeVideoPath: String
    @Binding var youtubeSubtitlePath: String
    @Binding var youtubeSubtitleExtractionLanguages: String
    let youtubeLibrary: YoutubeNasLibraryResponse?
    let youtubeInlineSubtitleStreams: [YoutubeInlineSubtitleStream]
    let isLoadingYoutubeLibrary: Bool
    let isLoadingYoutubeSubtitleStreams: Bool
    let isExtractingYoutubeSubtitles: Bool
    let youtubeLibraryErrorMessage: String?
    let youtubeSubtitleExtractionMessage: String?
    let youtubeSubtitleExtractionErrorMessage: String?
    let onRefreshYoutubeLibrary: () -> Void
    let onInspectYoutubeSubtitles: () -> Void
    let onExtractYoutubeSubtitles: () -> Void

    var body: some View {
        TextField("NAS directory", text: $youtubeBaseDir)
            .textInputAutocapitalization(.never)
            .autocorrectionDisabled()
            .accessibilityIdentifier("createYoutubeBaseDirField")
        if let baseDir = youtubeLibrary?.baseDir,
           !baseDir.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            Text("Base path: \(baseDir)")
                .font(.footnote)
                .foregroundStyle(.secondary)
                .accessibilityIdentifier("createYoutubeBaseDirLabel")
        }
        if !youtubeVideos.isEmpty {
            Picker("NAS video", selection: $youtubeVideoPath) {
                Text("Manual path").tag("")
                if shouldShowCurrentYoutubeVideoPath {
                    Text(youtubeVideoPath).tag(youtubeVideoPath)
                }
                ForEach(youtubeVideos, id: \.path) { video in
                    Text(youtubeVideoLabel(video)).tag(video.path)
                }
            }
            .accessibilityIdentifier("createYoutubeNasVideoPicker")
            .onChange(of: youtubeVideoPath) { _, newValue in
                applyYoutubeVideoSelection(newValue)
            }
        }
        HStack {
            Button(action: onRefreshYoutubeLibrary) {
                Label(
                    isLoadingYoutubeLibrary ? "Refreshing Videos" : "Refresh Videos",
                    systemImage: "arrow.clockwise"
                )
            }
            .disabled(isLoadingYoutubeLibrary)
            .accessibilityIdentifier("createYoutubeRefreshNasVideosButton")

            if isLoadingYoutubeLibrary {
                ProgressView()
                    .accessibilityIdentifier("createYoutubeNasVideosProgress")
            }
        }
        if let youtubeLibraryErrorMessage {
            Text(youtubeLibraryErrorMessage)
                .font(.footnote)
                .foregroundStyle(.secondary)
                .accessibilityIdentifier("createYoutubeNasVideosMessage")
        }
        TextField("Video path", text: $youtubeVideoPath)
            .textInputAutocapitalization(.never)
            .autocorrectionDisabled()
            .accessibilityIdentifier("createYoutubeVideoPathField")
        embeddedYoutubeSubtitleControls
        if !youtubeSubtitleEntries.isEmpty {
            Picker("Subtitle", selection: $youtubeSubtitlePath) {
                Text("Manual path").tag("")
                if shouldShowCurrentYoutubeSubtitlePath {
                    Text(youtubeSubtitlePath).tag(youtubeSubtitlePath)
                }
                ForEach(youtubeSubtitleEntries, id: \.path) { subtitle in
                    Text(youtubeSubtitleLabel(subtitle)).tag(subtitle.path)
                }
            }
            .accessibilityIdentifier("createYoutubeNasSubtitlePicker")
        }
        TextField("Subtitle path", text: $youtubeSubtitlePath)
            .textInputAutocapitalization(.never)
            .autocorrectionDisabled()
            .accessibilityIdentifier("createYoutubeSubtitlePathField")
    }

    @ViewBuilder
    private var embeddedYoutubeSubtitleControls: some View {
        HStack {
            Button(action: onInspectYoutubeSubtitles) {
                Label(
                    isLoadingYoutubeSubtitleStreams ? "Inspecting Embedded Subtitles" : "Inspect Embedded Subtitles",
                    systemImage: "magnifyingglass"
                )
            }
            .disabled(!hasYoutubeVideoPath || isLoadingYoutubeSubtitleStreams || isExtractingYoutubeSubtitles)
            .accessibilityIdentifier("createYoutubeInspectEmbeddedSubtitlesButton")

            if isLoadingYoutubeSubtitleStreams {
                ProgressView()
                    .accessibilityIdentifier("createYoutubeEmbeddedSubtitlesProgress")
            }
        }

        if !youtubeInlineSubtitleStreams.isEmpty {
            ForEach(youtubeInlineSubtitleStreams) { stream in
                Label(
                    AppleBookCreatePresentation.youtubeInlineSubtitleStreamLabel(stream),
                    systemImage: stream.canExtract ? "captions.bubble" : "photo"
                )
                .font(.footnote)
                .foregroundStyle(.secondary)
                .accessibilityIdentifier("createYoutubeEmbeddedSubtitleStream.\(stream.index)")
            }

            TextField("Languages to extract", text: $youtubeSubtitleExtractionLanguages)
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()
                .accessibilityIdentifier("createYoutubeEmbeddedSubtitleLanguagesField")
        }

        HStack {
            Button(action: onExtractYoutubeSubtitles) {
                Label(
                    isExtractingYoutubeSubtitles ? "Extracting Subtitles" : "Extract Embedded Subtitles",
                    systemImage: "square.and.arrow.down"
                )
            }
            .disabled(!hasYoutubeVideoPath || isLoadingYoutubeSubtitleStreams || isExtractingYoutubeSubtitles)
            .accessibilityIdentifier("createYoutubeExtractEmbeddedSubtitlesButton")

            if isExtractingYoutubeSubtitles {
                ProgressView()
                    .accessibilityIdentifier("createYoutubeExtractEmbeddedSubtitlesProgress")
            }
        }

        if let youtubeSubtitleExtractionMessage {
            Text(youtubeSubtitleExtractionMessage)
                .font(.footnote)
                .foregroundStyle(.secondary)
                .accessibilityIdentifier("createYoutubeEmbeddedSubtitlesMessage")
        }
        if let youtubeSubtitleExtractionErrorMessage {
            Text(youtubeSubtitleExtractionErrorMessage)
                .font(.footnote)
                .foregroundStyle(.secondary)
                .accessibilityIdentifier("createYoutubeEmbeddedSubtitlesError")
        }
    }

    private var youtubeVideos: [YoutubeNasVideoEntry] {
        youtubeLibrary?.videos ?? []
    }

    private var selectedYoutubeVideo: YoutubeNasVideoEntry? {
        youtubeVideos.first { $0.path == youtubeVideoPath }
    }

    private var hasYoutubeVideoPath: Bool {
        !youtubeVideoPath.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
    }

    private var youtubeSubtitleEntries: [YoutubeNasSubtitleEntry] {
        AppleBookCreatePresentation.playableYoutubeSubtitles(for: selectedYoutubeVideo)
    }

    private var shouldShowCurrentYoutubeVideoPath: Bool {
        let trimmedPath = youtubeVideoPath.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmedPath.isEmpty else {
            return false
        }
        return !youtubeVideos.contains { $0.path == youtubeVideoPath }
    }

    private var shouldShowCurrentYoutubeSubtitlePath: Bool {
        let trimmedPath = youtubeSubtitlePath.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmedPath.isEmpty else {
            return false
        }
        return !youtubeSubtitleEntries.contains { $0.path == youtubeSubtitlePath }
    }

    private func youtubeVideoLabel(_ video: YoutubeNasVideoEntry) -> String {
        let subtitleCount = AppleBookCreatePresentation.playableYoutubeSubtitles(for: video).count
        let label = subtitleCount == 1 ? "1 subtitle" : "\(subtitleCount) subtitles"
        return "\(video.filename) · \(label)"
    }

    private func youtubeSubtitleLabel(_ subtitle: YoutubeNasSubtitleEntry) -> String {
        let language = subtitle.language?.trimmingCharacters(in: .whitespacesAndNewlines)
        let suffix = [subtitle.format.uppercased(), language]
            .compactMap { value -> String? in
                guard let value, !value.isEmpty else { return nil }
                return value
            }
            .joined(separator: " · ")
        return suffix.isEmpty ? subtitle.filename : "\(subtitle.filename) · \(suffix)"
    }

    private func applyYoutubeVideoSelection(_ videoPath: String) {
        guard let video = youtubeVideos.first(where: { $0.path == videoPath }) else {
            return
        }
        let candidates = AppleBookCreatePresentation.playableYoutubeSubtitles(for: video)
        if candidates.contains(where: { $0.path == youtubeSubtitlePath }) {
            return
        }
        youtubeSubtitlePath = AppleBookCreatePresentation.preferredYoutubeSubtitle(for: video)?.path ?? ""
    }
}
