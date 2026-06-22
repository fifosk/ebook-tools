import SwiftUI

struct TokenFlowLayout: Layout {
    let itemSpacing: CGFloat
    let lineSpacing: CGFloat
    let alignment: HorizontalAlignment

    private struct Line {
        var indices: [Int] = []
        var width: CGFloat = 0
        var height: CGFloat = 0
    }

    init(itemSpacing: CGFloat, lineSpacing: CGFloat, alignment: HorizontalAlignment = .center) {
        self.itemSpacing = itemSpacing
        self.lineSpacing = lineSpacing
        self.alignment = alignment
    }

    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        let maxWidth = proposal.width ?? .greatestFiniteMagnitude
        let lines = buildLines(maxWidth: maxWidth, subviews: subviews)
        let maxLineWidth = lines.map(\.width).max() ?? 0
        let totalHeight = lines.reduce(0) { $0 + $1.height }
            + lineSpacing * max(0, CGFloat(lines.count - 1))
        return CGSize(width: min(maxWidth, maxLineWidth), height: totalHeight)
    }

    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) {
        guard bounds.width > 0 else { return }
        let lines = buildLines(maxWidth: bounds.width, subviews: subviews)
        var y = bounds.minY
        for line in lines {
            let lineWidth = line.width
            let xStart: CGFloat = {
                switch alignment {
                case .leading:
                    return bounds.minX
                case .trailing:
                    return bounds.minX + max(0, bounds.width - lineWidth)
                default:
                    return bounds.minX + max(0, (bounds.width - lineWidth) / 2)
                }
            }()
            var x = xStart
            for index in line.indices {
                let subview = subviews[index]
                let size = subview.sizeThatFits(.unspecified)
                let origin = CGPoint(x: x, y: y + (line.height - size.height) / 2)
                subview.place(at: origin, proposal: ProposedViewSize(width: size.width, height: size.height))
                x += size.width + itemSpacing
            }
            y += line.height + lineSpacing
        }
    }

    private func buildLines(maxWidth: CGFloat, subviews: Subviews) -> [Line] {
        guard !subviews.isEmpty else { return [] }
        let effectiveWidth = maxWidth > 0 ? maxWidth : .greatestFiniteMagnitude
        var lines: [Line] = []
        var current = Line()
        for index in subviews.indices {
            let size = subviews[index].sizeThatFits(.unspecified)
            let itemWidth = size.width
            if current.indices.isEmpty {
                current.indices = [index]
                current.width = itemWidth
                current.height = size.height
                continue
            }
            if current.width + itemSpacing + itemWidth <= effectiveWidth {
                current.indices.append(index)
                current.width += itemSpacing + itemWidth
                current.height = max(current.height, size.height)
            } else {
                lines.append(current)
                current = Line(indices: [index], width: itemWidth, height: size.height)
            }
        }
        if !current.indices.isEmpty {
            lines.append(current)
        }
        return lines
    }
}
