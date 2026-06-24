import SwiftUI

struct AppleBookCreateAdvancedMetadataJSONEditor: View {
    @Binding var text: String
    let errorMessage: String?
    let disclosureIdentifier: String
    let textEditorIdentifier: String
    let applyIdentifier: String
    let syncIdentifier: String
    let errorIdentifier: String
    let onApply: () -> Void
    let onSync: () -> Void

    var body: some View {
        #if os(tvOS)
        Group {
            Text("Advanced Metadata JSON")
                .font(.headline)
            editorBody
        }
        .accessibilityIdentifier(disclosureIdentifier)
        #else
        DisclosureGroup("Advanced Metadata JSON") {
            editorBody
        }
        .accessibilityIdentifier(disclosureIdentifier)
        #endif
    }

    private var editorBody: some View {
        VStack(alignment: .leading, spacing: 8) {
            jsonEditorControl

            HStack(spacing: 12) {
                Button(action: onApply) {
                    Label("Apply JSON", systemImage: "checkmark.circle")
                }
                .accessibilityIdentifier(applyIdentifier)

                Button(action: onSync) {
                    Label("Sync From Fields", systemImage: "arrow.triangle.2.circlepath")
                }
                .accessibilityIdentifier(syncIdentifier)
            }

            if let errorMessage, !errorMessage.isEmpty {
                Label(errorMessage, systemImage: "exclamationmark.triangle")
                    .font(.footnote)
                    .foregroundStyle(.red)
                    .accessibilityIdentifier(errorIdentifier)
            }
        }
    }

    @ViewBuilder
    private var jsonEditorControl: some View {
        #if os(tvOS)
        TextField("Advanced Metadata JSON", text: $text, axis: .vertical)
            .font(.system(.footnote, design: .monospaced))
            .lineLimit(6...10)
            .autocorrectionDisabled()
            .accessibilityIdentifier(textEditorIdentifier)
        #else
        TextEditor(text: $text)
            .font(.system(.footnote, design: .monospaced))
            .frame(minHeight: 140)
            .textInputAutocapitalization(.never)
            .autocorrectionDisabled()
            .accessibilityIdentifier(textEditorIdentifier)
        #endif
    }
}

struct AppleBookCreateMetadataArtworkPreview: View {
    let posterURL: String
    let stillURL: String
    var thumbnailURL: String = ""
    let posterLabel: String
    let stillLabel: String
    var thumbnailLabel: String = "YouTube thumbnail"

    var body: some View {
        let items = [
            ArtworkItem(urlString: posterURL, label: posterLabel, accessibilityIdentifier: "createMetadataPosterPreview"),
            ArtworkItem(urlString: stillURL, label: stillLabel, accessibilityIdentifier: "createMetadataStillPreview"),
            ArtworkItem(urlString: thumbnailURL, label: thumbnailLabel, accessibilityIdentifier: "createMetadataYoutubeThumbnailPreview")
        ].filter { !$0.urlString.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }

        if !items.isEmpty {
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 12) {
                    ForEach(items) { item in
                        AppleBookCreateMetadataArtworkTile(item: item)
                    }
                }
                .padding(.vertical, 4)
            }
            .accessibilityIdentifier("createMetadataArtworkPreview")
        }
    }
}

struct AppleBookCreateMetadataStatusMessages: View {
    let message: String?
    let errorMessage: String?
    let statusIdentifier: String
    let errorIdentifier: String

    var body: some View {
        if let message, !message.isEmpty {
            Label(message, systemImage: "checkmark.circle")
                .font(.footnote)
                .foregroundStyle(.secondary)
                .accessibilityIdentifier(statusIdentifier)
        }
        if let errorMessage, !errorMessage.isEmpty {
            Label(errorMessage, systemImage: "exclamationmark.triangle")
                .font(.footnote)
                .foregroundStyle(.red)
                .accessibilityIdentifier(errorIdentifier)
        }
    }
}

struct AppleBookCreateMetadataActionButton: View {
    let title: String
    let busyTitle: String?
    let systemImage: String
    let busySystemImage: String
    let isBusy: Bool
    let isDisabled: Bool
    let accessibilityIdentifier: String
    let action: () -> Void

    init(
        title: String,
        busyTitle: String? = nil,
        systemImage: String,
        busySystemImage: String = "hourglass",
        isBusy: Bool = false,
        isDisabled: Bool,
        accessibilityIdentifier: String,
        action: @escaping () -> Void
    ) {
        self.title = title
        self.busyTitle = busyTitle
        self.systemImage = systemImage
        self.busySystemImage = busySystemImage
        self.isBusy = isBusy
        self.isDisabled = isDisabled
        self.accessibilityIdentifier = accessibilityIdentifier
        self.action = action
    }

    var body: some View {
        AppleBookCreateBusyActionButton(
            title: title,
            busyTitle: busyTitle,
            systemImage: systemImage,
            busySystemImage: busySystemImage,
            isBusy: isBusy,
            isDisabled: isDisabled,
            accessibilityIdentifier: accessibilityIdentifier,
            action: action
        )
    }
}

struct AppleBookCreateBusyActionButton: View {
    let title: String
    let busyTitle: String?
    let systemImage: String
    let busySystemImage: String
    let isBusy: Bool
    let isDisabled: Bool
    let accessibilityIdentifier: String
    let action: () -> Void

    init(
        title: String,
        busyTitle: String? = nil,
        systemImage: String,
        busySystemImage: String = "hourglass",
        isBusy: Bool = false,
        isDisabled: Bool,
        accessibilityIdentifier: String,
        action: @escaping () -> Void
    ) {
        self.title = title
        self.busyTitle = busyTitle
        self.systemImage = systemImage
        self.busySystemImage = busySystemImage
        self.isBusy = isBusy
        self.isDisabled = isDisabled
        self.accessibilityIdentifier = accessibilityIdentifier
        self.action = action
    }

    var body: some View {
        Button(action: action) {
            Label(
                isBusy ? (busyTitle ?? title) : title,
                systemImage: isBusy ? busySystemImage : systemImage
            )
        }
        .disabled(isDisabled)
        .accessibilityIdentifier(accessibilityIdentifier)
    }
}

private struct AppleBookCreateMetadataArtworkTile: View {
    let item: ArtworkItem

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            ZStack {
                RoundedRectangle(cornerRadius: 8)
                    .fill(.thinMaterial)
                if let url = URL(string: item.urlString.trimmingCharacters(in: .whitespacesAndNewlines)) {
                    AsyncImage(url: url) { phase in
                        switch phase {
                        case .success(let image):
                            image
                                .resizable()
                                .scaledToFill()
                        case .failure:
                            Image(systemName: "photo")
                                .font(.title2)
                                .foregroundStyle(.secondary)
                        case .empty:
                            ProgressView()
                        @unknown default:
                            Image(systemName: "photo")
                                .font(.title2)
                                .foregroundStyle(.secondary)
                        }
                    }
                } else {
                    Image(systemName: "photo")
                        .font(.title2)
                        .foregroundStyle(.secondary)
                }
            }
            .frame(width: 118, height: 78)
            .clipShape(RoundedRectangle(cornerRadius: 8))

            Text(item.label)
                .font(.caption)
                .lineLimit(1)
                .foregroundStyle(.secondary)
        }
        .frame(width: 118, alignment: .leading)
        .accessibilityElement(children: .combine)
        .accessibilityLabel(item.label)
        .accessibilityIdentifier(item.accessibilityIdentifier)
    }
}

private struct ArtworkItem: Identifiable {
    let urlString: String
    let label: String
    let accessibilityIdentifier: String

    var id: String {
        accessibilityIdentifier
    }
}
