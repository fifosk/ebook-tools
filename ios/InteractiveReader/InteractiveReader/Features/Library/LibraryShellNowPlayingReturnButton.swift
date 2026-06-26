import SwiftUI

struct LibraryShellNowPlayingReturnButton: View {
    let title: String
    let subtitle: String?
    let horizontalPadding: CGFloat
    let topPadding: CGFloat
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: 14) {
                Image(systemName: "arrow.uturn.backward.circle.fill")
                    .font(.title2.weight(.semibold))
                VStack(alignment: .leading, spacing: 2) {
                    Text("Return to Now Playing")
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(.secondary)
                    Text(title)
                        .font(.headline.weight(.semibold))
                        .lineLimit(1)
                        .minimumScaleFactor(0.8)
                    if let subtitle {
                        Text(subtitle)
                            .font(.caption)
                            .foregroundStyle(.secondary)
                            .lineLimit(1)
                    }
                }
                Spacer(minLength: 16)
                Image(systemName: "chevron.right")
                    .font(.headline.weight(.semibold))
                    .foregroundStyle(.secondary)
            }
            .padding(.vertical, 10)
            .frame(maxWidth: .infinity, alignment: .leading)
        }
        .buttonStyle(.borderedProminent)
        .controlSize(.large)
        .padding(.horizontal, horizontalPadding)
        .padding(.top, topPadding)
        .accessibilityLabel("Return to Now Playing")
        .accessibilityValue(title)
        .accessibilityIdentifier("nowPlayingReturnButton")
    }
}

struct LibraryShellNowPlayingMiniButton: View {
    let title: String
    let subtitle: String?
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: 16) {
                Image(systemName: "waveform.circle.fill")
                    .font(.title.weight(.semibold))

                VStack(alignment: .leading, spacing: 2) {
                    Text("Now Playing")
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(.secondary)
                    Text(title)
                        .font(.headline.weight(.semibold))
                        .lineLimit(1)
                        .minimumScaleFactor(0.78)
                    if let subtitle {
                        Text(subtitle)
                            .font(.caption)
                            .foregroundStyle(.secondary)
                            .lineLimit(1)
                    }
                }

                Spacer(minLength: 18)

                HStack(spacing: 8) {
                    Text("Open")
                        .font(.callout.weight(.semibold))
                    Image(systemName: "chevron.right.circle.fill")
                        .font(.title3.weight(.semibold))
                }
                .foregroundStyle(.secondary)
            }
            .padding(.vertical, 14)
            .padding(.horizontal, 18)
            .frame(minWidth: 520, maxWidth: 780, alignment: .leading)
        }
        .buttonStyle(.borderedProminent)
        .controlSize(.large)
        .accessibilityLabel("Return to Now Playing")
        .accessibilityValue(title)
        .accessibilityIdentifier("nowPlayingMiniReturnButton")
    }
}
