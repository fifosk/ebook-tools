import Foundation
import SwiftUI

struct AppleBookCreateTemplateSection: View {
    let templates: [CreationTemplateEntry]
    @Binding var selectedTemplateID: String
    let isLoading: Bool
    let isSaving: Bool
    let isDeleting: Bool
    let errorMessage: String?
    let message: String?
    let onRefresh: () -> Void
    let onSave: () -> Void
    let onApply: () -> Void
    let onDelete: () -> Void

    var body: some View {
        Section("Saved Templates") {
            Button(action: onSave) {
                Label(isSaving ? "Saving Template" : "Save Template", systemImage: "square.and.arrow.down")
            }
            .disabled(isSaving || isLoading || isDeleting)
            .accessibilityIdentifier("createBookSaveTemplateButton")

            if templates.isEmpty {
                Label(emptyLabel, systemImage: "doc.badge.plus")
                    .foregroundStyle(.secondary)
                    .accessibilityIdentifier("createBookTemplateStatusLabel")
            } else {
                Picker("Template", selection: $selectedTemplateID) {
                    Text("Choose template").tag("")
                    ForEach(templates) { template in
                        Text(template.displayName).tag(template.id)
                    }
                }
                .accessibilityIdentifier("createBookTemplatePicker")

                if let selectedTemplate {
                    AppleBookCreateTemplateDetailView(template: selectedTemplate)
                        .accessibilityIdentifier("createBookTemplateDetailSummary")
                }

                Button(action: onApply) {
                    Label("Apply Template", systemImage: "arrow.down.doc")
                }
                .disabled(selectedTemplateID.isEmpty)
                .accessibilityIdentifier("createBookApplyTemplateButton")

                Button(role: .destructive, action: onDelete) {
                    Label(isDeleting ? "Deleting Template" : "Delete Template", systemImage: "trash")
                }
                .disabled(selectedTemplateID.isEmpty || isDeleting)
                .accessibilityIdentifier("createBookDeleteTemplateButton")
            }

            Button(action: onRefresh) {
                Label(isLoading ? "Refreshing Templates" : "Refresh Templates", systemImage: "arrow.clockwise")
            }
            .disabled(isLoading || isSaving || isDeleting)
            .accessibilityIdentifier("createBookRefreshTemplatesButton")

            if let message {
                Label(message, systemImage: "checkmark.circle.fill")
                    .foregroundStyle(.green)
                    .accessibilityIdentifier("createBookTemplateStatusLabel")
            }

            if let errorMessage {
                Label(errorMessage, systemImage: "exclamationmark.triangle.fill")
                    .foregroundStyle(.orange)
                    .accessibilityIdentifier("createBookTemplateErrorLabel")
            }
        }
    }

    private var emptyLabel: String {
        isLoading ? "Loading saved templates..." : "No saved templates for this job type"
    }

    private var selectedTemplate: CreationTemplateEntry? {
        let selectedID = selectedTemplateID.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !selectedID.isEmpty else {
            return nil
        }
        return templates.first { $0.id == selectedID }
    }
}

private struct AppleBookCreateTemplateDetailView: View {
    let template: CreationTemplateEntry

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Label("Template Details", systemImage: "doc.text.magnifyingglass")
                .font(.footnote.weight(.semibold))
            ForEach(detailLines, id: \.self) { line in
                Text(line)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .lineLimit(2)
            }
        }
        .padding(.vertical, 4)
    }

    private var detailLines: [String] {
        [
            "Type: \(templateTypeLabel)",
            "Updated: \(Self.updatedDateLabel(for: template.updatedAt))",
            "Saved fields: \(formState.count)",
            discoverySourceLine,
        ].compactMap { $0 }
    }

    private var templateTypeLabel: String {
        AppleBookCreateTemplateSettings.mode(for: template)?.label
            ?? template.normalizedMode
    }

    private var formState: [String: JSONValue] {
        AppleBookCreateTemplateSettings.formState(from: template) ?? [:]
    }

    private var discoveryState: [String: JSONValue] {
        AppleBookCreateTemplateSettings.discoveryState(from: template) ?? [:]
    }

    private var discoverySourceLine: String? {
        guard !discoveryState.isEmpty else {
            return nil
        }
        return "Discovery source: \(Self.discoverySourceLabel(from: discoveryState))"
    }

    private static func discoverySourceLabel(from state: [String: JSONValue]) -> String {
        let provider = firstString(
            in: state,
            keys: ["selected_provider", "source_provider", "acquisition_provider", "provider"]
        )
        let sourceKind = firstString(in: state, keys: ["source_kind", "kind"])
        switch (provider, sourceKind) {
        case let (.some(provider), .some(sourceKind)) where provider != sourceKind:
            return "\(displayLabel(provider)) / \(displayLabel(sourceKind))"
        case let (.some(provider), _):
            return displayLabel(provider)
        case let (_, .some(sourceKind)):
            return displayLabel(sourceKind)
        default:
            return "saved"
        }
    }

    private static func firstString(
        in state: [String: JSONValue],
        keys: [String]
    ) -> String? {
        for key in keys {
            if let value = state[key]?.stringValue?.trimmingCharacters(in: .whitespacesAndNewlines),
               !value.isEmpty {
                return value
            }
        }
        return nil
    }

    private static func displayLabel(_ value: String) -> String {
        value
            .replacingOccurrences(of: "_", with: " ")
            .replacingOccurrences(of: "-", with: " ")
            .capitalized
    }

    private static func updatedDateLabel(for timestamp: Double) -> String {
        guard timestamp.isFinite, timestamp > 0 else {
            return "Unknown"
        }
        return dateFormatter.string(from: Date(timeIntervalSince1970: timestamp))
    }

    private static let dateFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.dateStyle = .medium
        formatter.timeStyle = .short
        return formatter
    }()
}

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
