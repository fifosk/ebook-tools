import SwiftUI

private struct PlayTriangle: Shape {
    func path(in rect: CGRect) -> Path {
        var path = Path()
        path.move(to: CGPoint(x: rect.minX, y: rect.minY))
        path.addLine(to: CGPoint(x: rect.maxX, y: rect.midY))
        path.addLine(to: CGPoint(x: rect.minX, y: rect.maxY))
        path.closeSubpath()
        return path
    }
}

struct YoutubeGlyphMark: View {
    let width: CGFloat
    let height: CGFloat

    var body: some View {
        ZStack {
            RoundedRectangle(cornerRadius: height * 0.28, style: .continuous)
                .fill(Color(red: 1, green: 0, blue: 0))
            PlayTriangle()
                .fill(Color.white)
                .frame(width: height * 0.42, height: height * 0.42)
                .offset(x: height * 0.04)
        }
        .frame(width: width, height: height)
    }
}

struct TubeTVGlyphMark: View {
    let width: CGFloat
    let height: CGFloat
    let color: Color

    var body: some View {
        TubeTVShape()
            .stroke(
                color,
                style: StrokeStyle(
                    lineWidth: max(1.2, height * 0.12),
                    lineCap: .round,
                    lineJoin: .round
                )
            )
            .frame(width: width, height: height)
    }
}

private struct TubeTVShape: Shape {
    func path(in rect: CGRect) -> Path {
        let width = rect.width
        let height = rect.height
        let bodyRect = CGRect(
            x: rect.minX + width * 0.05,
            y: rect.minY + height * 0.18,
            width: width * 0.9,
            height: height * 0.62
        )
        let screenRect = bodyRect.insetBy(dx: bodyRect.width * 0.18, dy: bodyRect.height * 0.2)
        let antennaHeight = height * 0.2
        let baseY = bodyRect.maxY + height * 0.08
        let baseHalf = width * 0.18
        let antennaSpan = width * 0.2

        var path = Path()
        path.addRoundedRect(
            in: bodyRect,
            cornerSize: CGSize(width: bodyRect.height * 0.22, height: bodyRect.height * 0.22)
        )
        path.addRoundedRect(
            in: screenRect,
            cornerSize: CGSize(width: screenRect.height * 0.18, height: screenRect.height * 0.18)
        )
        path.move(to: CGPoint(x: bodyRect.midX, y: bodyRect.minY))
        path.addLine(to: CGPoint(x: bodyRect.midX - antennaSpan, y: bodyRect.minY - antennaHeight))
        path.move(to: CGPoint(x: bodyRect.midX, y: bodyRect.minY))
        path.addLine(to: CGPoint(x: bodyRect.midX + antennaSpan, y: bodyRect.minY - antennaHeight))
        path.move(to: CGPoint(x: bodyRect.midX - baseHalf, y: baseY))
        path.addLine(to: CGPoint(x: bodyRect.midX + baseHalf, y: baseY))
        return path
    }
}

struct PlayerCoverStackView: View {
    let primaryURL: URL?
    let secondaryURL: URL?
    let width: CGFloat
    let height: CGFloat
    let isTV: Bool

    var body: some View {
        if let resolvedPrimary = primaryURL ?? secondaryURL {
            let resolvedSecondary = (primaryURL != nil && secondaryURL != nil && primaryURL != secondaryURL)
                ? secondaryURL
                : nil
            ZStack(alignment: .topLeading) {
                coverImage(url: resolvedPrimary, width: width, height: height)
                if let resolvedSecondary {
                    coverImage(url: resolvedSecondary, width: secondaryWidth, height: secondaryHeight)
                        .offset(x: secondaryOffset, y: secondaryYOffset)
                }
            }
            .frame(width: stackWidth(resolvedSecondary != nil), height: height, alignment: .leading)
        }
    }

    private func coverImage(url: URL, width: CGFloat, height: CGFloat) -> some View {
        AsyncImage(url: url) { phase in
            if let image = phase.image {
                image.resizable().scaledToFill()
            } else {
                Color.black.opacity(0.35)
            }
        }
        .frame(width: width, height: height)
        .clipShape(RoundedRectangle(cornerRadius: 6))
        .overlay(
            RoundedRectangle(cornerRadius: 6)
                .stroke(Color.white.opacity(0.22), lineWidth: 1)
        )
    }

    private var secondaryScale: CGFloat {
        0.66
    }

    private var secondaryWidth: CGFloat {
        width * secondaryScale
    }

    private var secondaryHeight: CGFloat {
        height * secondaryScale
    }

    private var secondaryOffset: CGFloat {
        width * (isTV ? 0.72 : 0.68)
    }

    private var secondaryYOffset: CGFloat {
        height * (1 - secondaryScale)
    }

    private func stackWidth(_ hasSecondary: Bool) -> CGFloat {
        width + (hasSecondary ? secondaryOffset : 0)
    }
}
