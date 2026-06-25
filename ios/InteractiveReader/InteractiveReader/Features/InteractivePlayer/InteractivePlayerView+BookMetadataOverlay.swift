import SwiftUI

extension InteractivePlayerView {
    #if os(iOS)
    func handleHeaderCoverTap() {
        guard headerInfo != nil else { return }
        withAnimation(.spring(response: 0.28, dampingFraction: 0.86)) {
            showBookMetadataOverlay = true
        }
    }

    func dismissBookMetadataOverlay() {
        withAnimation(.easeOut(duration: 0.18)) {
            showBookMetadataOverlay = false
        }
    }
    #else
    func handleHeaderCoverTap() {}
    func dismissBookMetadataOverlay() {}
    #endif
}

struct InteractivePlayerBookMetadataOverlay: View {
    let info: InteractivePlayerHeaderInfo
    let isPad: Bool
    let onDismiss: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            header
            Divider()
                .overlay(Color.white.opacity(0.18))
            metadataRows
        }
        .padding(isPad ? 22 : 18)
        .frame(maxWidth: isPad ? 560 : .infinity, alignment: .leading)
        .background(PlayerHeaderIdentityBannerBackground(cornerRadius: 24))
        .clipShape(RoundedRectangle(cornerRadius: 24, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 24, style: .continuous)
                .strokeBorder(Color.white.opacity(0.16), lineWidth: 1)
        )
        .shadow(color: Color.black.opacity(0.42), radius: 24, x: 0, y: 14)
    }

    private var header: some View {
        HStack(alignment: .top, spacing: 14) {
            PlayerCoverStackView(
                primaryURL: info.coverURL,
                secondaryURL: info.secondaryCoverURL,
                width: isPad ? 74 : 58,
                height: isPad ? 96 : 76,
                isTV: false
            )
            .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
            VStack(alignment: .leading, spacing: 6) {
                Text(title)
                    .font(isPad ? .title3.weight(.semibold) : .headline.weight(.semibold))
                    .foregroundStyle(Color.white)
                    .lineLimit(3)
                    .minimumScaleFactor(0.82)
                if !author.isEmpty {
                    Text("by \(author)")
                        .font(.subheadline)
                        .foregroundStyle(Color.white.opacity(0.72))
                        .lineLimit(2)
                }
            }
            Spacer(minLength: 8)
            Button(action: onDismiss) {
                Image(systemName: "xmark")
                    .font(.system(size: 13, weight: .bold))
                    .foregroundStyle(Color.white.opacity(0.84))
                    .frame(width: 34, height: 34)
                    .background(PlayerHeaderPillBackground(isActive: false))
            }
            .buttonStyle(.plain)
            .accessibilityLabel("Close book metadata")
        }
    }

    private var metadataRows: some View {
        VStack(alignment: .leading, spacing: 10) {
            metadataRow(icon: "books.vertical", label: "Type", value: info.itemTypeLabel)
            if !languageSummary.isEmpty {
                metadataRow(icon: "globe", label: "Languages", value: languageSummary)
            }
            if let translationModel = info.translationModel?.trimmingCharacters(in: .whitespacesAndNewlines),
               !translationModel.isEmpty {
                metadataRow(icon: "sparkles", label: "Model", value: translationModel)
            }
        }
    }

    private func metadataRow(icon: String, label: String, value: String) -> some View {
        HStack(alignment: .firstTextBaseline, spacing: 10) {
            Image(systemName: icon)
                .font(.subheadline.weight(.semibold))
                .foregroundStyle(Color.white.opacity(0.72))
                .frame(width: 18)
            Text(label)
                .font(.footnote.weight(.semibold))
                .foregroundStyle(Color.white.opacity(0.64))
                .frame(width: 72, alignment: .leading)
            Text(value)
                .font(.subheadline)
                .foregroundStyle(Color.white.opacity(0.88))
                .fixedSize(horizontal: false, vertical: true)
        }
    }

    private var title: String {
        let trimmed = info.title.trimmingCharacters(in: .whitespacesAndNewlines)
        return trimmed.isEmpty ? "Untitled" : trimmed
    }

    private var author: String {
        info.author.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private var languageSummary: String {
        info.languageFlags
            .map(\.label)
            .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
            .filter { !$0.isEmpty }
            .joined(separator: " -> ")
    }
}
