import SwiftUI

struct AppleBookCreateStatusSection: View {
    let isLoadingOptions: Bool
    let optionsErrorMessage: String?
    let errorMessage: String?
    let intakeStatus: PipelineIntakeStatusResponse?
    let isLoadingIntakeStatus: Bool
    let submittedJobId: String?
    let onRetryDefaults: () -> Void
    let onOpenJobs: (String) -> Void

    var body: some View {
        if isLoadingOptions {
            Section {
                Label("Loading backend creation defaults", systemImage: "arrow.triangle.2.circlepath")
                    .foregroundStyle(.secondary)
                    .accessibilityIdentifier("createBookOptionsLoadingLabel")
            }
        } else if let optionsErrorMessage {
            Section {
                Label("Using built-in defaults", systemImage: "exclamationmark.arrow.triangle.2.circlepath")
                    .foregroundStyle(.secondary)
                    .accessibilityIdentifier("createBookOptionsFallbackLabel")
                Text(optionsErrorMessage)
                    .font(.footnote)
                    .foregroundStyle(.secondary)
                    .accessibilityIdentifier("createBookOptionsErrorLabel")
                Button(action: onRetryDefaults) {
                    Label("Retry Defaults", systemImage: "arrow.clockwise")
                }
                .accessibilityIdentifier("createBookOptionsRetryButton")
            }
        }

        if let errorMessage {
            Section {
                Label(errorMessage, systemImage: "exclamationmark.triangle.fill")
                    .foregroundStyle(.red)
                    .accessibilityIdentifier("createBookErrorLabel")
            }
        }

        if let intakeStatus {
            Section {
                let presentation = AppleBookCreatePresentation.intakeStatusPresentation(for: intakeStatus)
                Label(presentation.label, systemImage: intakeStatusSystemImage(for: intakeStatus))
                    .foregroundStyle(intakeStatusForegroundStyle(for: intakeStatus))
                    .accessibilityIdentifier("createBookIntakeStatusLabel")
                ForEach(presentation.detailLines, id: \.self) { detailLine in
                    Text(detailLine)
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                }
            }
        } else if isLoadingIntakeStatus {
            Section {
                Label("Checking job intake...", systemImage: "clock.arrow.circlepath")
                    .foregroundStyle(.secondary)
                    .accessibilityIdentifier("createBookIntakeStatusLoadingLabel")
            }
        }

        if let submittedJobId {
            Section {
                Label("Job \(submittedJobId)", systemImage: "checkmark.circle.fill")
                    .foregroundStyle(.green)
                    .accessibilityIdentifier("createBookSubmittedJobLabel")
                Button {
                    onOpenJobs(submittedJobId)
                } label: {
                    Label("Open Jobs", systemImage: "tray.full")
                }
                .accessibilityIdentifier("createBookOpenJobsButton")
            }
        }
    }

    private func intakeStatusSystemImage(for status: PipelineIntakeStatusResponse) -> String {
        if !status.acceptingJobs {
            return "pause.circle.fill"
        }
        if status.isUnderPressure {
            return "clock.badge.exclamationmark"
        }
        return "checkmark.circle.fill"
    }

    private func intakeStatusForegroundStyle(for status: PipelineIntakeStatusResponse) -> Color {
        if !status.acceptingJobs {
            return .red
        }
        if status.isUnderPressure {
            return .orange
        }
        return .green
    }
}

struct AppleBookCreateSubmitSection: View {
    let creationMode: AppleCreateMode
    let isSubmitting: Bool
    let canSubmit: Bool
    let isIntakeAtCapacity: Bool
    let webCreateHandoffURL: URL?
    let onSubmit: () -> Void
    let onOpenWebCreate: (URL) -> Void

    var body: some View {
        Section {
            Button(action: onSubmit) {
                let presentation = AppleBookCreatePresentation.submitButtonPresentation(
                    for: creationMode,
                    isSubmitting: isSubmitting
                )
                Label(presentation.title, systemImage: presentation.systemImage)
            }
            .disabled(!canSubmit || isSubmitting || isIntakeAtCapacity)
            .accessibilityIdentifier("createBookSubmitButton")
            #if !os(tvOS)
            if let webCreateHandoffURL {
                Button {
                    onOpenWebCreate(webCreateHandoffURL)
                } label: {
                    Label("Open Web Create", systemImage: "safari")
                }
                .accessibilityIdentifier("createBookOpenWebCreateButton")
            }
            #endif
        }
    }
}
